"""Test command for competitive programming."""
import click
import concurrent.futures
import tempfile
import sys
import os
import subprocess

from config import load_config
from commands.test_scoring import (
    aggregate_suite_results,
    format_suite_result_line,
    load_best_known,
    report_compare_results,
    report_noise_floor_results,
    report_noise_summary,
    report_relative_scores,
    update_best_known as update_best_known_scores,
    write_best_known,
)
from commands.test_suite import (
    compile_for_suite,
    detect_suite_language,
    discover_suite_cases,
    prepare_source_for_suite_compile,
    run_compare_pair,
    run_suite_case,
)
from plugins.cpp_plugin import CppPreprocessor
from plugins.rust_plugin import RustPreprocessor


@click.command(name="test", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def test(args):
    """Compile/run one case, or use `test suite` for multi-case runs."""
    if args and args[0] == "suite":
        suite_args = list(args[1:])
        if suite_args and suite_args[0] == "compare":
            suite_compare_cmd.main(args=suite_args[1:], prog_name="test suite compare", standalone_mode=False)
        elif suite_args and suite_args[0] == "noise-floor":
            suite_noise_floor_cmd.main(args=suite_args[1:], prog_name="test suite noise-floor", standalone_mode=False)
        else:
            suite_cmd.main(args=suite_args, prog_name="test suite", standalone_mode=False)
    else:
        single_cmd.main(args=list(args), prog_name="test", standalone_mode=False)


@click.command(name="run")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True, resolve_path=True), help='Input file to feed to the program')
@click.option('-e', '--expected', 'expected_file', type=click.Path(exists=True, resolve_path=True), help='Expected output file for comparison')
@click.option('--preprocess', is_flag=True, help='Preprocess the file before compiling')
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths for preprocessing')
@click.option('--rust', is_flag=True, help='Force Rust mode (auto-detected from .rs extension)')
def single_cmd(file, input_file, expected_file, preprocess, include_paths, rust):
    """Compile and run C++ or Rust code with optional test input/output comparison."""
    # Auto-detect language from file extension
    file_ext = os.path.splitext(file)[1].lower()
    is_rust = rust or file_ext == '.rs'
    is_cpp = file_ext in ['.cpp', '.cc', '.cxx', '.c++']

    if not is_rust and not is_cpp:
        click.echo(f"❌ Unsupported file extension: {file_ext}", err=True)
        click.echo("   Supported: .cpp, .cc, .cxx, .c++, .rs", err=True)
        sys.exit(1)

    if is_rust:
        _test_rust(file, input_file, expected_file, preprocess, include_paths)
    else:
        _test_cpp(file, input_file, expected_file, preprocess, include_paths)


@click.command(name="suite")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.argument('cases_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--pattern', default='*.in', show_default=True, help='Input filename glob inside cases_dir')
@click.option('-j', '--workers', default=1, show_default=True, type=click.IntRange(min=1), help='Parallel case worker count')
@click.option('--runs', default=1, show_default=True, type=click.IntRange(min=1), help='Runs per case for noise-aware averaging')
@click.option('--timeout', type=float, help='Per-case timeout in seconds (defaults to prepkit_config.yaml test.timeout or 5)')
@click.option('--preprocess', is_flag=True, help='Preprocess the file before compiling')
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths for preprocessing')
@click.option('--rust', is_flag=True, help='Force Rust mode (auto-detected from .rs extension)')
@click.option('--best-known', 'best_known_file', type=click.Path(dir_okay=False, resolve_path=True), help='JSON file with best-known numeric outputs by case')
@click.option('--update-best-known', is_flag=True, help='Update --best-known with improved numeric outputs from this run')
@click.option('--score-mode', type=click.Choice(['min', 'max']), default='min', show_default=True, help='Whether lower or higher numeric outputs are better')
@click.option('--relative-scale', type=float, default=1.0, show_default=True, help='Per-case relative score scale')
@click.option('--relative-round', is_flag=True, help='Round each relative score to contest-style integer points')
def suite_cmd(file, cases_dir, pattern, workers, runs, timeout, preprocess, include_paths, rust, best_known_file, update_best_known, score_mode, relative_scale, relative_round):
    """Compile once and run an exact-match test suite over *.in/*.out cases."""
    if update_best_known and not best_known_file:
        click.echo("❌ --update-best-known requires --best-known", err=True)
        sys.exit(1)

    config = load_config()
    timeout = timeout if timeout is not None else config.get("test", {}).get("timeout", 5)

    is_rust = detect_suite_language(file, rust)

    cases = discover_suite_cases(cases_dir, pattern)
    if not cases:
        click.echo(f"❌ No cases found in {cases_dir} matching {pattern} with .out files", err=True)
        sys.exit(1)

    executable = None
    source_file = None
    try:
        source_file = prepare_source_for_suite_compile(file, preprocess, include_paths, is_rust, config)
        executable = compile_for_suite(file, source_file, is_rust, config)

        if runs == 1:
            click.echo(f"Running {len(cases)} case(s) with {workers} worker(s)...")
        else:
            click.echo(f"Running {len(cases)} case(s) x {runs} run(s) with {workers} worker(s)...")

        raw_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(run_suite_case, executable, input_file, expected_file, timeout)
                for input_file, expected_file in cases
                for _ in range(runs)
            ]
            for future in concurrent.futures.as_completed(futures):
                raw_results.append(future.result())

        results = aggregate_suite_results(raw_results, runs) if runs > 1 else raw_results
        results.sort(key=lambda result: result.case)
        passed = sum(1 for result in results if result.passed)

        click.echo("\n--- Suite Results ---")
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            click.echo(format_suite_result_line(status, result, runs))
            if not result.passed and result.error:
                click.echo(f"  {result.error}")

        click.echo(f"\nSummary: {passed}/{len(results)} passed")
        if runs > 1:
            report_noise_summary(results, runs)

        if best_known_file:
            best_known = load_best_known(best_known_file)
            report_relative_scores(results, best_known, score_mode, relative_scale, relative_round)
            if update_best_known:
                updated = update_best_known_scores(results, best_known, score_mode)
                write_best_known(best_known_file, best_known)
                click.echo(f"\nUpdated best-known: {best_known_file} ({updated} case(s) improved)")

        if passed != len(results):
            sys.exit(1)
    finally:
        if preprocess and source_file and os.path.exists(source_file):
            os.remove(source_file)
        if executable and os.path.exists(executable):
            os.remove(executable)


@click.command(name="compare")
@click.argument('file_a', type=click.Path(exists=True, resolve_path=True))
@click.argument('file_b', type=click.Path(exists=True, resolve_path=True))
@click.argument('cases_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--pattern', default='*.in', show_default=True, help='Input filename glob inside cases_dir')
@click.option('-j', '--workers', default=1, show_default=True, type=click.IntRange(min=1), help='Parallel paired worker count')
@click.option('--runs', default=1, show_default=True, type=click.IntRange(min=1), help='Paired runs per case')
@click.option('--timeout', type=float, help='Per-program timeout in seconds (defaults to prepkit_config.yaml test.timeout or 5)')
@click.option('--preprocess', is_flag=True, help='Preprocess both files before compiling')
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths for preprocessing')
@click.option('--rust', is_flag=True, help='Force Rust mode for both files (auto-detected from .rs extension)')
@click.option('--score-mode', type=click.Choice(['min', 'max']), default='min', show_default=True, help='Whether lower or higher numeric outputs are better')
def suite_compare_cmd(file_a, file_b, cases_dir, pattern, workers, runs, timeout, preprocess, include_paths, rust, score_mode):
    """Compare two programs with paired repeated suite runs."""
    config = load_config()
    timeout = timeout if timeout is not None else config.get("test", {}).get("timeout", 5)
    is_rust_a = detect_suite_language(file_a, rust)
    is_rust_b = detect_suite_language(file_b, rust)

    cases = discover_suite_cases(cases_dir, pattern)
    if not cases:
        click.echo(f"❌ No cases found in {cases_dir} matching {pattern} with .out files", err=True)
        sys.exit(1)

    executable_a = None
    executable_b = None
    source_a = None
    source_b = None
    try:
        source_a = prepare_source_for_suite_compile(file_a, preprocess, include_paths, is_rust_a, config)
        source_b = prepare_source_for_suite_compile(file_b, preprocess, include_paths, is_rust_b, config)
        executable_a = compile_for_suite(file_a, source_a, is_rust_a, config)
        executable_b = compile_for_suite(file_b, source_b, is_rust_b, config)

        click.echo(f"Comparing {len(cases)} case(s) x {runs} paired run(s) with {workers} worker(s)...")
        pair_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(run_compare_pair, executable_a, executable_b, input_file, expected_file, timeout)
                for input_file, expected_file in cases
                for _ in range(runs)
            ]
            for future in concurrent.futures.as_completed(futures):
                pair_results.append(future.result())

        report_compare_results(pair_results, score_mode)
        if any(not result.valid for result in pair_results):
            sys.exit(1)
    finally:
        for source_file in (source_a, source_b):
            if preprocess and source_file and os.path.exists(source_file):
                os.remove(source_file)
        for executable in (executable_a, executable_b):
            if executable and os.path.exists(executable):
                os.remove(executable)


@click.command(name="noise-floor")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.argument('cases_dir', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--pattern', default='*.in', show_default=True, help='Input filename glob inside cases_dir')
@click.option('-j', '--workers', default=1, show_default=True, type=click.IntRange(min=1), help='Parallel paired worker count')
@click.option('--runs', default=3, show_default=True, type=click.IntRange(min=1), help='Self-comparison pairs per case')
@click.option('--timeout', type=float, help='Per-run timeout in seconds (defaults to prepkit_config.yaml test.timeout or 5)')
@click.option('--preprocess', is_flag=True, help='Preprocess the file before compiling')
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths for preprocessing')
@click.option('--rust', is_flag=True, help='Force Rust mode (auto-detected from .rs extension)')
def suite_noise_floor_cmd(file, cases_dir, pattern, workers, runs, timeout, preprocess, include_paths, rust):
    """Measure same-solver run-to-run score variance."""
    config = load_config()
    timeout = timeout if timeout is not None else config.get("test", {}).get("timeout", 5)
    is_rust = detect_suite_language(file, rust)

    cases = discover_suite_cases(cases_dir, pattern)
    if not cases:
        click.echo(f"❌ No cases found in {cases_dir} matching {pattern} with .out files", err=True)
        sys.exit(1)

    executable = None
    source_file = None
    try:
        source_file = prepare_source_for_suite_compile(file, preprocess, include_paths, is_rust, config)
        executable = compile_for_suite(file, source_file, is_rust, config)

        click.echo(f"Calibrating {len(cases)} case(s) x {runs} self-pair(s) with {workers} worker(s)...")
        pair_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(run_compare_pair, executable, executable, input_file, expected_file, timeout)
                for input_file, expected_file in cases
                for _ in range(runs)
            ]
            for future in concurrent.futures.as_completed(futures):
                pair_results.append(future.result())

        report_noise_floor_results(pair_results)
        if any(not result.valid for result in pair_results):
            sys.exit(1)
    finally:
        if preprocess and source_file and os.path.exists(source_file):
            os.remove(source_file)
        if executable and os.path.exists(executable):
            os.remove(executable)


def _test_cpp(file, input_file, expected_file, preprocess, include_paths):
    """Test C++ code."""
    # Load config for defaults
    config = load_config()
    test_config = config.get("test", {})
    cpp_compile_config = config.get("cpp_compile", {})

    # Use config defaults if CLI options not provided
    if not input_file and test_config.get("input_file"):
        input_file = test_config["input_file"]
        if os.path.exists(input_file):
            click.echo(f"Using input file from config: {input_file}")

    if not expected_file and test_config.get("expected_file"):
        expected_file = test_config["expected_file"]
        if os.path.exists(expected_file):
            click.echo(f"Using expected file from config: {expected_file}")

    timeout = test_config.get("timeout", 5)
    compiler_std = cpp_compile_config.get("std", "c++17")
    compiler_flags = cpp_compile_config.get("flags", [])

    # Determine source code to compile
    if preprocess:
        click.echo("Preprocessing...")
        # Use config include paths + CLI include paths
        cpp_preprocess_config = config.get("cpp_preprocess", {})
        config_include_paths = cpp_preprocess_config.get("include_paths", [])
        all_include_paths = list(config_include_paths) + list(include_paths)

        cpp_preprocessor = CppPreprocessor()
        preprocessed_code = cpp_preprocessor.preprocess(file, all_include_paths)

        # Write preprocessed code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as tmp:
            tmp.write(preprocessed_code)
            source_file = tmp.name
    else:
        source_file = file

    # Compile
    executable = tempfile.NamedTemporaryFile(delete=False, suffix='.out')
    executable.close()

    # Build compile command with config
    compile_cmd = ['g++', source_file, '-o', executable.name, f'-std={compiler_std}'] + compiler_flags

    click.echo(f"Compiling {os.path.basename(file)}...")
    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True
    )

    # Clean up preprocessed temp file if created
    if preprocess:
        os.remove(source_file)

    if compile_result.returncode != 0:
        click.echo("❌ Compilation failed", err=True)
        click.echo(f"   Compiler: g++ -std=c++17", err=True)
        click.echo(f"   Source: {os.path.basename(file)}", err=True)
        click.echo("", err=True)
        click.echo("Compiler output:", err=True)
        click.echo(compile_result.stderr, err=True)
        if os.path.exists(executable.name):
            os.remove(executable.name)
        sys.exit(1)

    click.echo("✓ Compilation successful")

    # Run the executable
    click.echo("\n--- Running ---")
    stdin_data = None
    if input_file:
        with open(input_file, 'r') as f:
            stdin_data = f.read()
        click.echo(f"Input from: {os.path.basename(input_file)}")

    run_result = subprocess.run(
        [executable.name],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=timeout
    )

    # Clean up executable
    os.remove(executable.name)

    if run_result.returncode != 0:
        click.echo("❌ Runtime error:", err=True)
        if run_result.stderr:
            click.echo(run_result.stderr, err=True)
        sys.exit(1)

    # Show output
    click.echo("\n--- Output ---")
    click.echo(run_result.stdout)

    # Compare with expected output if provided
    if expected_file:
        with open(expected_file, 'r') as f:
            expected_output = f.read()

        if run_result.stdout.strip() == expected_output.strip():
            click.echo("\n✓ Output matches expected!")
        else:
            click.echo("\n❌ Output differs from expected:", err=True)
            click.echo("\n--- Expected ---")
            click.echo(expected_output)
            sys.exit(1)


def _test_rust(file, input_file, expected_file, preprocess, include_paths):
    """Test Rust code."""
    # Load config for defaults
    config = load_config()
    test_config = config.get("test", {})
    rust_compile_config = config.get("rust_compile", {})

    # Use config defaults if CLI options not provided
    if not input_file and test_config.get("input_file"):
        input_file = test_config["input_file"]
        if os.path.exists(input_file):
            click.echo(f"Using input file from config: {input_file}")

    if not expected_file and test_config.get("expected_file"):
        expected_file = test_config["expected_file"]
        if os.path.exists(expected_file):
            click.echo(f"Using expected file from config: {expected_file}")

    timeout = test_config.get("timeout", 5)
    compiler_edition = rust_compile_config.get("edition", "2021")
    compiler_flags = rust_compile_config.get("flags", [])

    # Determine source code to compile
    if preprocess:
        click.echo("Preprocessing...")
        # Use config include paths + CLI include paths
        rust_preprocess_config = config.get("rust_preprocess", {})
        config_include_paths = rust_preprocess_config.get("include_paths", [])
        all_include_paths = list(config_include_paths) + list(include_paths)

        rust_preprocessor = RustPreprocessor()
        preprocessed_code = rust_preprocessor.preprocess(file, all_include_paths)

        # Write preprocessed code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as tmp:
            tmp.write(preprocessed_code)
            source_file = tmp.name
    else:
        source_file = file

    # Compile
    executable = tempfile.NamedTemporaryFile(delete=False, suffix='.out')
    executable.close()

    # Build compile command with config
    compile_cmd = ['rustc', source_file, '-o', executable.name, f'--edition={compiler_edition}'] + compiler_flags

    click.echo(f"Compiling {os.path.basename(file)}...")
    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True
    )

    # Clean up preprocessed temp file if created
    if preprocess:
        os.remove(source_file)

    if compile_result.returncode != 0:
        click.echo("❌ Compilation failed", err=True)
        click.echo(f"   Compiler: rustc --edition={compiler_edition}", err=True)
        click.echo(f"   Source: {os.path.basename(file)}", err=True)
        click.echo("", err=True)
        click.echo("Compiler output:", err=True)
        click.echo(compile_result.stderr, err=True)
        if os.path.exists(executable.name):
            os.remove(executable.name)
        sys.exit(1)

    click.echo("✓ Compilation successful")

    # Run the executable
    click.echo("\n--- Running ---")
    stdin_data = None
    if input_file:
        with open(input_file, 'r') as f:
            stdin_data = f.read()
        click.echo(f"Input from: {os.path.basename(input_file)}")

    run_result = subprocess.run(
        [executable.name],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=timeout
    )

    # Clean up executable
    os.remove(executable.name)

    if run_result.returncode != 0:
        click.echo("❌ Runtime error:", err=True)
        if run_result.stderr:
            click.echo(run_result.stderr, err=True)
        sys.exit(1)

    # Show output
    click.echo("\n--- Output ---")
    click.echo(run_result.stdout)

    # Compare with expected output if provided
    if expected_file:
        with open(expected_file, 'r') as f:
            expected_output = f.read()

        if run_result.stdout.strip() == expected_output.strip():
            click.echo("\n✓ Output matches expected!")
        else:
            click.echo("\n❌ Output differs from expected:", err=True)
            click.echo("\n--- Expected ---")
            click.echo(expected_output)
            sys.exit(1)
