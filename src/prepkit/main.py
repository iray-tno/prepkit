import click

@click.group()
def cli():
    pass

from .cpp_preprocessor import cpp
from .kaggle_automation import kaggle
from .experiment_manager import experiment

cli.add_command(cpp)
cli.add_command(kaggle)
cli.add_command(experiment)

if __name__ == "__main__":
    cli()
