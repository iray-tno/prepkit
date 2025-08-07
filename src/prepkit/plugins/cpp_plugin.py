import click
import os
import re
from collections import defaultdict, deque
import clang.cindex
import subprocess
from ..base_interfaces import BasePreprocessor, BaseMinifier

class CppPreprocessor(BasePreprocessor):
    def preprocess(self, file_path: str, include_paths: list[str]) -> str:
        click.echo(f"Preprocessing {file_path}")
        
        all_include_paths = list(include_paths)
        file_dir = os.path.dirname(file_path)
        if file_dir not in all_include_paths:
            all_include_paths.insert(0, file_dir)

        all_files = {os.path.abspath(file_path)}
        include_regex = re.compile(r'#include\s+"([^"]+)"')
        files_to_scan = [file_path]

        while files_to_scan:
            current_file = files_to_scan.pop(0)
            with open(current_file, 'r') as f:
                content = f.read()
            
            for match in include_regex.finditer(content):
                include_file = match.group(1)
                for path in all_include_paths:
                    full_path = os.path.abspath(os.path.join(path, include_file))
                    if os.path.exists(full_path) and full_path not in all_files:
                        all_files.add(full_path)
                        files_to_scan.append(full_path)

        graph, in_degree = self._build_dependency_graph(list(all_files), all_include_paths)
        sorted_files = self._topological_sort(graph, in_degree, list(all_files))

        if sorted_files:
            combined_content = ""
            for f in sorted_files:
                with open(f, 'r') as source_file:
                    source_content = source_file.read()
                    source_content = include_regex.sub("", source_content)
                    combined_content += source_content

            temp_file_path = "temp_combined.cpp"
            with open(temp_file_path, "w") as f:
                f.write(combined_content)

            # First clang-format pass for initial formatting
            subprocess.run(['clang-format', '-i', temp_file_path])
            
            with open(temp_file_path, "r") as f:
                formatted_content = f.read()

            clang.cindex.Config.set_library_file("/lib/x86_64-linux-gnu/libclang-18.so.18")
            index = clang.cindex.Index.create()
            clang_include_paths = [f'-I{path}' for path in all_include_paths]
            
            # Re-parse formatted_content to get accurate AST after first formatting pass
            tu_for_decls = index.parse(temp_file_path, args=clang_include_paths, unsaved_files=[(temp_file_path, formatted_content)])

            constexpr_values = {}
            constexpr_decl_ranges = []

            for c in tu_for_decls.cursor.walk_preorder():
                if c.kind == clang.cindex.CursorKind.VAR_DECL:
                    tokens = {t.spelling for t in c.get_tokens()}
                    if 'constexpr' in tokens:
                        # Store the source range of the constexpr declaration
                        constexpr_decl_ranges.append(c.extent)
                        # Also collect the value for replacement later
                        name = c.spelling
                        value = None
                        literal_kinds = [clang.cindex.CursorKind.INTEGER_LITERAL, clang.cindex.CursorKind.FLOATING_LITERAL, clang.cindex.CursorKind.IMAGINARY_LITERAL, clang.cindex.CursorKind.STRING_LITERAL, clang.cindex.CursorKind.CHARACTER_LITERAL]
                        for child in c.get_children():
                            if child.kind in literal_kinds:
                                value = next(child.get_tokens(), None)
                                if value:
                                    value = value.spelling
                                    break
                        if value:
                            constexpr_values[name] = value

            # Build new content by skipping constexpr declarations
            processed_content_list = []
            current_offset = 0
            # Sort ranges by start offset to process them in order
            for extent in sorted(constexpr_decl_ranges, key=lambda x: x.start.offset):
                # Add content before the current constexpr declaration
                processed_content_list.append(formatted_content[current_offset:extent.start.offset])
                current_offset = extent.end.offset
            # Add any remaining content after the last constexpr declaration
            processed_content_list.append(formatted_content[current_offset:])
            processed_content = "".join(processed_content_list)

            # Perform text-based constexpr replacement
            for name, value in constexpr_values.items():
                processed_content = re.sub(r'\b' + re.escape(name) + r'\b', value, processed_content)

            # Remove comments using regex
            processed_content = re.sub(r'//.*\n', '\n', processed_content)  # Single-line comments
            processed_content = re.sub(r'/\*.*?\*/', '', processed_content, flags=re.DOTALL)  # Multi-line comments

            # Final clang-format pass
            with open(temp_file_path, "w") as f:
                f.write(processed_content)

            subprocess.run(['clang-format', '-i', temp_file_path])

            with open(temp_file_path, "r") as f:
                final_output = f.read()

            os.remove(temp_file_path)
            return final_output
        else:
            click.echo("Error: Circular dependency detected.", err=True)
            return ""

    def get_supported_languages(self) -> list[str]:
        return ["cpp", "cxx", "c"]

    def _build_dependency_graph(self, files, include_paths):
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        include_regex = re.compile(r'#include\s+"([^"]+)"')

        for file_path in files:
            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r') as f:
                content = f.read()

            for match in include_regex.finditer(content):
                include_file = match.group(1)
                found = False
                for path in include_paths:
                    full_path = os.path.abspath(os.path.join(path, include_file))
                    if os.path.exists(full_path):
                        graph[full_path].append(os.path.abspath(file_path))
                        in_degree[os.path.abspath(file_path)] += 1
                        found = True
                        break
                if not found:
                    click.echo(f"Warning: Could not find include file {include_file} in {file_path}", err=True)

        return graph, in_degree

    def _topological_sort(self, graph, in_degree, all_files):
        queue = deque([f for f in all_files if in_degree[os.path.abspath(f)] == 0])
        sorted_order = []

        while queue:
            node = queue.popleft()
            sorted_order.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(sorted_order) == len(all_files):
            return sorted_order
        else:
            return None

class CppMinifier(BaseMinifier):
    def minify(self, file_path: str) -> str:
        click.echo(f"Minifying {file_path}")
        temp_file_path = "temp_minify.cpp"
        with open(file_path, "r") as f:
            content = f.read()

        # Aggressive clang-format style for minification
        minify_style = "{IndentWidth: 0, BreakBeforeBraces: Attach, SpaceAfterCStyleCast: false, SpacesInParentheses: false, CompactNamespaces: true, AllowShortBlocksOnASingleLine: Always, AllowShortFunctionsOnASingleLine: All}"

        # Remove comments using regex
        content = re.sub(r'//.*\n', '\n', content)  # Single-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # Multi-line comments

        with open(temp_file_path, "w") as f:
            f.write(content)

        subprocess.run(['clang-format', '-i', '-style=' + minify_style, temp_file_path])

        # Remove all newlines and extra spaces
        with open(temp_file_path, "r") as f:
            minified_output = f.read()
        minified_output = re.sub(r'\s+', '', minified_output) # Remove all whitespace
        minified_output = re.sub(r'\n', '', minified_output) # Remove all newlines

        os.remove(temp_file_path)
        return minified_output

    def get_supported_languages(self) -> list[str]:
        return ["cpp", "cxx", "c"]
