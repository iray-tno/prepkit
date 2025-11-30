import click
import importlib.metadata
import shutil
import os
import yaml

from kaggle_automation import kaggle
from experiment_manager import experiment
from ai_assistant_config import ai_config
from base_interfaces import BasePreprocessor, BaseMinifier
from plugins.cpp_plugin import CppPreprocessor

@click.group()
@click.version_option(importlib.metadata.version("prepkit"), "-v", "--version", prog_name="prepkit")
def cli():
    pass

cli.add_command(kaggle)
cli.add_command(experiment)
cli.add_command(ai_config)

# Directly register C++ commands for now
@cli.group(name="cpp")
def cpp_group():
    """C++ preprocessor and minifier."""
    pass

cpp_preprocessor_instance = CppPreprocessor()
@cpp_group.command(name="preprocess")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True))
def cpp_preprocess_cmd(file, include_paths):
    result = cpp_preprocessor_instance.preprocess(file, list(include_paths))
    click.echo(result)

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

# Load preprocessor plugins
load_plugins("prepkit.preprocessors", BasePreprocessor)

# Load minifier plugins
load_plugins("prepkit.minifiers", BaseMinifier)

if __name__ == "__main__":
    cli()