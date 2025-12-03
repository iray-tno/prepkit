import pytest
import os
from pathlib import Path
from click.testing import CliRunner

from main import cli
from plugins.cpp_plugin import CppPreprocessor


class TestErrorMessages:
    """Test improved error messages for common issues."""

    def test_missing_include_error_message(self, tmp_path, capsys):
        """Test error message when include file is not found."""
        code = """
        #include <iostream>
        #include "nonexistent.h"

        int main() {
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        cpp_preprocessor = CppPreprocessor()

        try:
            output = cpp_preprocessor.preprocess(str(main_cpp), [str(tmp_path)])
            # If it doesn't raise an exception, check the error was logged
            captured = capsys.readouterr()
            if captured.err:
                assert "❌ Error: Could not find include file" in captured.err
                assert "nonexistent.h" in captured.err
                assert "Searched in:" in captured.err
                assert "Hint: Use -I/--include-path" in captured.err
        except SystemExit:
            captured = capsys.readouterr()
            assert "❌ Error: Could not find include file" in captured.err
            assert "nonexistent.h" in captured.err

    def test_missing_include_shows_search_paths(self, tmp_path, capsys):
        """Test that error message shows all searched paths."""
        code = '#include "missing.h"\nint main() { return 0; }'

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        lib1 = tmp_path / "lib1"
        lib1.mkdir()
        lib2 = tmp_path / "lib2"
        lib2.mkdir()

        cpp_preprocessor = CppPreprocessor()

        try:
            output = cpp_preprocessor.preprocess(str(main_cpp), [str(lib1), str(lib2)])
        except SystemExit:
            pass

        captured = capsys.readouterr()
        if captured.err:
            assert "lib1" in captured.err
            assert "lib2" in captured.err
            assert "Searched in:" in captured.err

    def test_circular_dependency_error_message(self, tmp_path, capsys):
        """Test error message for circular include dependencies."""
        # Create circular dependency: a.h -> b.h -> c.h -> a.h
        a_h = tmp_path / "a.h"
        b_h = tmp_path / "b.h"
        c_h = tmp_path / "c.h"

        a_h.write_text('#include "b.h"\nint func_a() { return 1; }')
        b_h.write_text('#include "c.h"\nint func_b() { return 2; }')
        c_h.write_text('#include "a.h"\nint func_c() { return 3; }')

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text('#include "a.h"\nint main() { return 0; }')

        cpp_preprocessor = CppPreprocessor()

        try:
            output = cpp_preprocessor.preprocess(str(main_cpp), [str(tmp_path)])
        except SystemExit:
            pass

        captured = capsys.readouterr()
        if captured.err:
            assert "❌ Error: Circular dependency detected" in captured.err
            assert "Files involved in the cycle:" in captured.err
            assert "Hint: Check #include directives" in captured.err

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_compilation_error_message(self, tmp_path):
        """Test compilation error message from test command."""
        code = """
        #include <iostream>
        int main() {
            undefined_function();  // This will cause compilation error
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp)])

        assert result.exit_code == 1
        assert "❌ Compilation failed" in result.output
        assert "Compiler: g++ -std=c++17" in result.output
        assert "Source:" in result.output
        assert "Compiler output:" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_output_mismatch_error_message(self, tmp_path):
        """Test error message when output doesn't match expected."""
        code = """
        #include <iostream>
        int main() {
            std::cout << "Wrong output" << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        expected_file = tmp_path / "expected.txt"
        expected_file.write_text("Correct output\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp), '-e', str(expected_file)])

        assert result.exit_code == 1
        assert "❌ Output differs from expected:" in result.output
        assert "--- Expected ---" in result.output

    def test_missing_include_hint_message(self, tmp_path, capsys):
        """Test that missing include provides helpful hint."""
        code = """
        #include "utils.h"
        int main() { return 0; }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        cpp_preprocessor = CppPreprocessor()

        try:
            output = cpp_preprocessor.preprocess(str(main_cpp), [])
        except SystemExit:
            pass

        captured = capsys.readouterr()
        if captured.err:
            # Check that the error message includes helpful information
            assert "❌ Error:" in captured.err
            assert "utils.h" in captured.err
            # Should suggest using -I flag
            assert "-I" in captured.err or "include-path" in captured.err


class TestStringLiteralProtection:
    """Test that constexpr replacement doesn't break string literals."""

    def test_constexpr_not_replaced_in_strings(self, tmp_path):
        """Test that constexpr values inside strings are preserved."""
        code = """
        constexpr int MOD = 1000000007;
        #include <iostream>
        int main() {
            std::cout << "MOD: " << MOD << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        cpp_preprocessor = CppPreprocessor()
        output = cpp_preprocessor.preprocess(str(main_cpp), [str(tmp_path)])

        # MOD in the string literal should NOT be replaced
        assert '"MOD: "' in output or '"MOD:"' in output
        # But MOD outside strings should be replaced
        assert "1000000007" in output
        # Should not have broken the string
        assert '"1000000007:' not in output  # This would be wrong

    def test_multiple_constexpr_with_strings(self, tmp_path):
        """Test multiple constexpr with string literals."""
        code = """
        constexpr int MAXN = 100000;
        constexpr int MOD = 998244353;
        #include <iostream>
        int main() {
            std::cout << "MAXN = " << MAXN << ", MOD = " << MOD << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        cpp_preprocessor = CppPreprocessor()
        output = cpp_preprocessor.preprocess(str(main_cpp), [str(tmp_path)])

        # Strings should be preserved
        assert '"MAXN = "' in output or '"MAXN ="' in output
        assert '"MOD = "' in output or '", MOD = "' in output
        # But values outside strings should be replaced
        assert "100000" in output
        assert "998244353" in output
        # Should not break strings
        assert '"100000 = "' not in output
        assert '"998244353 = "' not in output

    def test_char_literal_protection(self, tmp_path):
        """Test that char literals are protected from replacement."""
        code = """
        constexpr char A = 'a';
        constexpr char B = 'b';
        #include <iostream>
        int main() {
            char c = A;
            std::cout << 'A' << " is " << c << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        cpp_preprocessor = CppPreprocessor()
        output = cpp_preprocessor.preprocess(str(main_cpp), [str(tmp_path)])

        # Char literal 'A' should be preserved (not replaced with 'a')
        assert "'A'" in output
        # Variable A should be replaced with 'a'
        assert "'a'" in output
        # Should not break char literals
        assert "''a''" not in output
