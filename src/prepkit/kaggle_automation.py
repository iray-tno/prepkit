import click
import subprocess
import os
import json
from typing import Any, Dict, Optional

@click.group()
def kaggle():
    """Kaggle workflow automation."""
    pass

@kaggle.command()
@click.argument('notebook_file', type=click.Path(exists=True, resolve_path=True))
@click.option('--title', type=str, help="Title of the Kaggle notebook. If not provided, derived from filename.")
@click.option('--slug', type=str, help="Slug for the Kaggle notebook. If not provided, derived from title.")
@click.option('--language', default="python", type=str, help="Programming language of the notebook.")
@click.option('--private/--public', default=True, type=bool, help="Visibility of the notebook.")
def push_notebook(
    notebook_file: str,
    title: Optional[str],
    slug: Optional[str],
    language: str,
    private: bool
) -> None:
    """
    Pushes a Jupyter notebook (or Python script intended as a notebook) to Kaggle Kernels.
    A kernel-metadata.json file will be generated or updated in the notebook's directory.
    """
    click.echo(f"Pushing notebook {notebook_file} to Kaggle.")

    notebook_dir: str = os.path.dirname(notebook_file)
    notebook_name: str = os.path.basename(notebook_file)
    metadata_file: str = os.path.join(notebook_dir, "kernel-metadata.json")

    # Generate or update kernel-metadata.json
    if not title:
        title = os.path.splitext(notebook_name)[0].replace('_', ' ').title()
    if not slug:
        slug = title.lower().replace(' ', '-')

    metadata: Dict[str, Any] = {
        "id": f"<KAGGLE_USERNAME>/{slug}", # User needs to replace <KAGGLE_USERNAME>
        "title": title,
        "code_file": notebook_name,
        "language": language,
        "kernel_type": "notebook" if notebook_name.endswith('.ipynb') else "script",
        "is_private": private,
        "enable_gpu": False,
        "enable_internet": False,
        "enable_tpu": False,
        "id_no_global": "",
        "keywords": [],
        "dataset_sources": [],
        "competition_sources": [],
        "model_sources": [],
        "kernel_sources": []
    }

    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)
        click.echo(f"Generated/Updated {metadata_file}")

        # Change directory to notebook_dir for kaggle command to work correctly
        result: subprocess.CompletedProcess = subprocess.run(
            ['kaggle', 'kernels', 'push'],
            cwd=notebook_dir,
            capture_output=True,
            text=True,
            check=True
        )
        click.echo("Kaggle Kernels Push Output:")
        click.echo(result.stdout)
        if result.stderr:
            click.echo("Kaggle Kernels Push Error:")
            click.echo(result.stderr)
        click.echo(f"Successfully pushed {notebook_file} to Kaggle.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error pushing notebook: {e.cmd} failed with exit code {e.returncode}", err=True)
        click.echo(f"Stdout: {e.stdout}", err=True)
        click.echo(f"Stderr: {e.stderr}", err=True)
    except FileNotFoundError:
        click.echo("Error: 'kaggle' command not found. Please ensure Kaggle API is installed and configured in your PATH.", err=True)
    except IOError as e:
        click.echo(f"Error writing metadata file {metadata_file}: {e}", err=True)


@kaggle.command()
@click.argument('submission_file', type=click.Path(exists=True, resolve_path=True))
@click.option('--competition', required=True, type=str, help="Kaggle competition name.")
@click.option('--message', default="From PrepKit", type=str, help="Submission message.")
def submit_competition(
    submission_file: str,
    competition: str,
    message: str
) -> None:
    """
    Submits a prediction file to a Kaggle competition.
    """
    click.echo(f"Submitting {submission_file} to {competition} with message: {message}")

    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ['kaggle', 'competitions', 'submit', '-f', submission_file, '-m', message, competition],
            capture_output=True,
            text=True,
            check=True
        )
        click.echo("Kaggle Competition Submit Output:")
        click.echo(result.stdout)
        if result.stderr:
            click.echo("Kaggle Competition Submit Error:")
            click.echo(result.stderr)
        click.echo(f"Successfully submitted {submission_file} to {competition}.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error submitting to competition: {e.cmd} failed with exit code {e.returncode}", err=True)
        click.echo(f"Stdout: {e.stdout}", err=True)
        click.echo(f"Stderr: {e.stderr}", err=True)
    except FileNotFoundError:
        click.echo("Error: 'kaggle' command not found. Please ensure Kaggle API is installed and configured in your PATH.", err=True)
