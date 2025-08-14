import click
import importlib.metadata
import shutil
import os
import yaml

from kaggle_automation import kaggle
from experiment_manager import experiment
from base_interfaces import BasePreprocessor, BaseMinifier
from plugins.cpp_plugin import CppPreprocessor

@click.group()
def cli():
    pass

cli.add_command(kaggle)
cli.add_command(experiment)

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