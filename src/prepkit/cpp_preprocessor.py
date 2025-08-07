import click

@click.group()
def cpp():
    """C++ preprocessor and minifier."""
    pass

@cpp.command()
@click.argument('file', type=click.Path(exists=True))
def preprocess(file):
    """Preprocesses a C++ file."""
    click.echo(f"Preprocessing {file}")

@cpp.command()
@click.argument('file', type=click.Path(exists=True))
def minify(file):
    """Minifies a C++ file."""
    click.echo(f"Minifying {file}")
