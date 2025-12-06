import click
import os
import re
import subprocess
from collections import defaultdict
from typing import List, Tuple, Dict, Set, Optional
from base_interfaces import BasePreprocessor, BaseMinifier
from preprocessing_utils import topological_sort_files, StringLiteralProtector, report_circular_dependency_error


class RustPreprocessor(BasePreprocessor):
    """Rust preprocessor for flattening multi-file projects into single submission files."""

    def preprocess(self, file_path: str, include_paths: List[str]) -> str:
        """
        Preprocess a Rust project by flattening modules into a single file.

        Args:
            file_path: Path to the entry file (main.rs or lib.rs)
            include_paths: Additional paths to search for modules

        Returns:
            Flattened Rust code as a single string
        """
        click.echo(f"Preprocessing {file_path}")

        # Setup include paths
        all_include_paths: List[str] = list(include_paths)
        file_dir: str = os.path.dirname(file_path)
        if file_dir not in all_include_paths:
            all_include_paths.insert(0, file_dir)

        # Discover all modules
        all_files_result = self._discover_modules(file_path, all_include_paths)

        if all_files_result is None:
            # Module discovery failed
            return ""

        all_files: Set[str] = all_files_result

        # Build dependency graph
        graph, in_degree = self._build_dependency_graph(list(all_files), all_include_paths)

        # Topological sort
        sorted_files, cycle_files = topological_sort_files(graph, in_degree, list(all_files))

        if sorted_files:
            # Combine files in dependency order
            combined_content: str = ""
            mod_regex: re.Pattern = re.compile(r'^\s*(?:pub\s+)?mod\s+\w+\s*;.*\n?', re.MULTILINE)
            # Remove use statements that reference internal modules (simplified approach)
            # This will remove entire lines like: use utils::math::{gcd, lcm};
            # For competitive programming, we can be aggressive here
            use_regex: re.Pattern = re.compile(r'^\s*use\s+(?!std|core|alloc)\w+::.*\n?', re.MULTILINE)
            # Remove module qualifiers like utils:: from function calls
            qualifier_regex: re.Pattern = re.compile(r'\b\w+::(?=\w+)', re.MULTILINE)

            # Regex to match #[path = "..."] attributes (to remove them after processing)
            path_attr_regex: re.Pattern = re.compile(r'#\[path\s*=\s*"[^"]+"\]\s*\n?', re.MULTILINE)

            for f in sorted_files:
                with open(f, 'r') as source_file:
                    source_content: str = source_file.read()
                    # Remove mod declarations (they're being inlined)
                    source_content = mod_regex.sub("", source_content)
                    # Remove #[path = "..."] attributes (after we've used them)
                    source_content = path_attr_regex.sub("", source_content)
                    # Remove internal use statements (but keep std, core, alloc)
                    source_content = use_regex.sub("", source_content)
                    combined_content += source_content + "\n"

            # Remove module qualifiers (utils::, math::, etc.) from the combined content
            # Keep std::, core::, alloc:: qualifiers
            # This regex matches module_name:: but not std::, core::, or alloc::
            def keep_std_qualifiers(match):
                qualifier = match.group(1)
                if qualifier in ('std', 'core', 'alloc'):
                    return match.group(0)  # Keep it
                return ''  # Remove it

            combined_content = re.sub(r'\b(\w+)::(?=\w)', keep_std_qualifiers, combined_content)

            # Phase 2: Const/static inlining
            const_values = self._extract_const_values(combined_content)
            combined_content = self._inline_const_values(combined_content, const_values)

            # Format output with rustfmt if available
            try:
                temp_file_path: str = "temp_combined.rs"
                with open(temp_file_path, "w") as f:
                    f.write(combined_content)

                result = subprocess.run(
                    ['rustfmt', temp_file_path],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    with open(temp_file_path, "r") as f:
                        combined_content = f.read()

                os.remove(temp_file_path)
            except (FileNotFoundError, subprocess.SubprocessError):
                # rustfmt not available, use unformatted output
                pass

            return combined_content
        else:
            # Report circular dependency error
            report_circular_dependency_error(cycle_files, language="Rust")
            return ""

    def _discover_modules(self, file_path: str, include_paths: List[str]) -> Optional[Set[str]]:
        """
        Discover all modules referenced via 'mod' declarations.

        Supports:
        - Standard mod declarations: mod utils;
        - Custom paths: #[path = "my_file.rs"] mod utils;

        Args:
            file_path: Starting file path
            include_paths: Directories to search for modules

        Returns:
            Set of absolute file paths for all discovered modules, or None on error
        """
        all_files: Set[str] = {os.path.abspath(file_path)}
        # Match: mod module_name; or pub mod module_name;
        # Note: This won't match inline modules like "mod utils { ... }"
        mod_regex: re.Pattern = re.compile(r'^\s*(?:pub\s+)?mod\s+(\w+)\s*;', re.MULTILINE)
        # Match: #[path = "custom/path.rs"] appearing before mod declaration
        path_attr_regex: re.Pattern = re.compile(r'#\[path\s*=\s*"([^"]+)"\]', re.MULTILINE)
        # Match: #[cfg(...)] appearing before mod declaration
        cfg_attr_regex: re.Pattern = re.compile(r'#\[cfg\([^)]+\)\]', re.MULTILINE)

        files_to_scan: List[str] = [file_path]

        while files_to_scan:
            current_file: str = files_to_scan.pop(0)
            with open(current_file, 'r') as f:
                content: str = f.read()

            # Find all mod declarations with their positions
            for match in mod_regex.finditer(content):
                module_name: str = match.group(1)
                custom_path: Optional[str] = None

                # Calculate line number for error reporting
                line_number = content[:match.start()].count('\n') + 1

                # Check if there's a #[cfg(...)] attribute before this mod declaration
                # If so, skip this module (it's conditionally compiled)
                content_before_mod = content[:match.start()]
                cfg_matches = list(cfg_attr_regex.finditer(content_before_mod))
                if cfg_matches:
                    last_cfg_match = cfg_matches[-1]
                    # If #[cfg] is within 100 chars of mod declaration, skip this module
                    if match.start() - last_cfg_match.end() < 100:
                        # Skip cfg-gated modules - they should be preserved as-is
                        continue

                # Check if there's a #[path = "..."] attribute before this mod declaration
                # Look backwards from the mod declaration
                # Find the last #[path = "..."] in the content before this mod
                path_matches = list(path_attr_regex.finditer(content_before_mod))
                if path_matches:
                    # Check if the #[path = ...] is close to the mod (within ~100 chars)
                    last_path_match = path_matches[-1]
                    if match.start() - last_path_match.end() < 100:
                        custom_path = last_path_match.group(1)

                module_file: Optional[str] = self._resolve_module_path(
                    module_name, current_file, include_paths, custom_path, line_number
                )

                if module_file is None:
                    # Module not found - return None to indicate error
                    return None

                if module_file not in all_files:
                    all_files.add(module_file)
                    files_to_scan.append(module_file)

        return all_files

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

    def _build_dependency_graph(
        self, files: List[str], include_paths: List[str]
    ) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """
        Build a dependency graph for the modules.

        Args:
            files: List of all module file paths
            include_paths: Directories to search for modules

        Returns:
            Tuple of (graph, in_degree) where:
            - graph[A] = [B, C] means A is imported by B and C
            - in_degree[B] = N means B depends on N other modules
        """
        graph: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = defaultdict(int)

        mod_regex: re.Pattern = re.compile(r'^\s*(?:pub\s+)?mod\s+(\w+)\s*;', re.MULTILINE)
        path_attr_regex: re.Pattern = re.compile(r'#\[path\s*=\s*"([^"]+)"\]', re.MULTILINE)
        cfg_attr_regex: re.Pattern = re.compile(r'#\[cfg\([^)]+\)\]', re.MULTILINE)

        for file_path in files:
            if not os.path.exists(file_path):
                continue

            with open(file_path, 'r') as f:
                content: str = f.read()

            for match in mod_regex.finditer(content):
                module_name: str = match.group(1)
                custom_path: Optional[str] = None

                # Calculate line number for error reporting
                line_number = content[:match.start()].count('\n') + 1

                # Check if there's a #[cfg(...)] attribute before this mod declaration
                # If so, skip this module (it's conditionally compiled)
                content_before_mod = content[:match.start()]
                cfg_matches = list(cfg_attr_regex.finditer(content_before_mod))
                if cfg_matches:
                    last_cfg_match = cfg_matches[-1]
                    if match.start() - last_cfg_match.end() < 100:
                        # Skip cfg-gated modules
                        continue

                # Check for #[path = "..."] attribute before this mod
                path_matches = list(path_attr_regex.finditer(content_before_mod))
                if path_matches:
                    last_path_match = path_matches[-1]
                    if match.start() - last_path_match.end() < 100:
                        custom_path = last_path_match.group(1)

                module_file: Optional[str] = self._resolve_module_path(
                    module_name, file_path, include_paths, custom_path, line_number
                )

                if module_file:
                    # module_file is depended upon by file_path
                    graph[module_file].append(os.path.abspath(file_path))
                    in_degree[os.path.abspath(file_path)] += 1

        return graph, in_degree

    def _extract_const_values(self, content: str) -> Dict[str, str]:
        """
        Extract const and static declarations and their values.
        
        Protects string literals to avoid extracting fake const declarations from strings.

        Args:
            content: Source code content

        Returns:
            Dictionary mapping const/static names to their values
        """
        const_map: Dict[str, str] = {}

        # Protect string literals before extracting const values
        # This prevents extracting fake const declarations from strings
        with StringLiteralProtector(content) as protected:
            # Work with protected content (strings replaced with placeholders)
            protected_content = protected.working_content
            
            # Match: const NAME: TYPE = VALUE;
            # Type pattern: match anything up to the = sign (handles &str, &'static str, *const T, etc.)
            const_pattern = r'const\s+([A-Z_][A-Z0-9_]*)\s*:\s*[^=]+\s*=\s*([^;]+);'

            for match in re.finditer(const_pattern, protected_content, re.MULTILINE):
                name = match.group(1)
                value = match.group(2).strip()
                # Restore string literals in the value using replace (which restores strings)
                for i, literal in enumerate(protected.string_literals):
                    value = value.replace(f"__STRING_LITERAL_{i}__", literal)
                const_map[name] = value

            # Also handle static
            # Same flexible type pattern
            static_pattern = r'static\s+([A-Z_][A-Z0-9_]*)\s*:\s*[^=]+\s*=\s*([^;]+);'

            for match in re.finditer(static_pattern, protected_content, re.MULTILINE):
                name = match.group(1)
                value = match.group(2).strip()
                # Restore string literals in the value
                for i, literal in enumerate(protected.string_literals):
                    value = value.replace(f"__STRING_LITERAL_{i}__", literal)
                const_map[name] = value

        return const_map

    def _inline_const_values(self, content: str, const_map: Dict[str, str]) -> str:
        """
        Replace const/static references with their literal values.
        
        Protects string literals during both removal and replacement.

        Args:
            content: Source code content
            const_map: Dictionary mapping names to values

        Returns:
            Content with const values inlined
        """
        if not const_map:
            return content

        # Use StringLiteralProtector to safely remove const/static declarations
        # This prevents removing declarations from inside string literals
        with StringLiteralProtector(content) as protected:
            # Remove const/static declarations from protected content
            # Type pattern: match anything up to the = sign (handles &str, &'static str, *const T, etc.)
            protected.working_content = re.sub(
                r'const\s+[A-Z_][A-Z0-9_]*\s*:\s*[^=]+\s*=\s*[^;]+;\n?',
                '',
                protected.working_content
            )
            protected.working_content = re.sub(
                r'static\s+[A-Z_][A-Z0-9_]*\s*:\s*[^=]+\s*=\s*[^;]+;\n?',
                '',
                protected.working_content
            )
            
            # Replace const names with their values (strings still protected)
            for name, value in const_map.items():
                # Use word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(name) + r'\b'
                protected.working_content = re.sub(pattern, value, protected.working_content)
            
            # Restore string literals
            result = protected.working_content
            for i, literal in enumerate(protected.string_literals):
                result = result.replace(f"__STRING_LITERAL_{i}__", literal)
            
            return result

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
