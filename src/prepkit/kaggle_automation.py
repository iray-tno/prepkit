import click

@click.group()
def kaggle():
    """Kaggle workflow automation."""
    pass

@kaggle.command()
@click.argument('notebook_file', type=click.Path(exists=True))
def push_notebook(notebook_file):
    """Pushes a Jupyter notebook to Kaggle Kernels."""
    click.echo(f"Pushing notebook {notebook_file} to Kaggle.")

@kaggle.command()
@click.argument('submission_file', type=click.Path(exists=True))
@click.option('--competition', required=True, help="Kaggle competition name.")
@click.option('--message', default="From PrepKit", help="Submission message.")
def submit_competition(submission_file, competition, message):
    """Submits a prediction file to a Kaggle competition."""
    click.echo(f"Submitting {submission_file} to {competition} with message: {message}")
