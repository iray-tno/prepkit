import click

@click.group()
def experiment():
    """Experiment management tools."""
    pass

@experiment.command()
@click.argument('config_file', type=click.Path(exists=True))
def run(config_file):
    """Runs an experiment based on a configuration file."""
    click.echo(f"Running experiment with config: {config_file}")

@experiment.command()
def optimize():
    """Optimizes hyperparameters for an experiment."""
    click.echo("Optimizing hyperparameters.")
