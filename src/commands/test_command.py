"""Test command for competitive programming."""
import click
import concurrent.futures
import json
import statistics
import tempfile
import sys
import os
import subprocess
import time

from config import load_config
from plugins.cpp_plugin import CppPreprocessor
from plugins.rust_plugin import RustPreprocessor


@click.command(name="test", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument('args', nargs=-1, type=click.UNPROCESSED)
def test(args):
    """Compile/run one case, or use `test suite` for multi-case runs."""
    if args and args[0] == "suite":
        suite_cmd.main(args=list(args[1:]), prog_name="test suite", standalone_mode=False)
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
def suite_cmd(file, cases_dir, pattern, workers, runs, timeout, preprocess, include_paths, rust, best_known_file, update_best_known, score_mode, relative_scale):
    """Compile once and run an exact-match test suite over *.in/*.out cases."""
    if update_best_known and not best_known_file:
        click.echo("❌ --update-best-known requires --best-known", err=True)
        sys.exit(1)

    config = load_config()
    timeout = timeout if timeout is not None else config.get("test", {}).get("timeout", 5)

    file_ext = os.path.splitext(file)[1].lower()
    is_rust = rust or file_ext == '.rs'
    is_cpp = file_ext in ['.cpp', '.cc', '.cxx', '.c++']

    if not is_rust and not is_cpp:
        click.echo(f"❌ Unsupported file extension: {file_ext}", err=True)
        click.echo("   Supported: .cpp, .cc, .cxx, .c++, .rs", err=True)
        sys.exit(1)

    cases = _discover_suite_cases(cases_dir, pattern)
    if not cases:
        click.echo(f"❌ No cases found in {cases_dir} matching {pattern} with .out files", err=True)
        sys.exit(1)

    executable = None
    source_file = None
    try:
        source_file = _prepare_source_for_compile(file, preprocess, include_paths, is_rust, config)
        executable = _compile_for_suite(file, source_file, is_rust, config)

        if runs == 1:
            click.echo(f"Running {len(cases)} case(s) with {workers} worker(s)...")
        else:
            click.echo(f"Running {len(cases)} case(s) x {runs} run(s) with {workers} worker(s)...")

        raw_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_run_suite_case, executable, input_file, expected_file, timeout)
                for input_file, expected_file in cases
                for _ in range(runs)
            ]
            for future in concurrent.futures.as_completed(futures):
                raw_results.append(future.result())

        results = _aggregate_suite_results(raw_results, runs) if runs > 1 else raw_results
        results.sort(key=lambda result: result["case"])
        passed = sum(1 for result in results if result["passed"])

        click.echo("\n--- Suite Results ---")
        for result in results:
            status = "PASS" if result["passed"] else "FAIL"
            click.echo(_format_suite_result_line(status, result, runs))
            if not result["passed"] and result["error"]:
                click.echo(f"  {result['error']}")

        click.echo(f"\nSummary: {passed}/{len(results)} passed")
        if runs > 1:
            _report_noise_summary(results, runs)

        if best_known_file:
            best_known = _load_best_known(best_known_file)
            _report_relative_scores(results, best_known, score_mode, relative_scale)
            if update_best_known:
                updated = _update_best_known(results, best_known, score_mode)
                _write_best_known(best_known_file, best_known)
                click.echo(f"\nUpdated best-known: {best_known_file} ({updated} case(s) improved)")

        if passed != len(results):
            sys.exit(1)
    finally:
        if preprocess and source_file and os.path.exists(source_file):
            os.remove(source_file)
        if executable and os.path.exists(executable):
            os.remove(executable)


def _discover_suite_cases(cases_dir, pattern):
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


def _prepare_source_for_compile(file, preprocess, include_paths, is_rust, config):
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


def _compile_for_suite(original_file, source_file, is_rust, config):
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


def _run_suite_case(executable, input_file, expected_file, timeout):
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
        return {
            "case": os.path.basename(input_file),
            "passed": False,
            "runtime": timeout,
            "error": f"timed out after {timeout}s",
            "output": "",
        }

    if run_result.returncode != 0:
        return {
            "case": os.path.basename(input_file),
            "passed": False,
            "runtime": runtime,
            "error": f"runtime error: {run_result.stderr.strip()}",
            "output": run_result.stdout,
        }

    passed = run_result.stdout.strip() == expected_output.strip()
    error = "" if passed else "output differs from expected"
    return {
        "case": os.path.basename(input_file),
        "passed": passed,
        "runtime": runtime,
        "error": error,
        "output": run_result.stdout,
    }


def _aggregate_suite_results(raw_results, runs):
    grouped = {}
    for result in raw_results:
        grouped.setdefault(result["case"], []).append(result)

    aggregate_results = []
    for case, case_results in grouped.items():
        numeric_outputs = []
        for result in case_results:
            try:
                numeric_outputs.append(_parse_numeric_output(result["output"]))
            except ValueError:
                pass

        mean_output = statistics.mean(numeric_outputs) if numeric_outputs else None
        output = f"{mean_output}\n" if mean_output is not None else ""
        failed_runs = [result for result in case_results if not result["passed"]]
        aggregate_results.append({
            "case": case,
            "passed": not failed_runs and len(case_results) == runs,
            "runtime": statistics.mean(result["runtime"] for result in case_results),
            "error": _format_aggregate_error(failed_runs, len(case_results), runs),
            "output": output,
            "runs": len(case_results),
            "passed_runs": len(case_results) - len(failed_runs),
            "score_mean": mean_output,
            "score_stdev": statistics.stdev(numeric_outputs) if len(numeric_outputs) > 1 else 0.0,
            "numeric_runs": len(numeric_outputs),
        })
    return aggregate_results


def _format_aggregate_error(failed_runs, actual_runs, expected_runs):
    if actual_runs != expected_runs:
        return f"expected {expected_runs} run(s), got {actual_runs}"
    if not failed_runs:
        return ""
    first_error = failed_runs[0]["error"]
    return f"{len(failed_runs)}/{actual_runs} run(s) failed: {first_error}"


def _format_suite_result_line(status, result, runs):
    if runs == 1:
        return f"{status} {result['case']} ({result['runtime']:.3f}s)"
    return (
        f"{status} {result['case']} "
        f"({result['passed_runs']}/{result['runs']} runs, avg {result['runtime']:.3f}s)"
    )


def _report_noise_summary(results, runs):
    click.echo("\n--- Noise Summary ---")
    for result in results:
        if result["numeric_runs"] == runs:
            click.echo(
                f"{result['case']}: mean={_format_score(result['score_mean'])} "
                f"stdev={result['score_stdev']:.6f}"
            )
        else:
            click.echo(f"{result['case']}: N/A ({result['numeric_runs']}/{runs} numeric run(s))")


def _load_best_known(best_known_file):
    if not os.path.exists(best_known_file):
        return {}
    with open(best_known_file, 'r') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise click.ClickException("--best-known must contain a JSON object")
    return data


def _write_best_known(best_known_file, best_known):
    parent_dir = os.path.dirname(best_known_file)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(best_known_file, 'w') as f:
        json.dump(best_known, f, indent=2, sort_keys=True)
        f.write("\n")


def _report_relative_scores(results, best_known, score_mode, relative_scale):
    click.echo("\n--- Relative Score ---")
    total = 0.0
    scored = 0
    for result in results:
        case = result["case"]
        try:
            your_score = _parse_numeric_output(result["output"])
        except ValueError as exc:
            click.echo(f"{case}: N/A ({exc})")
            continue

        best_score = best_known.get(case)
        if best_score is None:
            click.echo(f"{case}: N/A (no best-known value)")
            continue

        try:
            relative_score = _relative_score(your_score, float(best_score), score_mode, relative_scale)
        except ValueError as exc:
            click.echo(f"{case}: N/A ({exc})")
            continue

        total += relative_score
        scored += 1
        click.echo(
            f"{case}: your={_format_score(your_score)} "
            f"best={_format_score(float(best_score))} "
            f"relative={relative_score:.6f}"
        )

    click.echo(f"Total relative score: {total:.6f} / {(scored * relative_scale):.6f}")


def _update_best_known(results, best_known, score_mode):
    updated = 0
    for result in results:
        try:
            your_score = _parse_numeric_output(result["output"])
        except ValueError:
            continue

        current_best = best_known.get(result["case"])
        if current_best is None or _is_better(your_score, float(current_best), score_mode):
            best_known[result["case"]] = your_score
            updated += 1
    return updated


def _parse_numeric_output(output):
    tokens = output.strip().split()
    if not tokens:
        raise ValueError("empty output")
    try:
        return float(tokens[0])
    except ValueError as exc:
        raise ValueError("first output token is not numeric") from exc


def _relative_score(your_score, best_score, score_mode, relative_scale):
    if your_score <= 0 or best_score <= 0:
        raise ValueError("relative score requires positive numeric values")
    if score_mode == "min":
        return relative_scale * best_score / your_score
    return relative_scale * your_score / best_score


def _is_better(candidate, current_best, score_mode):
    if score_mode == "min":
        return candidate < current_best
    return candidate > current_best


def _format_score(score):
    if score.is_integer():
        return str(int(score))
    return f"{score:.6f}"


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
