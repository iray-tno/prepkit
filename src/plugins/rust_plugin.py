import click
import os
import re
import subprocess
from typing import List, Dict, Optional
from base_interfaces import BasePreprocessor, BaseMinifier
from preprocessing_utils import StringLiteralProtector, report_circular_dependency_error


class RustPreprocessor(BasePreprocessor):
    """Rust preprocessor for flattening multi-file projects into single submission files."""

    def preprocess(self, file_path: str, include_paths: List[str], defines: Dict[str, str] = None) -> str:
        """
        Preprocess a Rust project by flattening modules into a single file.

        Modules are flattened by *wrapping* each `mod name;` declaration in an
        inline `mod name { ... }` block rather than inlining their raw bodies
        into a shared namespace. This preserves every module's own namespace, so
        items sharing a name across modules no longer collide, and all original
        paths (`crate::a::b`, `std::collections::HashMap`, `Type::method`,
        `use foo::bar`) keep resolving without any qualifier rewriting.

        Args:
            file_path: Path to the entry file (main.rs or lib.rs)
            include_paths: Additional paths to search for modules
            defines: Optional dict of parameter names to values for injection.
                     Only replaces parameters marked with // @tune comment.

        Returns:
            Flattened Rust code as a single string
        """
        click.echo(f"Preprocessing {file_path}")
        if defines:
            click.echo(f"Injecting {len(defines)} tunable parameter(s): {list(defines.keys())}")

        # Setup include paths (the entry file's directory is always searched).
        all_include_paths: List[str] = list(include_paths)
        file_dir: str = os.path.dirname(file_path)
        if file_dir not in all_include_paths:
            all_include_paths.insert(0, file_dir)

        # Recursively expand every `mod name;` declaration into `mod name { ... }`.
        combined_content: Optional[str] = self._expand_file(file_path, all_include_paths, [])

        if combined_content is None:
            # A module could not be resolved, or a circular dependency was found.
            # The specific error has already been reported to stderr.
            return ""

        # Format output with rustfmt if available
        combined_content = self._format_with_rustfmt(combined_content)

        # Inject tunable parameters
        if defines:
            combined_content = self._inject_tunable_params(combined_content, defines)

        return combined_content

    def _expand_file(
        self, file_path: str, include_paths: List[str], stack: List[str]
    ) -> Optional[str]:
        """
        Read a file and recursively expand its `mod name;` declarations into
        inline `mod name { ... }` blocks.

        Args:
            file_path: File to expand (the entry file or a module file)
            include_paths: Directories to search for module files
            stack: Chain of files currently being expanded, used to detect
                   circular `mod` references and avoid infinite recursion

        Returns:
            The file's source with all module declarations expanded, or None if a
            module cannot be found or a circular dependency is detected.
        """
        abs_path: str = os.path.abspath(file_path)
        if abs_path in stack:
            # Following mod declarations led back to a file already being expanded.
            cycle_start = stack.index(abs_path)
            report_circular_dependency_error(stack[cycle_start:] + [abs_path], language="Rust")
            return None

        with open(file_path, 'r') as f:
            content: str = f.read()

        # Only declarations anchored at the start of a line are expanded, so
        # `mod x;` or `#[path = "..."]` text that merely appears inside a string
        # literal mid-line is left untouched.
        return self._expand_mod_declarations(
            content, file_path, include_paths, stack + [abs_path]
        )

    def _expand_mod_declarations(
        self, content: str, current_file: str, include_paths: List[str], stack: List[str]
    ) -> Optional[str]:
        """
        Replace each `mod name;` declaration in `content` with an inline
        `mod name { <expanded module body> }` block.

        - cfg-gated modules (preceded by `#[cfg(...)]`) are left untouched so
          conditional-compilation semantics are preserved.
        - `#[path = "..."]` attributes are consumed to locate the module file
          and then removed from the output.

        Args:
            content: String-literal-protected source of a single file
            current_file: Path of the file `content` came from (for resolution)
            include_paths: Directories to search for module files
            stack: Chain of files currently being expanded (for cycle detection)

        Returns:
            The content with declarations expanded, or None on error.
        """
        # Match `mod name;` capturing leading indentation, visibility, and name.
        # Inline modules (`mod name { ... }`) end in `{` and are left as-is.
        mod_regex = re.compile(
            r'^([ \t]*)((?:pub\s*(?:\([^)]*\)\s*)?)?)mod\s+(\w+)\s*;',
            re.MULTILINE,
        )
        path_attr_regex = re.compile(r'#\[\s*path\s*=\s*"([^"]+)"\s*\]')
        cfg_attr_regex = re.compile(r'#\[\s*cfg\([^)]*\)\s*\]')

        parts: List[str] = []
        cursor = 0
        for match in mod_regex.finditer(content):
            indent = match.group(1)
            visibility = match.group(2) or ""
            module_name = match.group(3)
            line_number = content[:match.start()].count('\n') + 1

            before = content[cursor:match.start()]
            content_before = content[:match.start()]

            # Leave cfg-gated modules as-is (they are conditionally compiled).
            cfg_matches = list(cfg_attr_regex.finditer(content_before))
            if cfg_matches and match.start() - cfg_matches[-1].end() < 100:
                parts.append(before)
                parts.append(match.group(0))
                cursor = match.end()
                continue

            # Pick up a nearby #[path = "..."] attribute and strip it from output.
            custom_path: Optional[str] = None
            path_matches = list(path_attr_regex.finditer(content_before))
            if path_matches and match.start() - path_matches[-1].end() < 100:
                custom_path = path_matches[-1].group(1)
                rel_start = path_matches[-1].start() - cursor
                rel_end = path_matches[-1].end() - cursor
                before = before[:rel_start] + before[rel_end:]

            module_file = self._resolve_module_path(
                module_name, current_file, include_paths, custom_path, line_number
            )
            if module_file is None:
                return None  # error already reported

            child_body = self._expand_file(module_file, include_paths, stack)
            if child_body is None:
                return None  # cycle or nested error already reported

            wrapped = f"{indent}{visibility}mod {module_name} {{\n{child_body}\n}}"
            parts.append(before)
            parts.append(wrapped)
            cursor = match.end()

        parts.append(content[cursor:])
        return "".join(parts)

    def _format_with_rustfmt(self, content: str) -> str:
        """Format Rust source with rustfmt if it is available, else return as-is."""
        try:
            temp_file_path: str = "temp_combined.rs"
            with open(temp_file_path, "w") as f:
                f.write(content)

            result = subprocess.run(
                ['rustfmt', temp_file_path],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                with open(temp_file_path, "r") as f:
                    content = f.read()

            os.remove(temp_file_path)
        except (FileNotFoundError, subprocess.SubprocessError):
            # rustfmt not available, use unformatted output
            pass

        return content

    def _resolve_module_path(
        self, module_name: str, current_file: str, include_paths: List[str], 
        custom_path: Optional[str] = None, line_number: int = 0
    ) -> Optional[str]:
        """
        Resolve a module name to its file path following Rust conventions.

        Rust module resolution:
        - #[path = "custom.rs"] mod foo; uses custom path
        - mod foo; looks for foo.rs or foo/mod.rs
        - Search in: current file's directory, then include_paths

        Args:
            module_name: Name of the module (e.g., "utils")
            current_file: Path to file containing the mod declaration
            include_paths: Additional search paths
            custom_path: Optional custom path from #[path = "..."] attribute
            line_number: Line number of the mod declaration (for error reporting)

        Returns:
            Absolute path to module file, or None if not found
        """
        current_dir: str = os.path.dirname(current_file)

        # If custom path is specified via #[path = "..."], use it directly
        if custom_path:
            # Custom path is relative to the current file's directory
            custom_full_path = os.path.join(current_dir, custom_path)
            if os.path.exists(custom_full_path):
                return os.path.abspath(custom_full_path)
            else:
                location_str = f"{current_file}:{line_number}" if line_number else current_file
                click.echo(
                    f"❌ Error: Custom path '{custom_path}' for module '{module_name}' not found",
                    err=True
                )
                click.echo(f"   Referenced in: {location_str}", err=True)
                click.echo(f"   Looked for: {custom_full_path}", err=True)
                return None

        # Standard module resolution
        search_paths: List[str] = [current_dir] + include_paths

        for path in search_paths:
            # Try module_name.rs
            candidate1: str = os.path.join(path, f"{module_name}.rs")
            if os.path.exists(candidate1):
                return os.path.abspath(candidate1)

            # Try module_name/mod.rs
            candidate2: str = os.path.join(path, module_name, "mod.rs")
            if os.path.exists(candidate2):
                return os.path.abspath(candidate2)

        # Module not found
        location_str = f"{current_file}:{line_number}" if line_number else current_file
        click.echo(
            f"❌ Error: Could not find module '{module_name}'", err=True
        )
        click.echo(f"   Referenced in: {location_str}", err=True)
        searched_paths = '\n    '.join([os.path.abspath(path) for path in search_paths])
        click.echo(f"   Searched in:\n    {searched_paths}", err=True)
        click.echo(
            f"   Hint: Ensure {module_name}.rs or {module_name}/mod.rs exists",
            err=True
        )
        return None

    def _inject_tunable_params(self, content: str, defines: Dict[str, str]) -> str:
        """
        Replace values of tunable parameters marked with // @tune.

        Args:
            content: Source code content
            defines: Dictionary of parameter names to replacement values

        Returns:
            Content with tunable parameter values replaced
        """
        # Pattern to match: const NAME: TYPE = VALUE; // @tune
        # Captures: NAME, TYPE, VALUE
        pattern = r'(const\s+)(\w+)(\s*:\s*[^=]+\s*=\s*)([^;]+)(;\s*//\s*@tune)'

        def replace_value(match):
            prefix = match.group(1)  # const
            name = match.group(2)     # NAME
            type_and_eq = match.group(3)  # : TYPE =
            old_value = match.group(4).strip()  # VALUE
            suffix = match.group(5)   # ; // @tune

            if name in defines:
                new_value = defines[name]
                click.echo(f"  {name}: {old_value} -> {new_value}")
                return f"{prefix}{name}{type_and_eq}{new_value}{suffix}"
            return match.group(0)  # No replacement

        return re.sub(pattern, replace_value, content)

    def get_supported_languages(self) -> List[str]:
        """Return list of supported language file extensions."""
        return ["rust", "rs"]


class RustMinifier(BaseMinifier):
    """Rust code minifier (placeholder for future implementation)."""

    def minify(self, file_path: str) -> str:
        """Minify Rust code by removing comments and excess whitespace."""
        with open(file_path, 'r') as f:
            content = f.read()

        # Use StringLiteralProtector to safely handle string literals
        with StringLiteralProtector(content) as protected:
            # Remove single-line comments (safe because strings are protected)
            protected.working_content = re.sub(r'//.*$', '', protected.working_content, flags=re.MULTILINE)
            # Remove multi-line comments
            protected.working_content = re.sub(r'/\*.*?\*/', '', protected.working_content, flags=re.DOTALL)
            
            # Remove leading/trailing whitespace from each line and compress whitespace
            lines = protected.working_content.split('\n')
            minified_lines = []

            for line in lines:
                line = line.strip()
                if line:
                    # Compress multiple spaces into single space
                    line = re.sub(r'\s+', ' ', line)
                    # Remove spaces around operators and punctuation
                    line = re.sub(r'\s*([{}()\[\];,:])\s*', r'\1', line)
                    # Remove spaces around operators
                    line = re.sub(r'\s*([+\-*/%=<>!&|^])\s*', r'\1', line)
                    minified_lines.append(line)

            protected.working_content = '\n'.join(minified_lines)
            
            # Restore string literals
            result = protected.working_content
            for i, literal in enumerate(protected.string_literals):
                result = result.replace(f"__STRING_LITERAL_{i}__", literal)

        return result

    def get_supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return ["rust", "rs"]
