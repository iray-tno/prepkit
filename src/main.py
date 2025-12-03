import click
import importlib.metadata
import shutil
import os
import yaml
import subprocess
from typing import Dict, Any, List

from kaggle_automation import kaggle
from experiment_manager import experiment
from ai_assistant_config import ai_config
from base_interfaces import BasePreprocessor, BaseMinifier
from plugins.cpp_plugin import CppPreprocessor, CppMinifier
from config import load_config
from commands.cpp_commands import cpp_group

@click.group()
@click.version_option(importlib.metadata.version("prepkit"), "-v", "--version", prog_name="prepkit")
def cli():
    pass

cli.add_command(kaggle)
cli.add_command(experiment)
cli.add_command(ai_config)
cli.add_command(cpp_group)

# Test command for competitive programming
@cli.command()
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-i', '--input', 'input_file', type=click.Path(exists=True, resolve_path=True), help='Input file to feed to the program')
@click.option('-e', '--expected', 'expected_file', type=click.Path(exists=True, resolve_path=True), help='Expected output file for comparison')
@click.option('--preprocess', is_flag=True, help='Preprocess the file before compiling')
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths for preprocessing')
def test(file, input_file, expected_file, preprocess, include_paths):
    """Compile and run C++ code with optional test input/output comparison."""
    import tempfile
    import sys

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

# Project command group
@cli.group()
def project():
    """Project management commands."""
    pass

@project.command()
@click.argument('project_name')
@click.option('--lang', default='cpp', help='Programming language for the boilerplate (e.g., cpp).')
@click.option('--type', default='atcoder-algorithm', help='Preconfigured project type (e.g., atcoder-algorithm, codingame, kaggle).')
def new(project_name, lang, type):
    """
    Creates a new project boilerplate in the specified directory.
    """
    boilerplate_path = os.path.join(os.path.dirname(__file__), 'boilerplate', lang)
    project_configs_path = os.path.join(os.path.dirname(__file__), 'boilerplate', 'project_configs.yaml')
    destination_path = os.path.join(os.getcwd(), project_name)

    if not os.path.exists(boilerplate_path):
        click.echo(f"Error: Boilerplate for language '{lang}' not found.", err=True)
        return

    if os.path.exists(destination_path):
        click.echo(f"Error: Project directory '{project_name}' already exists.", err=True)
        return

    try:
        shutil.copytree(boilerplate_path, destination_path)
        click.echo(f"Successfully created new {lang} project '{project_name}' at {destination_path}")

        # Load project configurations
        with open(project_configs_path, 'r') as f:
            all_project_configs = yaml.safe_load(f)
        
        selected_config = all_project_configs.get(type)
        if not selected_config:
            click.echo(f"Warning: Project type '{type}' not found in configurations. Using default settings.", err=True)
            selected_config = {}

        # Write prepkit_config.yaml to the new project directory
        prepkit_config_content = {
            "project_type": type,
            "cpp_preprocess": selected_config.get("cpp_preprocess", {"minify_output": False}) # Default to no minify
        }
        with open(os.path.join(destination_path, "prepkit_config.yaml"), 'w') as f:
            yaml.dump(prepkit_config_content, f, indent=2)
        click.echo(f"Generated prepkit_config.yaml for type '{type}' in {project_name}")

        # Setup Claude Code settings based on contest type
        claude_config = selected_config.get("claude_config", {})
        if claude_config:
            claude_dir = os.path.join(destination_path, ".claude")
            os.makedirs(claude_dir, exist_ok=True)
            
            # Determine which Claude settings template to use
            claude_settings_file = None
            if claude_config.get("enabled", False):
                platform = selected_config.get("contest_settings", {}).get("platform", "")
                if platform == "kaggle":
                    claude_settings_file = "kaggle_settings.json"
                elif platform == "codingame":
                    claude_settings_file = "codingame_settings.json"
                else:
                    claude_settings_file = "kaggle_settings.json"  # Default enabled config
            else:
                claude_settings_file = "disabled_settings.json"
            
            # Copy the appropriate Claude settings
            if claude_settings_file:
                claude_template_path = os.path.join(os.path.dirname(__file__), "boilerplate", "claude_configs", claude_settings_file)
                claude_dest_path = os.path.join(claude_dir, "settings.json")
                
                try:
                    shutil.copy2(claude_template_path, claude_dest_path)
                    if claude_config.get("enabled", False):
                        click.echo(f"✓ Claude Code enabled for {type} ({claude_config.get('reason', 'AI assistance allowed')})")
                    else:
                        click.echo(f"✗ Claude Code disabled for {type} ({claude_config.get('reason', 'Contest rules prohibit AI assistance')})")
                except FileNotFoundError:
                    click.echo(f"Warning: Claude settings template '{claude_settings_file}' not found", err=True)

        # Setup MCP configuration based on contest type
        mcp_config_file = None
        if claude_config.get("enabled", False):
            platform = selected_config.get("contest_settings", {}).get("platform", "")
            if platform == "kaggle":
                mcp_config_file = "kaggle_mcp.json"
            elif platform == "codingame":
                mcp_config_file = "codingame_mcp.json"
            else:
                mcp_config_file = "kaggle_mcp.json"  # Default enabled config
        else:
            mcp_config_file = "disabled_mcp.json"
        
        # Copy the appropriate MCP settings
        if mcp_config_file:
            mcp_template_path = os.path.join(os.path.dirname(__file__), "boilerplate", "mcp_configs", mcp_config_file)
            mcp_dest_path = os.path.join(destination_path, ".mcp.json")
            
            try:
                shutil.copy2(mcp_template_path, mcp_dest_path)
                if claude_config.get("enabled", False):
                    click.echo(f"✓ MCP (Serena) enabled for intelligent code assistance")
                else:
                    click.echo(f"✗ MCP disabled for contest compliance")
            except FileNotFoundError:
                click.echo(f"Warning: MCP settings template '{mcp_config_file}' not found", err=True)

    except Exception as e:
        click.echo(f"Error creating project: {e}", err=True)

# Keep load_plugins for future expansion (Rust, Kotlin, etc.)
def load_plugins(group_name, base_class):
    for entry_point in importlib.metadata.entry_points().select(group=group_name):
        try:
            plugin_class = entry_point.load()
            if issubclass(plugin_class, base_class):
                plugin_instance = plugin_class()
                for lang in plugin_instance.get_supported_languages():
                    # Skip cpp as it's handled directly
                    if lang == "cpp" or lang == "cxx" or lang == "c":
                        continue

                    lang_group = click.Group(name=lang)
                    cli.add_command(lang_group)

                    # Add preprocess command
                    @lang_group.command(name="preprocess")
                    @click.argument('file', type=click.Path(exists=True, resolve_path=True))
                    @click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True))
                    def preprocess_cmd(file, include_paths):
                        result = plugin_instance.preprocess(file, list(include_paths))
                        click.echo(result)
                    
                    # Add minify command
                    @lang_group.command(name="minify")
                    @click.argument('file', type=click.Path(exists=True, resolve_path=True))
                    def minify_cmd(file):
                        result = plugin_instance.minify(file)
                        click.echo(result)

        except Exception as e:
            click.echo(f"Error loading plugin {entry_point.name}: {e}", err=True)

# Plugin loading disabled for performance - plugins are not yet implemented
# TODO: Enable lazy plugin loading when Rust/Kotlin plugins are ready
# load_plugins("prepkit.preprocessors", BasePreprocessor)
# load_plugins("prepkit.minifiers", BaseMinifier)

if __name__ == "__main__":
    cli()