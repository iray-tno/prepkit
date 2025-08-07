import click
import importlib.metadata

from .kaggle_automation import kaggle
from .experiment_manager import experiment
from .base_interfaces import BasePreprocessor, BaseMinifier

@click.group()
def cli():
    pass

cli.add_command(kaggle)
cli.add_command(experiment)

def load_plugins(group_name, base_class):
    for entry_point in importlib.metadata.entry_points().select(group=group_name):
        try:
            plugin_class = entry_point.load()
            if issubclass(plugin_class, base_class):
                plugin_instance = plugin_class()
                for lang in plugin_instance.get_supported_languages():
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