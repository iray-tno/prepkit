"""Shared utilities for preprocessors (C++, Rust, etc.)."""
import os
import re
import click
from collections import deque
from typing import Dict, List, Tuple, Optional


def topological_sort_files(
    graph: Dict[str, List[str]],
    in_degree: Dict[str, int],
    all_files: List[str]
) -> Tuple[Optional[List[str]], List[str]]:
    """
    Perform topological sort on file dependencies.

    This function sorts files based on their dependencies, ensuring that
    files with no dependencies come first, followed by their dependents.
    Handles circular dependency detection.

    Args:
        graph: Dependency graph where graph[A] = [B, C] means A is imported by B and C
        in_degree: Number of dependencies for each file
        all_files: List of all files to sort

    Returns:
        Tuple of (sorted_files, cycle_files) where:
        - sorted_files: List of files in dependency order (None if cycle detected)
        - cycle_files: Files involved in circular dependency (empty list if no cycle)

    Example:
        >>> graph = {'/a.rs': ['/b.rs'], '/b.rs': ['/c.rs']}
        >>> in_degree = {'/a.rs': 0, '/b.rs': 1, '/c.rs': 1}
        >>> all_files = ['/a.rs', '/b.rs', '/c.rs']
        >>> sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)
        >>> sorted_files
        ['/a.rs', '/b.rs', '/c.rs']
    """
    # Sort initial nodes for deterministic ordering
    initial_nodes = sorted([f for f in all_files if in_degree[os.path.abspath(f)] == 0])
    queue: deque[str] = deque(initial_nodes)
    sorted_order: List[str] = []

    while queue:
        node: str = queue.popleft()
        sorted_order.append(node)

        # Collect neighbors that become ready
        neighbors_ready = []
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                neighbors_ready.append(neighbor)

        # Add sorted neighbors to maintain deterministic order
        for neighbor in sorted(neighbors_ready):
            queue.append(neighbor)

    if len(sorted_order) == len(all_files):
        return sorted_order, []
    else:
        # Files not in sorted_order are part of the cycle
        cycle_files = [f for f in all_files if os.path.abspath(f) not in sorted_order]
        return None, cycle_files


class StringLiteralProtector:
    """
    Context manager for protecting string literals during text replacement.

    This prevents unwanted replacements inside string literals when doing
    const/constexpr value inlining or other text-based substitutions.

    Usage:
        >>> content = 'const MAX = 100; std::cout << "MAX is 100";'
        >>> with StringLiteralProtector(content) as protected:
        ...     result = protected.replace("MAX", "200")
        >>> result
        'const 200 = 100; std::cout << "MAX is 100";'

    The string literal "MAX is 100" is preserved while the identifier MAX is replaced.
    """

    def __init__(self, content: str):
        """
        Initialize the protector with content.

        Args:
            content: Source code content to protect
        """
        self.original_content = content
        self.working_content = content
        self.string_literals: List[str] = []

    def __enter__(self) -> 'StringLiteralProtector':
        """
        Enter context manager and protect string literals.

        Returns:
            Self with protected content
        """
        def save_string(match):
            self.string_literals.append(match.group(0))
            return f"__STRING_LITERAL_{len(self.string_literals) - 1}__"

        # Save string literals (both double and single quoted)
        self.working_content = re.sub(r'"(?:[^"\\]|\\.)*"', save_string, self.working_content)
        self.working_content = re.sub(r"'(?:[^'\\]|\\.)*'", save_string, self.working_content)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager (no cleanup needed)."""
        pass

    def replace(self, old: str, new: str, use_word_boundaries: bool = True) -> str:
        """
        Replace text in protected content.

        This method works on the working content and returns a new result each time.
        For chained replacements, call this method multiple times and use the result
        from each call.

        Args:
            old: Text to replace
            new: Replacement text
            use_word_boundaries: If True, only replace whole words (default: True)

        Returns:
            Content with replacements applied and string literals restored
        """
        # Perform replacement on working content
        if use_word_boundaries:
            # Use regex to replace only whole words, avoiding placeholders
            pattern = r'\b' + re.escape(old) + r'\b'
            self.working_content = re.sub(pattern, new, self.working_content)
        else:
            self.working_content = self.working_content.replace(old, new)

        # Create result with string literals restored
        result = self.working_content
        for i, literal in enumerate(self.string_literals):
            result = result.replace(f"__STRING_LITERAL_{i}__", literal)

        return result


def report_circular_dependency_error(cycle_files: List[str], language: str = ""):
    """
    Report circular dependency error to stderr with helpful formatting.

    Args:
        cycle_files: List of file paths involved in the circular dependency
        language: Programming language name (for context in error message)

    Example:
        >>> report_circular_dependency_error(['/path/a.rs', '/path/b.rs'], 'Rust')
        # Outputs to stderr:
        # ❌ Error: Circular dependency detected in Rust module files
        #    Files involved in the cycle:
        #     • a.rs (/path/a.rs)
        #     • b.rs (/path/b.rs)
        #    Hint: Check mod declarations in these files for circular references
    """
    file_type = f"{language} module " if language else ""
    click.echo(f"❌ Error: Circular dependency detected in {file_type}files", err=True)
    click.echo("   Files involved in the cycle:", err=True)

    for cycle_file in cycle_files:
        basename = os.path.basename(cycle_file)
        click.echo(f"    • {basename} ({cycle_file})", err=True)

    if language:
        if language.lower() == "rust":
            hint = "Check mod declarations in these files for circular references"
        elif language.lower() in ["c++", "cpp", "c"]:
            hint = "Check #include directives in these files for circular references"
        else:
            hint = "Check import/include statements in these files for circular references"
    else:
        hint = "Check dependencies in these files for circular references"

    click.echo(f"   Hint: {hint}", err=True)
