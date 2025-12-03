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
from commands.test_command import test
from commands.project_commands import project

@click.group()
@click.version_option(importlib.metadata.version("prepkit"), "-v", "--version", prog_name="prepkit")
def cli():
    pass

cli.add_command(kaggle)
cli.add_command(experiment)
cli.add_command(ai_config)
cli.add_command(cpp_group)
cli.add_command(test)
cli.add_command(project)

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