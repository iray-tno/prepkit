import click
import os
import re
from collections import defaultdict
import clang.cindex
import subprocess
import yaml
from typing import List, Tuple, Dict, Set, Any
from base_interfaces import BasePreprocessor, BaseMinifier
from preprocessing_utils import topological_sort_files, StringLiteralProtector, report_circular_dependency_error

# Set libclang path once when the module is imported
try:
    clang.cindex.Config.set_library_file("/lib/x86_64-linux-gnu/libclang-18.so.18")
except Exception as e:
    click.echo(f"Warning: Could not set libclang library path. Ensure libclang-18 is installed and accessible. Error: {e}", err=True)

class CppPreprocessor(BasePreprocessor):
    def preprocess(self, file_path: str, include_paths: List[str]) -> str:
        click.echo(f"Preprocessing {file_path}")
        
        all_include_paths: List[str] = list(include_paths)
        file_dir: str = os.path.dirname(file_path)
        if file_dir not in all_include_paths:
            all_include_paths.insert(0, file_dir)

        all_files: Set[str] = {os.path.abspath(file_path)}
        include_regex: re.Pattern = re.compile(r'#include\s+"([^"]+)"')
        files_to_scan: List[str] = [file_path]

        while files_to_scan:
            current_file: str = files_to_scan.pop(0)
            with open(current_file, 'r') as f:
                content: str = f.read()
            
            for match in include_regex.finditer(content):
                include_file: str = match.group(1)
                for path in all_include_paths:
                    full_path: str = os.path.abspath(os.path.join(path, include_file))
                    if os.path.exists(full_path) and full_path not in all_files:
                        all_files.add(full_path)
                        files_to_scan.append(full_path)

        graph, in_degree = self._build_dependency_graph(list(all_files), all_include_paths)
        sorted_files, cycle_files = topological_sort_files(graph, in_degree, list(all_files))

        if sorted_files:
            combined_content: str = ""
            for f in sorted_files:
                with open(f, 'r') as source_file:
                    source_content: str = source_file.read()
                    source_content = include_regex.sub("", source_content)
                    combined_content += source_content

            temp_file_path: str = "temp_combined.cpp"
            with open(temp_file_path, "w") as f:
                f.write(combined_content)

            # First clang-format pass for initial formatting
            subprocess.run(['clang-format', '-i', temp_file_path])
            
            with open(temp_file_path, "r") as f:
                formatted_content: str = f.read()

            index: clang.cindex.Index = clang.cindex.Index.create()
            clang_include_paths: List[str] = [f'-I{path}' for path in all_include_paths]
            
            # Re-parse formatted_content to get accurate AST after first formatting pass
            tu_for_decls: clang.cindex.TranslationUnit = index.parse(temp_file_path, args=clang_include_paths, unsaved_files=[(temp_file_path, formatted_content)])

            constexpr_values: Dict[str, str] = {}
            constexpr_decl_ranges: List[clang.cindex.SourceRange] = []

            for c in tu_for_decls.cursor.walk_preorder():
                if c.kind == clang.cindex.CursorKind.VAR_DECL:
                    tokens: Set[str] = {t.spelling for t in c.get_tokens()}
                    if 'constexpr' in tokens:
                        # Store the source range of the constexpr declaration
                        constexpr_decl_ranges.append(c.extent)
                        # Also collect the value for replacement later
                        name: str = c.spelling
                        value: str | None = None
                        literal_kinds: List[clang.cindex.CursorKind] = [
                            clang.cindex.CursorKind.INTEGER_LITERAL, 
                            clang.cindex.CursorKind.FLOATING_LITERAL, 
                            clang.cindex.CursorKind.IMAGINARY_LITERAL, 
                            clang.cindex.CursorKind.STRING_LITERAL, 
                            clang.cindex.CursorKind.CHARACTER_LITERAL,
                            clang.cindex.CursorKind.CXX_BOOL_LITERAL_EXPR
                        ]
                        for child in c.get_children():
                            if child.kind in literal_kinds:
                                value_token: clang.cindex.Token | None = next(child.get_tokens(), None)
                                if value_token:
                                    value = value_token.spelling
                                    break
                            elif child.kind == clang.cindex.CursorKind.UNEXPOSED_EXPR:
                                # Handle unexposed expressions that might contain literals (e.g., string literals)
                                for grandchild in child.get_children():
                                    if grandchild.kind in literal_kinds:
                                        value_token: clang.cindex.Token | None = next(grandchild.get_tokens(), None)
                                        if value_token:
                                            value = value_token.spelling
                                            break
                                if value:
                                    break
                            elif child.kind == clang.cindex.CursorKind.UNARY_OPERATOR:
                                # Handle negative numbers: constexpr double NEG_PI = -3.14159;
                                tokens = list(child.get_tokens())
                                if len(tokens) >= 2 and tokens[0].spelling == '-':
                                    # Check if second token is a numeric literal
                                    for grandchild in child.get_children():
                                        if grandchild.kind in [clang.cindex.CursorKind.INTEGER_LITERAL, clang.cindex.CursorKind.FLOATING_LITERAL]:
                                            value = '-' + tokens[1].spelling
                                            break
                                if value:
                                    break
                        if value:
                            constexpr_values[name] = value

            # Build new content by skipping constexpr declarations
            processed_content_list: List[str] = []
            current_offset: int = 0
            # Sort ranges by start offset to process them in order
            for extent in sorted(constexpr_decl_ranges, key=lambda x: x.start.offset):
                # Add content before the current constexpr declaration
                processed_content_list.append(formatted_content[current_offset:extent.start.offset])
                current_offset = extent.end.offset
            # Add any remaining content after the last constexpr declaration
            processed_content_list.append(formatted_content[current_offset:])
            processed_content: str = "".join(processed_content_list)

            # Perform text-based constexpr replacement using StringLiteralProtector
            with StringLiteralProtector(processed_content) as protected:
                for name, value in constexpr_values.items():
                    processed_content = protected.replace(name, value)

            # Remove comments using regex
            processed_content = re.sub(r'//.*\n', '\n', processed_content)  # Single-line comments
            processed_content = re.sub(r'/\*.*?\*/', '', processed_content, flags=re.DOTALL)  # Multi-line comments

            # Check for prepkit_config.yaml for minification setting
            config_file_path: str = os.path.join(os.getcwd(), "prepkit_config.yaml")
            minify_output: bool = False
            if os.path.exists(config_file_path):
                try:
                    with open(config_file_path, 'r') as f:
                        config: Dict[str, Any] = yaml.safe_load(f)
                        minify_output = config.get("cpp_preprocess", {}).get("minify_output", False)
                except yaml.YAMLError as e:
                    click.echo(f"Warning: Error reading prepkit_config.yaml: {e}. Using default settings.", err=True)

            if minify_output:
                # Aggressive clang-format style for minification
                minify_style: str = "{IndentWidth: 0, BreakBeforeBraces: Attach, SpaceAfterCStyleCast: false, SpacesInParentheses: false, CompactNamespaces: true, AllowShortBlocksOnASingleLine: Always, AllowShortFunctionsOnASingleLine: All}"

                # Final clang-format pass with minification style
                with open(temp_file_path, "w") as f:
                    f.write(processed_content)

                subprocess.run(['clang-format', '-i', '-style=' + minify_style, temp_file_path])

                with open(temp_file_path, "r") as f:
                    minified_output: str = f.read()
                minified_output = re.sub(r'\s+', '', minified_output) # Remove all whitespace
                minified_output = re.sub(r'\n', '', minified_output) # Remove all newlines
                final_output: str = minified_output
            else:
                # Final clang-format pass with default style
                with open(temp_file_path, "w") as f:
                    f.write(processed_content)

                subprocess.run(['clang-format', '-i', temp_file_path])

                with open(temp_file_path, "r") as f:
                    final_output: str = f.read()

            os.remove(temp_file_path)
            return final_output
        else:
            # Report circular dependency error
            report_circular_dependency_error(cycle_files, language="C++")
            return ""

    def get_supported_languages(self) -> List[str]:
        return ["cpp", "cxx", "c"]

    def _build_dependency_graph(self, files: List[str], include_paths: List[str]) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        graph: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = defaultdict(int)
        
        include_regex: re.Pattern = re.compile(r'#include\s+"([^"]+)"')

        for file_path in files:
            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r') as f:
                content: str = f.read()

            for match in include_regex.finditer(content):
                include_file: str = match.group(1)
                found: bool = False
                for path in include_paths:
                    full_path: str = os.path.abspath(os.path.join(path, include_file))
                    if os.path.exists(full_path):
                        graph[full_path].append(os.path.abspath(file_path))
                        in_degree[os.path.abspath(file_path)] += 1
                        found = True
                        break
                if not found:
                    # Show searched paths for better debugging
                    searched_paths = '\n    '.join([os.path.abspath(path) for path in include_paths])
                    click.echo(f"❌ Error: Could not find include file '{include_file}'", err=True)
                    click.echo(f"   Referenced in: {file_path}", err=True)
                    click.echo(f"   Searched in:", err=True)
                    click.echo(f"    {searched_paths}", err=True)
                    click.echo(f"   Hint: Use -I/--include-path to specify additional search directories", err=True)

        return graph, in_degree


class CppMinifier(BaseMinifier):
    """C++ code minifier that removes comments and whitespace for size-constrained platforms."""
    
    def minify(self, file_path: str) -> str:
        """Minify C++ code by removing comments and excess whitespace."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Create temporary file
        temp_file_path = "temp_minify.cpp"
        with open(temp_file_path, "w") as f:
            f.write(content)
        
        try:
            # Use clang-format with aggressive minification style
            minify_style = """{
                BasedOnStyle: LLVM,
                IndentWidth: 0,
                TabWidth: 0,
                UseTab: Never,
                BreakBeforeBraces: Attach,
                AllowShortIfStatementsOnASingleLine: true,
                AllowShortLoopsOnASingleLine: true,
                AllowShortFunctionsOnASingleLine: true,
                AllowShortBlocksOnASingleLine: true,
                ColumnLimit: 1000
            }"""
            
            subprocess.run(['clang-format', '-i', '-style=' + minify_style, temp_file_path])
            
            with open(temp_file_path, "r") as f:
                minified_output = f.read()
            
            # Remove comments using regex (basic approach)
            # Remove single-line comments
            minified_output = re.sub(r'//.*$', '', minified_output, flags=re.MULTILINE)
            # Remove multi-line comments
            minified_output = re.sub(r'/\*.*?\*/', '', minified_output, flags=re.DOTALL)
            
            # Moderate minification that preserves compilation compatibility
            # Remove extra whitespace but keep necessary structure
            lines = minified_output.split('\n')
            minified_lines = []
            
            for line in lines:
                line = line.strip()
                if line:
                    # Keep include statements on separate lines
                    if line.startswith('#include'):
                        minified_lines.append(line)
                    else:
                        # For other lines, compress spaces but keep basic structure
                        line = re.sub(r'\s+', ' ', line)
                        line = re.sub(r'\s*([{}();,])\s*', r'\1', line)
                        minified_lines.append(line)
            
            minified_output = '\n'.join(minified_lines)
            
            return minified_output
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def get_supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return ["cpp", "c", "cxx"]
