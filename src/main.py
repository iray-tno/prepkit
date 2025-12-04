import click
import importlib.metadata

from kaggle_automation import kaggle
from experiment_manager import experiment
from ai_assistant_config import ai_config
from commands.cpp_commands import cpp_group
from commands.rust_commands import rust_group
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
cli.add_command(rust_group)
cli.add_command(test)
cli.add_command(project)

if __name__ == "__main__":
    cli()