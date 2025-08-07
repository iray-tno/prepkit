import click
import importlib.metadata
import shutil
import os

from .kaggle_automation import kaggle
from .experiment_manager import experiment
from .base_interfaces import BasePreprocessor, BaseMinifier
from .plugins.cpp_plugin import CppPreprocessor, CppMinifier

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

cpp_minifier_instance = CppMinifier()
@cpp_group.command(name="minify")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
def cpp_minify_cmd(file):
    result = cpp_minifier_instance.minify(file)
    click.echo(result)

# Project command group
@cli.group()
def project():
    """Project management commands."""
    pass

@project.command()
@click.argument('project_name')
@click.option('--lang', default='cpp', help='Programming language for the boilerplate (e.g., cpp).')
def new(project_name, lang):
    """
    Creates a new project boilerplate in the specified directory.
    """
    boilerplate_path = os.path.join(os.path.dirname(__file__), 'boilerplate', lang)
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
