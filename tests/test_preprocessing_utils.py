"""Unit tests for shared preprocessing utilities."""
import pytest
from collections import defaultdict
from preprocessing_utils import (
    topological_sort_files,
    StringLiteralProtector,
    report_circular_dependency_error
)


class TestTopologicalSort:
    """Test topological sort utility for dependency resolution."""

    def test_simple_linear_dependency(self):
        """Test simple A -> B -> C dependency chain."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # A depends on nothing, B depends on A, C depends on B
        graph["/path/a.rs"] = ["/path/b.rs"]
        graph["/path/b.rs"] = ["/path/c.rs"]
        in_degree["/path/a.rs"] = 0
        in_degree["/path/b.rs"] = 1
        in_degree["/path/c.rs"] = 1

        all_files = ["/path/a.rs", "/path/b.rs", "/path/c.rs"]

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files is not None
        assert cycle_files == []
        assert sorted_files == ["/path/a.rs", "/path/b.rs", "/path/c.rs"]

    def test_multiple_independent_files(self):
        """Test files with no dependencies."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        all_files = ["/path/a.rs", "/path/b.rs", "/path/c.rs"]
        for f in all_files:
            in_degree[f] = 0

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files is not None
        assert cycle_files == []
        assert len(sorted_files) == 3
        # All files should be present (order doesn't matter for independent files)
        assert set(sorted_files) == set(all_files)

    def test_diamond_dependency(self):
        """Test diamond dependency: A -> B, A -> C, B -> D, C -> D."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # A is root, B and C depend on A, D depends on both B and C
        graph["/path/a.rs"] = ["/path/b.rs", "/path/c.rs"]
        graph["/path/b.rs"] = ["/path/d.rs"]
        graph["/path/c.rs"] = ["/path/d.rs"]
        in_degree["/path/a.rs"] = 0
        in_degree["/path/b.rs"] = 1
        in_degree["/path/c.rs"] = 1
        in_degree["/path/d.rs"] = 2

        all_files = ["/path/a.rs", "/path/b.rs", "/path/c.rs", "/path/d.rs"]

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files is not None
        assert cycle_files == []
        # A must come first, D must come last
        assert sorted_files[0] == "/path/a.rs"
        assert sorted_files[-1] == "/path/d.rs"

    def test_circular_dependency_two_files(self):
        """Test circular dependency: A -> B -> A."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # A depends on B, B depends on A (circular!)
        graph["/path/a.rs"] = ["/path/b.rs"]
        graph["/path/b.rs"] = ["/path/a.rs"]
        in_degree["/path/a.rs"] = 1
        in_degree["/path/b.rs"] = 1

        all_files = ["/path/a.rs", "/path/b.rs"]

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files is None
        assert len(cycle_files) == 2
        assert set(cycle_files) == {"/path/a.rs", "/path/b.rs"}

    def test_circular_dependency_three_files(self):
        """Test circular dependency: A -> B -> C -> A."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # A -> B -> C -> A (circular!)
        graph["/path/a.rs"] = ["/path/b.rs"]
        graph["/path/b.rs"] = ["/path/c.rs"]
        graph["/path/c.rs"] = ["/path/a.rs"]
        in_degree["/path/a.rs"] = 1
        in_degree["/path/b.rs"] = 1
        in_degree["/path/c.rs"] = 1

        all_files = ["/path/a.rs", "/path/b.rs", "/path/c.rs"]

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files is None
        assert len(cycle_files) == 3

    def test_deterministic_ordering(self):
        """Test that sorting is deterministic for same-level dependencies."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        # All files depend on root
        root = "/path/root.rs"
        graph[root] = ["/path/z.rs", "/path/a.rs", "/path/m.rs"]
        in_degree[root] = 0
        in_degree["/path/a.rs"] = 1
        in_degree["/path/m.rs"] = 1
        in_degree["/path/z.rs"] = 1

        all_files = [root, "/path/z.rs", "/path/a.rs", "/path/m.rs"]

        # Run multiple times to verify determinism
        results = []
        for _ in range(5):
            sorted_files, _ = topological_sort_files(graph.copy(), in_degree.copy(), all_files)
            results.append(sorted_files)

        # All results should be identical
        assert all(r == results[0] for r in results)
        # Root should be first
        assert results[0][0] == root
        # Files at same level should be sorted alphabetically
        assert results[0][1:] == sorted(["/path/a.rs", "/path/m.rs", "/path/z.rs"])

    def test_empty_graph(self):
        """Test empty dependency graph."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        all_files = []

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files == []
        assert cycle_files == []

    def test_single_file(self):
        """Test graph with single file."""
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        in_degree["/path/main.rs"] = 0
        all_files = ["/path/main.rs"]

        sorted_files, cycle_files = topological_sort_files(graph, in_degree, all_files)

        assert sorted_files == ["/path/main.rs"]
        assert cycle_files == []


class TestStringLiteralProtector:
    """Test string literal protection utility."""

    def test_protect_double_quotes(self):
        """Test protection of double-quoted strings."""
        content = 'const MAX_N = 100; std::cout << "MAX_N is 100";'

        with StringLiteralProtector(content) as protected:
            # Replace MAX_N in protected content
            result = protected.replace("MAX_N", "200")

        # MAX_N in string should be preserved, outside should be replaced
        assert '"MAX_N is 100"' in result
        assert "const 200" in result

    def test_protect_single_quotes(self):
        """Test protection of single-quoted strings (char literals)."""
        content = "const CHAR = 'A'; char c = 'A';"

        with StringLiteralProtector(content) as protected:
            result = protected.replace("CHAR", "LETTER")

        assert "'A'" in result
        assert "const LETTER" in result

    def test_protect_escaped_quotes(self):
        """Test protection of strings with escaped quotes."""
        content = r'std::cout << "He said \"MAX_N\""; const MAX_N = 100;'

        with StringLiteralProtector(content) as protected:
            result = protected.replace("MAX_N", "200")

        # String should be preserved with escaped quotes
        assert r'"He said \"MAX_N\""' in result
        assert "const 200" in result

    def test_multiple_replacements(self):
        """Test multiple replacements with string protection."""
        content = 'const A = 1; const B = 2; std::cout << "A and B";'

        with StringLiteralProtector(content) as protected:
            protected.replace("A", "10")  # First replacement
            result = protected.replace("B", "20")  # Second replacement

        assert '"A and B"' in result
        assert "const 10" in result
        assert "const 20" in result

    def test_empty_string(self):
        """Test empty string handling."""
        content = 'const VAL = ""; const VAL2 = 42;'

        with StringLiteralProtector(content) as protected:
            result = protected.replace("VAL", "VALUE")

        assert '""' in result
        assert "const VALUE" in result

    def test_multiline_strings(self):
        """Test protection of multiline content with strings."""
        content = '''const MAX = 100;
std::string msg = "MAX value is 100";
int val = MAX;'''

        with StringLiteralProtector(content) as protected:
            result = protected.replace("MAX", "200")

        # String should preserve MAX, but declarations should replace it
        assert '"MAX value is 100"' in result
        assert "const 200" in result
        assert "int val = 200" in result

    def test_no_strings(self):
        """Test content with no string literals."""
        content = "const A = 1; const B = 2; int sum = A + B;"

        with StringLiteralProtector(content) as protected:
            result = protected.replace("A", "10")

        assert "const 10" in result
        assert "sum = 10" in result

    def test_adjacent_strings(self):
        """Test multiple adjacent string literals."""
        content = 'const X = "a" "b" "c"; const Y = 42;'

        with StringLiteralProtector(content) as protected:
            result = protected.replace("X", "TEXT")

        assert '"a"' in result
        assert '"b"' in result
        assert '"c"' in result
        assert "const TEXT" in result


class TestCircularDependencyError:
    """Test circular dependency error reporting."""

    def test_error_message_format(self, capsys):
        """Test that error message is formatted correctly."""
        cycle_files = [
            "/home/user/project/a.rs",
            "/home/user/project/b.rs",
            "/home/user/project/c.rs"
        ]

        report_circular_dependency_error(cycle_files, language="Rust")

        captured = capsys.readouterr()
        assert "Circular dependency detected" in captured.err
        assert "a.rs" in captured.err
        assert "b.rs" in captured.err
        assert "c.rs" in captured.err

    def test_error_shows_basenames(self, capsys):
        """Test that error shows file basenames for readability."""
        cycle_files = ["/very/long/path/to/file/a.cpp"]

        report_circular_dependency_error(cycle_files, language="C++")

        captured = capsys.readouterr()
        assert "a.cpp" in captured.err

    def test_error_with_hint(self, capsys):
        """Test that error includes helpful hint."""
        cycle_files = ["/path/a.rs", "/path/b.rs"]

        report_circular_dependency_error(cycle_files, language="Rust")

        captured = capsys.readouterr()
        assert "Hint" in captured.err or "hint" in captured.err

    def test_empty_cycle_files(self, capsys):
        """Test handling of empty cycle files list."""
        report_circular_dependency_error([], language="Rust")

        captured = capsys.readouterr()
        # Should still show error message
        assert "Circular dependency" in captured.err
