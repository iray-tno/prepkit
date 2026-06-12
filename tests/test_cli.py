import pytest
import os
import tempfile
import yaml
from pathlib import Path
from click.testing import CliRunner

from main import cli
from config import load_config


class TestConfigLoading:
    """Test prepkit_config.yaml loading functionality."""

    def test_load_config_file_exists(self, tmp_path, monkeypatch):
        """Test loading a valid config file."""
        config_data = {
            "project_type": "atcoder-algorithm",
            "cpp_preprocess": {
                "include_paths": ["./lib", "./includes"],
                "minify_output": False
            },
            "cpp_compile": {
                "std": "c++20",
                "flags": ["-O2", "-Wall"]
            },
            "test": {
                "timeout": 10,
                "input_file": "input.txt",
                "expected_file": "expected.txt"
            }
        }

        config_file = tmp_path / "prepkit_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # Change to the temp directory
        monkeypatch.chdir(tmp_path)

        # Load config
        config = load_config()

        assert config["project_type"] == "atcoder-algorithm"
        assert config["cpp_preprocess"]["include_paths"] == ["./lib", "./includes"]
        assert config["cpp_preprocess"]["minify_output"] is False
        assert config["cpp_compile"]["std"] == "c++20"
        assert config["cpp_compile"]["flags"] == ["-O2", "-Wall"]
        assert config["test"]["timeout"] == 10
        assert config["test"]["input_file"] == "input.txt"
        assert config["test"]["expected_file"] == "expected.txt"

    def test_load_config_file_not_exists(self, tmp_path, monkeypatch):
        """Test loading when config file doesn't exist."""
        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config == {}

    def test_load_config_invalid_yaml(self, tmp_path, monkeypatch, capsys):
        """Test loading an invalid YAML file."""
        config_file = tmp_path / "prepkit_config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        monkeypatch.chdir(tmp_path)

        config = load_config()

        # Should return empty dict and print warning
        assert config == {}
        captured = capsys.readouterr()
        assert "Warning: Error reading prepkit_config.yaml" in captured.err

    def test_load_config_empty_file(self, tmp_path, monkeypatch):
        """Test loading an empty config file."""
        config_file = tmp_path / "prepkit_config.yaml"
        config_file.write_text("")

        monkeypatch.chdir(tmp_path)

        config = load_config()

        assert config == {}


class TestCppPreprocessCommand:
    """Test cpp preprocess CLI command."""

    def test_cpp_preprocess_basic(self, tmp_path):
        """Test basic preprocessing without config."""
        # Create test files
        helper_h = tmp_path / "helper.h"
        helper_h.write_text("int add(int a, int b) { return a + b; }")

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text('#include <iostream>\n#include "helper.h"\nint main() { return add(1, 2); }')

        runner = CliRunner()
        result = runner.invoke(cli, ['cpp', 'preprocess', str(main_cpp), '-I', str(tmp_path)])

        assert result.exit_code == 0
        assert "#include <iostream>" in result.output
        assert "int add(int a, int b)" in result.output
        assert '#include "helper.h"' not in result.output

    def test_cpp_preprocess_with_output_flag(self, tmp_path):
        """Test preprocessing with -o/--output flag."""
        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text('#include <iostream>\nint main() { return 0; }')

        output_file = tmp_path / "output.cpp"

        runner = CliRunner()
        result = runner.invoke(cli, ['cpp', 'preprocess', str(main_cpp), '-o', str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "✓ Preprocessed output written to:" in result.output

        content = output_file.read_text()
        assert "#include <iostream>" in content
        assert "int main()" in content

    def test_cpp_preprocess_with_config(self, tmp_path, monkeypatch):
        """Test preprocessing with config file include paths."""
        # Create directory structure
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()

        helper_h = lib_dir / "helper.h"
        helper_h.write_text("int multiply(int a, int b) { return a * b; }")

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text('#include "helper.h"\nint main() { return multiply(2, 3); }')

        # Create config file
        config_data = {
            "cpp_preprocess": {
                "include_paths": ["./lib"]
            }
        }
        config_file = tmp_path / "prepkit_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ['cpp', 'preprocess', str(main_cpp)])

        assert result.exit_code == 0
        assert "Using include paths from config" in result.output
        assert "int multiply(int a, int b)" in result.output


class TestCppMinifyCommand:
    """Test cpp minify CLI command."""

    def test_cpp_minify_basic(self, tmp_path):
        """Test basic minification."""
        code = """
        // This is a comment
        #include <iostream>

        /* Multi-line
         * comment */
        int main() {
            int x = 10; // inline comment
            return x;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        runner = CliRunner()
        result = runner.invoke(cli, ['cpp', 'minify', str(main_cpp)])

        assert result.exit_code == 0
        assert "//" not in result.output or "✓" in result.output  # No comments except status
        assert "/*" not in result.output
        assert "#include <iostream>" in result.output
        assert "int main()" in result.output

    def test_cpp_minify_with_output_flag(self, tmp_path):
        """Test minification with -o/--output flag."""
        code = "// Comment\n#include <iostream>\nint main() { return 0; }"

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        output_file = tmp_path / "minified.cpp"

        runner = CliRunner()
        result = runner.invoke(cli, ['cpp', 'minify', str(main_cpp), '-o', str(output_file)])

        assert result.exit_code == 0
        assert output_file.exists()
        assert "✓ Minified output written to:" in result.output

        content = output_file.read_text()
        assert "//" not in content
        assert "#include <iostream>" in content


class TestProjectCommand:
    """Test project scaffolding behavior."""

    def test_project_new_does_not_generate_mcp_config(self, tmp_path, monkeypatch):
        """Project scaffolding should not advertise or generate MCP config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ['project', 'new', 'sample_project', '--type', 'kaggle'])

        assert result.exit_code == 0
        project_dir = tmp_path / "sample_project"
        assert project_dir.exists()
        assert not (project_dir / ".mcp.json").exists()
        assert "MCP" not in result.output


class TestTestCommand:
    """Test the test command for competitive programming."""

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_test_command_basic(self, tmp_path):
        """Test basic compilation and execution."""
        code = """
        #include <iostream>
        int main() {
            std::cout << "Hello World" << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp)])

        assert result.exit_code == 0
        assert "✓ Compilation successful" in result.output
        assert "Hello World" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_test_command_with_input(self, tmp_path):
        """Test with input file."""
        code = """
        #include <iostream>
        int main() {
            int a, b;
            std::cin >> a >> b;
            std::cout << a + b << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        input_file = tmp_path / "input.txt"
        input_file.write_text("10 20\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp), '-i', str(input_file)])

        assert result.exit_code == 0
        assert "30" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_test_command_with_expected_output(self, tmp_path):
        """Test with expected output comparison."""
        code = """
        #include <iostream>
        int main() {
            int a, b;
            std::cin >> a >> b;
            std::cout << a + b << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        input_file = tmp_path / "input.txt"
        input_file.write_text("10 20\n")

        expected_file = tmp_path / "expected.txt"
        expected_file.write_text("30\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp), '-i', str(input_file), '-e', str(expected_file)])

        assert result.exit_code == 0
        assert "✓ Output matches expected!" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_test_command_with_preprocess(self, tmp_path):
        """Test with preprocessing enabled."""
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()

        helper_h = lib_dir / "helper.h"
        helper_h.write_text("int add(int a, int b) { return a + b; }")

        code = """
        #include <iostream>
        #include "helper.h"
        int main() {
            int a, b;
            std::cin >> a >> b;
            std::cout << add(a, b) << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        input_file = tmp_path / "input.txt"
        input_file.write_text("5 7\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp), '--preprocess', '-I', str(lib_dir), '-i', str(input_file)])

        assert result.exit_code == 0
        assert "Preprocessing..." in result.output
        assert "✓ Compilation successful" in result.output
        assert "12" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_test_command_with_config(self, tmp_path, monkeypatch):
        """Test with config file defaults."""
        code = """
        #include <iostream>
        int main() {
            int a, b;
            std::cin >> a >> b;
            std::cout << a * b << std::endl;
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        input_file = tmp_path / "input.txt"
        input_file.write_text("3 4\n")

        expected_file = tmp_path / "expected.txt"
        expected_file.write_text("12\n")

        # Create config file
        config_data = {
            "test": {
                "timeout": 10,
                "input_file": str(input_file),
                "expected_file": str(expected_file)
            },
            "cpp_compile": {
                "std": "c++17",
                "flags": ["-O2"]
            }
        }
        config_file = tmp_path / "prepkit_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp)])

        assert result.exit_code == 0
        assert "Using input file from config" in result.output
        assert "Using expected file from config" in result.output
        assert "✓ Output matches expected!" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_test_command_compilation_error(self, tmp_path):
        """Test compilation error handling."""
        code = """
        #include <iostream>
        int main() {
            undeclared_variable = 10;  // This will cause compilation error
            return 0;
        }
        """

        main_cpp = tmp_path / "main.cpp"
        main_cpp.write_text(code)

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_cpp)])

        assert result.exit_code == 1
        assert "❌ Compilation failed" in result.output
        assert "Compiler output:" in result.output


class TestVersionFlag:
    """Test version flag functionality."""

    def test_version_short_flag(self):
        """Test -v flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ['-v'])

        assert result.exit_code == 0
        assert "version" in result.output.lower()

    def test_version_long_flag(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])

        assert result.exit_code == 0
        assert "version" in result.output.lower()
