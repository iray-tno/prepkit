import click
import os
import re
from collections import defaultdict
import subprocess
import tempfile
import yaml
from typing import List, Tuple, Dict, Set, Any
from base_interfaces import BasePreprocessor, BaseMinifier
from preprocessing_utils import topological_sort_files, report_circular_dependency_error


def _run_clang_format(command: List[str]) -> None:
    """Run clang-format and raise a clear Click error on failure."""
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise click.ClickException(
            "clang-format not found. Please install clang-format and ensure it is in PATH."
        ) from e

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        message = f"clang-format failed with exit code {result.returncode}"
        if details:
            message = f"{message}:\n{details}"
        raise click.ClickException(message)


def _read_cpp_raw_string(content: str, start: int) -> Tuple[str, int] | None:
    """Read a C++ raw string literal starting at or near start, if present."""
    for prefix in ("u8R", "LR", "uR", "UR", "R"):
        if not content.startswith(prefix + '"', start):
            continue

        delimiter_start = start + len(prefix) + 1
        paren_index = content.find("(", delimiter_start)
        if paren_index == -1:
            return None

        delimiter = content[delimiter_start:paren_index]
        terminator = ")" + delimiter + '"'
        terminator_index = content.find(terminator, paren_index + 1)
        if terminator_index == -1:
            return content[start:], len(content)

        end = terminator_index + len(terminator)
        return content[start:end], end

    return None


def _strip_cpp_comments(content: str) -> str:
    """Remove C++ comments while preserving string, char, and raw string literals."""
    result: List[str] = []
    i = 0

    while i < len(content):
        raw_string = _read_cpp_raw_string(content, i)
        if raw_string is not None:
            literal, i = raw_string
            result.append(literal)
            continue

        current = content[i]
        next_char = content[i + 1] if i + 1 < len(content) else ""

        if current in {'"', "'"}:
            quote = current
            literal_start = i
            i += 1
            while i < len(content):
                if content[i] == "\\":
                    i += 2
                    continue
                if content[i] == quote:
                    i += 1
                    break
                i += 1
            result.append(content[literal_start:i])
            continue

        if current == "/" and next_char == "/":
            i += 2
            while i < len(content) and content[i] != "\n":
                i += 1
            if i < len(content):
                result.append("\n")
                i += 1
            continue

        if current == "/" and next_char == "*":
            i += 2
            while i + 1 < len(content) and not (content[i] == "*" and content[i + 1] == "/"):
                if content[i] == "\n":
                    result.append("\n")
                i += 1
            i = i + 2 if i + 1 < len(content) else len(content)
            continue

        result.append(current)
        i += 1

    return "".join(result)


class CppPreprocessor(BasePreprocessor):
    def preprocess(self, file_path: str, include_paths: List[str], defines: Dict[str, str] = None) -> str:
        """
        Preprocess C++ file by flattening includes and optionally injecting tunable parameters.

        Args:
            file_path: Path to the main C++ file
            include_paths: Additional include search paths
            defines: Optional dict of parameter names to values for injection.
                     Only replaces parameters marked with // @tune comment.

        Returns:
            Preprocessed C++ code as a single string
        """
        click.echo(f"Preprocessing {file_path}")
        if defines:
            click.echo(f"Injecting {len(defines)} tunable parameter(s): {list(defines.keys())}")
        
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

            with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as temp_file:
                temp_file.write(combined_content)
                temp_file_path: str = temp_file.name

            try:
                # First clang-format pass for initial formatting
                _run_clang_format(['clang-format', '-i', temp_file_path])

                with open(temp_file_path, "r") as f:
                    processed_content: str = f.read()

                # Inject tunable parameters (before removing comments, as we need // @tune markers)
                if defines:
                    processed_content = self._inject_tunable_params(processed_content, defines)

                processed_content = _strip_cpp_comments(processed_content)

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

                    _run_clang_format(['clang-format', '-i', '-style=' + minify_style, temp_file_path])

                    with open(temp_file_path, "r") as f:
                        minified_output: str = f.read()
                    minified_output = re.sub(r'\s+', '', minified_output) # Remove all whitespace
                    minified_output = re.sub(r'\n', '', minified_output) # Remove all newlines
                    final_output: str = minified_output
                else:
                    # Final clang-format pass with default style
                    with open(temp_file_path, "w") as f:
                        f.write(processed_content)

                    _run_clang_format(['clang-format', '-i', temp_file_path])

                    with open(temp_file_path, "r") as f:
                        final_output: str = f.read()
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

            return final_output
        else:
            # Report circular dependency error
            report_circular_dependency_error(cycle_files, language="C++")
            return ""

    def _inject_tunable_params(self, content: str, defines: Dict[str, str]) -> str:
        """
        Replace values of tunable parameters marked with // @tune.

        Args:
            content: Source code content
            defines: Dictionary of parameter names to replacement values

        Returns:
            Content with tunable parameter values replaced
        """
        # Pattern to match: constexpr TYPE NAME = VALUE; // @tune
        # Captures: TYPE, NAME, VALUE
        pattern = r'(constexpr\s+\w+(?:\s*<[^>]+>)?\s+)(\w+)(\s*=\s*)([^;]+)(;\s*//\s*@tune)'

        def replace_value(match):
            prefix = match.group(1)  # constexpr TYPE
            name = match.group(2)     # NAME
            equals = match.group(3)   # =
            old_value = match.group(4).strip()  # VALUE
            suffix = match.group(5)   # ; // @tune

            if name in defines:
                new_value = defines[name]
                click.echo(f"  {name}: {old_value} -> {new_value}")
                return f"{prefix}{name}{equals}{new_value}{suffix}"
            return match.group(0)  # No replacement

        return re.sub(pattern, replace_value, content)

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
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cpp", delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
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
            
            _run_clang_format(['clang-format', '-i', '-style=' + minify_style, temp_file_path])
            
            with open(temp_file_path, "r") as f:
                minified_output = f.read()
            
            minified_output = _strip_cpp_comments(minified_output)
            
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
