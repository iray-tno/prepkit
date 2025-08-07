import click

@click.group()
def cli():
    pass

from .cpp_preprocessor import cpp

cli.add_command(cpp)

if __name__ == "__main__":
    cli()
