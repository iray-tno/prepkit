"""Test command for competitive programming."""
import click
import tempfile
import sys
import os
import subprocess

from config import load_config
from plugins.cpp_plugin import CppPreprocessor
from plugins.rust_plugin import RustPreprocessor


@click.command(name="test")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True, resolve_path=True), help='Input file to feed to the program')
@click.option('-e', '--expected', 'expected_file', type=click.Path(exists=True, resolve_path=True), help='Expected output file for comparison')
@click.option('--preprocess', is_flag=True, help='Preprocess the file before compiling')
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths for preprocessing')
@click.option('--rust', is_flag=True, help='Force Rust mode (auto-detected from .rs extension)')
def test(file, input_file, expected_file, preprocess, include_paths, rust):
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
