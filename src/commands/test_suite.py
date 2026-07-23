"""Execution helpers for test suite commands."""
import click
import tempfile
import sys
import os
import subprocess
import time

from commands.test_scoring import PairResult, SuiteRunResult, parse_numeric_output
from plugins.cpp_plugin import CppPreprocessor
from plugins.rust_plugin import RustPreprocessor


def detect_suite_language(file, force_rust):
    file_ext = os.path.splitext(file)[1].lower()
    is_rust = force_rust or file_ext == '.rs'
    is_cpp = file_ext in ['.cpp', '.cc', '.cxx', '.c++']

    if not is_rust and not is_cpp:
        click.echo(f"❌ Unsupported file extension: {file_ext}", err=True)
        click.echo("   Supported: .cpp, .cc, .cxx, .c++, .rs", err=True)
        sys.exit(1)
    return is_rust


def discover_suite_cases(cases_dir, pattern):
    input_files = sorted(
        os.path.join(cases_dir, filename)
        for filename in os.listdir(cases_dir)
        if _matches_case_pattern(filename, pattern)
    )
    cases = []
    for input_file in input_files:
        expected_file = os.path.splitext(input_file)[0] + ".out"
        if os.path.exists(expected_file):
            cases.append((input_file, expected_file))
    return cases


def _matches_case_pattern(filename, pattern):
    if pattern == "*.in":
        return filename.endswith(".in")
    import fnmatch
    return fnmatch.fnmatch(filename, pattern)


def prepare_source_for_suite_compile(file, preprocess, include_paths, is_rust, config):
    if not preprocess:
        return file

    if is_rust:
        rust_preprocess_config = config.get("rust_preprocess", {})
        config_include_paths = rust_preprocess_config.get("include_paths", [])
        preprocessor = RustPreprocessor()
        preprocessed_code = preprocessor.preprocess(file, list(config_include_paths) + list(include_paths))
        suffix = ".rs"
    else:
        cpp_preprocess_config = config.get("cpp_preprocess", {})
        config_include_paths = cpp_preprocess_config.get("include_paths", [])
        preprocessor = CppPreprocessor()
        preprocessed_code = preprocessor.preprocess(file, list(config_include_paths) + list(include_paths))
        suffix = ".cpp"

    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp:
        tmp.write(preprocessed_code)
        return tmp.name


def compile_for_suite(original_file, source_file, is_rust, config):
    executable = tempfile.NamedTemporaryFile(delete=False, suffix='.out')
    executable.close()

    if is_rust:
        rust_compile_config = config.get("rust_compile", {})
        compiler_edition = rust_compile_config.get("edition", "2021")
        compiler_flags = rust_compile_config.get("flags", [])
        compile_cmd = ['rustc', source_file, '-o', executable.name, f'--edition={compiler_edition}'] + compiler_flags
    else:
        cpp_compile_config = config.get("cpp_compile", {})
        compiler_std = cpp_compile_config.get("std", "c++17")
        compiler_flags = cpp_compile_config.get("flags", [])
        compile_cmd = ['g++', source_file, '-o', executable.name, f'-std={compiler_std}'] + compiler_flags

    click.echo(f"Compiling {os.path.basename(original_file)}...")
    compile_result = subprocess.run(compile_cmd, capture_output=True, text=True)
    if compile_result.returncode != 0:
        click.echo("❌ Compilation failed", err=True)
        click.echo("Compiler output:", err=True)
        click.echo(compile_result.stderr, err=True)
        if os.path.exists(executable.name):
            os.remove(executable.name)
        sys.exit(1)

    click.echo("✓ Compilation successful")
    return executable.name


def run_suite_case(executable, input_file, expected_file, timeout):
    with open(input_file, 'r') as f:
        stdin_data = f.read()
    with open(expected_file, 'r') as f:
        expected_output = f.read()

    started = time.perf_counter()
    try:
        run_result = subprocess.run(
            [executable],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        runtime = time.perf_counter() - started
    except subprocess.TimeoutExpired:
        return SuiteRunResult(
            case=os.path.basename(input_file),
            passed=False,
            runtime=timeout,
            error=f"timed out after {timeout}s",
            output="",
        )

    if run_result.returncode != 0:
        return SuiteRunResult(
            case=os.path.basename(input_file),
            passed=False,
            runtime=runtime,
            error=f"runtime error: {run_result.stderr.strip()}",
            output=run_result.stdout,
        )

    passed = run_result.stdout.strip() == expected_output.strip()
    error = "" if passed else "output differs from expected"
    return SuiteRunResult(
        case=os.path.basename(input_file),
        passed=passed,
        runtime=runtime,
        error=error,
        output=run_result.stdout,
    )


def run_compare_pair(executable_a, executable_b, input_file, expected_file, timeout):
    result_a = run_suite_case(executable_a, input_file, expected_file, timeout)
    result_b = run_suite_case(executable_b, input_file, expected_file, timeout)
    case = os.path.basename(input_file)

    try:
        score_a = parse_numeric_output(result_a.output)
        score_b = parse_numeric_output(result_b.output)
    except ValueError as exc:
        return PairResult(
            case=case,
            valid=False,
            error=str(exc),
            score_a=None,
            score_b=None,
            diff=None,
        )

    return PairResult(
        case=case,
        valid=True,
        error="",
        score_a=score_a,
        score_b=score_b,
        diff=score_a - score_b,
    )
