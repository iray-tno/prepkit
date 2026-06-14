"""Tests for the test command with Rust support."""
import pytest
import os
from pathlib import Path
from click.testing import CliRunner
from main import cli


@pytest.mark.skipif(os.system("which rustc > /dev/null 2>&1") != 0, reason="rustc not available")
class TestRustTestCommand:
    """Test the test command with Rust files."""

    def test_rust_basic_compilation(self, tmp_path):
        """Test basic Rust compilation and execution."""
        # Create a simple Rust file
        test_file = tmp_path / "hello.rs"
        test_file.write_text("""
fn main() {
    println!("Hello, World!");
}
""")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file)])

        assert result.exit_code == 0
        assert "Compiling hello.rs..." in result.output
        assert "✓ Compilation successful" in result.output
        assert "Hello, World!" in result.output

    def test_rust_with_input(self, tmp_path):
        """Test Rust execution with input file."""
        # Create a Rust file that reads input
        test_file = tmp_path / "add.rs"
        test_file.write_text("""
use std::io;

fn main() {
    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();
    let nums: Vec<i32> = input
        .trim()
        .split_whitespace()
        .map(|s| s.parse().unwrap())
        .collect();
    println!("{}", nums[0] + nums[1]);
}
""")

        # Create input file
        input_file = tmp_path / "input.txt"
        input_file.write_text("5 3\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file), '-i', str(input_file)])

        assert result.exit_code == 0
        assert "8" in result.output

    def test_rust_with_expected_output(self, tmp_path):
        """Test Rust with expected output verification."""
        # Create a simple Rust file
        test_file = tmp_path / "output.rs"
        test_file.write_text("""
fn main() {
    println!("42");
}
""")

        # Create expected output file
        expected_file = tmp_path / "expected.txt"
        expected_file.write_text("42\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file), '-e', str(expected_file)])

        assert result.exit_code == 0
        assert "✓ Output matches expected!" in result.output

    def test_rust_output_mismatch(self, tmp_path):
        """Test Rust with mismatched expected output."""
        # Create a simple Rust file
        test_file = tmp_path / "output.rs"
        test_file.write_text("""
fn main() {
    println!("42");
}
""")

        # Create expected output file with wrong value
        expected_file = tmp_path / "expected.txt"
        expected_file.write_text("43\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file), '-e', str(expected_file)])

        assert result.exit_code != 0
        assert "❌ Output differs from expected:" in result.output

    def test_rust_compilation_error(self, tmp_path):
        """Test Rust compilation error handling."""
        # Create a Rust file with syntax error
        test_file = tmp_path / "error.rs"
        test_file.write_text("""
fn main() {
    println!("Hello"  // Missing closing parenthesis and semicolon
}
""")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file)])

        assert result.exit_code != 0
        assert "❌ Compilation failed" in result.output

    def test_rust_with_preprocessing(self, tmp_path):
        """Test Rust with preprocessing."""
        # Create a main file
        main_file = tmp_path / "main.rs"
        main_file.write_text("""
mod utils;

fn main() {
    println!("{}", utils::add(5, 3));
}
""")

        # Create a utils module
        utils_file = tmp_path / "utils.rs"
        utils_file.write_text("""
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
""")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(main_file), '--preprocess'])

        assert result.exit_code == 0
        assert "Preprocessing..." in result.output
        assert "✓ Compilation successful" in result.output
        assert "8" in result.output

    def test_rust_auto_detection(self, tmp_path):
        """Test that .rs extension auto-detects Rust mode."""
        # Create a simple Rust file
        test_file = tmp_path / "test.rs"
        test_file.write_text("""
fn main() {
    println!("Rust auto-detected");
}
""")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file)])

        assert result.exit_code == 0
        assert "Rust auto-detected" in result.output

    def test_rust_force_flag(self, tmp_path):
        """Test --rust flag for non-.rs files."""
        # Create a Rust file with different extension
        test_file = tmp_path / "test.rust"
        test_file.write_text("""
fn main() {
    println!("Forced Rust mode");
}
""")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file), '--rust'])

        assert result.exit_code == 0
        assert "Forced Rust mode" in result.output


class TestCppTestCommand:
    """Test that C++ test command still works."""

    def test_cpp_still_works(self, tmp_path):
        """Test that C++ compilation still works after Rust support."""
        # Create a simple C++ file
        test_file = tmp_path / "hello.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    std::cout << "C++ still works!" << std::endl;
    return 0;
}
""")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file)])

        assert result.exit_code == 0
        assert "✓ Compilation successful" in result.output
        assert "C++ still works!" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_all_cases_pass(self, tmp_path):
        """Test parallel exact-match suite execution for C++."""
        test_file = tmp_path / "add.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    int a, b;
    std::cin >> a >> b;
    std::cout << a + b << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("1 2\n")
        (cases_dir / "001.out").write_text("3\n")
        (cases_dir / "002.in").write_text("10 20\n")
        (cases_dir / "002.out").write_text("30\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', 'suite', str(test_file), str(cases_dir), '--workers', '2'])

        assert result.exit_code == 0
        assert "Running 2 case(s) with 2 worker(s)..." in result.output
        assert "PASS 001.in" in result.output
        assert "PASS 002.in" in result.output
        assert "Summary: 2/2 passed" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_reports_failure(self, tmp_path):
        """Test suite failure reporting for mismatched expected output."""
        test_file = tmp_path / "constant.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    std::cout << 1 << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "bad.in").write_text("\n")
        (cases_dir / "bad.out").write_text("2\n")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', 'suite', str(test_file), str(cases_dir)])

        assert result.exit_code == 1
        assert "FAIL bad.in" in result.output
        assert "output differs from expected" in result.output
        assert "Summary: 0/1 passed" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_reports_relative_score_from_best_known(self, tmp_path):
        """Test suite relative scoring against best-known values."""
        test_file = tmp_path / "echo_first.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("10\n")
        (cases_dir / "001.out").write_text("10\n")
        (cases_dir / "002.in").write_text("20\n")
        (cases_dir / "002.out").write_text("20\n")
        best_known = tmp_path / "best.json"
        best_known.write_text('{"001.in": 5, "002.in": 10}\n')

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                'test',
                'suite',
                str(test_file),
                str(cases_dir),
                '--best-known',
                str(best_known),
                '--relative-scale',
                '100',
            ],
        )

        assert result.exit_code == 0
        assert "--- Relative Score ---" in result.output
        assert "001.in: your=10 best=5 relative=50.000000" in result.output
        assert "002.in: your=20 best=10 relative=50.000000" in result.output
        assert "Total relative score: 100.000000 / 200.000000" in result.output
        assert "Contest score: 100.000000 / 200.000000 (50.00% of max)" in result.output
        assert "--- Relative Loss Ranking ---" in result.output
        assert "001.in: loss=50.000000 point(s)" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_reports_rounded_contest_score(self, tmp_path):
        """Test contest-style rounded per-case relative points."""
        test_file = tmp_path / "echo_first.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("3\n")
        (cases_dir / "001.out").write_text("3\n")
        best_known = tmp_path / "best.json"
        best_known.write_text('{"001.in": 2}\n')

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                'test',
                'suite',
                str(test_file),
                str(cases_dir),
                '--best-known',
                str(best_known),
                '--relative-scale',
                '100',
                '--relative-round',
            ],
        )

        assert result.exit_code == 0
        assert "001.in: your=3 best=2 relative=66.666667" in result.output
        assert "Contest score: 67 / 100 (67.00% of max, rounded per case)" in result.output
        assert "001.in: loss=33 point(s)" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_runs_multiple_times_for_noise_summary(self, tmp_path):
        """Test repeated suite runs aggregate numeric outputs before scoring."""
        test_file = tmp_path / "echo_first.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("10\n")
        (cases_dir / "001.out").write_text("10\n")
        best_known = tmp_path / "best.json"
        best_known.write_text('{"001.in": 5}\n')

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                'test',
                'suite',
                str(test_file),
                str(cases_dir),
                '--runs',
                '3',
                '--best-known',
                str(best_known),
                '--relative-scale',
                '100',
            ],
        )

        assert result.exit_code == 0
        assert "Running 1 case(s) x 3 run(s) with 1 worker(s)..." in result.output
        assert "PASS 001.in (3/3 runs" in result.output
        assert "--- Noise Summary ---" in result.output
        assert "001.in: mean=10 stdev=0.000000" in result.output
        assert "001.in: your=10 best=5 relative=50.000000" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_compare_reports_paired_wins(self, tmp_path):
        """Test paired A/B suite comparison for numeric outputs."""
        file_a = tmp_path / "solver_a.cpp"
        file_a.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value << std::endl;
    return 0;
}
""")
        file_b = tmp_path / "solver_b.cpp"
        file_b.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value + 5 << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("10\n")
        (cases_dir / "001.out").write_text("10\n")
        (cases_dir / "002.in").write_text("20\n")
        (cases_dir / "002.out").write_text("20\n")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                'test',
                'suite',
                'compare',
                str(file_a),
                str(file_b),
                str(cases_dir),
                '--runs',
                '2',
            ],
        )

        assert result.exit_code == 0
        assert "Comparing 2 case(s) x 2 paired run(s) with 1 worker(s)..." in result.output
        assert "--- Paired A/B Results ---" in result.output
        assert "001.in: A=10 B=15 diff(A-B)=-5.000000 winner=A" in result.output
        assert "002.in: A=20 B=25 diff(A-B)=-5.000000 winner=A" in result.output
        assert "Summary: A wins 4/4, B wins 0/4, ties 0/4" in result.output
        assert "Mean diff(A-B): -5.000000" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_noise_floor_reports_self_pair_variance(self, tmp_path):
        """Test same-solver noise-floor calibration for numeric outputs."""
        test_file = tmp_path / "echo_first.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("10\n")
        (cases_dir / "001.out").write_text("10\n")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                'test',
                'suite',
                'noise-floor',
                str(test_file),
                str(cases_dir),
                '--runs',
                '2',
            ],
        )

        assert result.exit_code == 0
        assert "Calibrating 1 case(s) x 2 self-pair(s) with 1 worker(s)..." in result.output
        assert "--- Noise Floor ---" in result.output
        assert "001.in: run1=10 run2=10 abs-diff=0.000000" in result.output
        assert "Summary: 2 valid self-pair(s)" in result.output
        assert "Mean absolute diff: 0.000000" in result.output
        assert "Max absolute diff: 0.000000" in result.output

    @pytest.mark.skipif(os.system("which g++ > /dev/null 2>&1") != 0, reason="g++ not available")
    def test_cpp_suite_updates_best_known(self, tmp_path):
        """Test best-known JSON updates when this run improves numeric values."""
        test_file = tmp_path / "echo_first.cpp"
        test_file.write_text("""
#include <iostream>

int main() {
    int value;
    std::cin >> value;
    std::cout << value << std::endl;
    return 0;
}
""")

        cases_dir = tmp_path / "cases"
        cases_dir.mkdir()
        (cases_dir / "001.in").write_text("5\n")
        (cases_dir / "001.out").write_text("5\n")
        (cases_dir / "002.in").write_text("7\n")
        (cases_dir / "002.out").write_text("7\n")
        best_known = tmp_path / "best.json"
        best_known.write_text('{"001.in": 10}\n')

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                'test',
                'suite',
                str(test_file),
                str(cases_dir),
                '--best-known',
                str(best_known),
                '--update-best-known',
            ],
        )

        assert result.exit_code == 0
        assert f"Updated best-known: {best_known} (2 case(s) improved)" in result.output
        assert best_known.read_text() == '{\n  "001.in": 5.0,\n  "002.in": 7.0\n}\n'


class TestTestCommandErrorHandling:
    """Test error handling for the test command."""

    def test_unsupported_extension(self, tmp_path):
        """Test error handling for unsupported file extensions."""
        # Create a file with unsupported extension
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        runner = CliRunner()
        result = runner.invoke(cli, ['test', str(test_file)])

        assert result.exit_code != 0
        assert "❌ Unsupported file extension:" in result.output
        assert "Supported: .cpp, .cc, .cxx, .c++, .rs" in result.output
