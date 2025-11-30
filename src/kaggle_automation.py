import click
import subprocess
import os
import json
import time
import re
from typing import Any, Dict, Optional

def _log_to_wandb(submission_info: Dict[str, Any], competition: str, message: str) -> None:
    """Log Kaggle submission information to WandB if available and currently running."""
    try:
        import wandb
        WANDB_AVAILABLE = True
    except ImportError:
        WANDB_AVAILABLE = False

    if not WANDB_AVAILABLE:
        click.echo("WandB not available. Skipping experiment logging.")
        return

    try:
        # Check if wandb is already initialized (i.e., we're in an active experiment)
        if wandb.run is not None:
            wandb.log({
                "kaggle_competition": competition,
                "kaggle_submission_message": message,
                "kaggle_submission_id": submission_info.get("submission_id"),
                "kaggle_submission_status": submission_info.get("status", "submitted"),
                "kaggle_submission_timestamp": time.time()
            })
            click.echo(f"Logged submission to WandB run: {wandb.run.name}")
        else:
            click.echo("No active WandB run found. To link submissions with experiments, run this command within a WandB experiment context.")
    except Exception as e:
        click.echo(f"Warning: Failed to log to WandB: {e}")

def _parse_submission_response(output: str) -> Dict[str, Any]:
    """Parse Kaggle submission response to extract submission ID and status."""
    info = {}
    
    # Try to extract submission ID from output
    submission_id_match = re.search(r'Successfully submitted to (.+)', output)
    if submission_id_match:
        info["status"] = "submitted"
        
    # Look for submission confirmation patterns
    if "Successfully submitted" in output:
        info["status"] = "submitted"
    elif "error" in output.lower() or "failed" in output.lower():
        info["status"] = "failed"
    else:
        info["status"] = "unknown"
        
    return info

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
@click.option('--log-wandb', is_flag=True, help="Log notebook push to WandB if run is active.")
def push_notebook(
    notebook_file: str,
    title: Optional[str],
    slug: Optional[str],
    language: str,
    private: bool,
    log_wandb: bool
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
        
        # Log to WandB if requested
        if log_wandb:
            notebook_info = {
                "status": "pushed",
                "notebook_file": notebook_name,
                "title": title,
                "slug": slug
            }
            _log_to_wandb(notebook_info, "kaggle-notebook", f"Pushed notebook: {title}")
        
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
@click.option('--log-wandb', is_flag=True, help="Log submission to WandB if run is active.")
def submit_competition(
    submission_file: str,
    competition: str,
    message: str,
    log_wandb: bool
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
        
        # Log to WandB if requested
        if log_wandb:
            submission_info = _parse_submission_response(result.stdout)
            submission_info["submission_file"] = os.path.basename(submission_file)
            _log_to_wandb(submission_info, competition, message)
        
    except subprocess.CalledProcessError as e:
        click.echo(f"Error submitting to competition: {e.cmd} failed with exit code {e.returncode}", err=True)
        click.echo(f"Stdout: {e.stdout}", err=True)
        click.echo(f"Stderr: {e.stderr}", err=True)
    except FileNotFoundError:
        click.echo("Error: 'kaggle' command not found. Please ensure Kaggle API is installed and configured in your PATH.", err=True)


@kaggle.command()
@click.option('--competition', required=True, type=str, help="Kaggle competition name.")
@click.option('--wandb-run-id', type=str, help="WandB run ID to update with scores. If not provided, uses active run.")
@click.option('--project', type=str, help="WandB project name. Required if run-id is provided.")
def update_scores(
    competition: str,
    wandb_run_id: Optional[str],
    project: Optional[str]
) -> None:
    """
    Fetch latest Kaggle submission scores and update WandB experiment with results.
    Useful for linking local experiment metrics with competition performance.
    """
    if not WANDB_AVAILABLE:
        click.echo("WandB not available. Cannot update experiment scores.", err=True)
        return
        
    click.echo(f"Fetching latest submissions for competition: {competition}")
    
    try:
        # Get latest submissions
        result: subprocess.CompletedProcess = subprocess.run(
            ['kaggle', 'competitions', 'submissions', competition],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse submissions (simplified - would need more robust parsing)
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:  # Skip header
            latest_submission = lines[1].split(',')  # Assuming CSV output
            if len(latest_submission) >= 4:
                try:
                    public_score = float(latest_submission[3])  # Assuming score is 4th column
                    
                    # Update WandB run with scores
                    if wandb_run_id and project:
                        # Resume specific run
                        wandb.init(project=project, id=wandb_run_id, resume="allow")
                        wandb.log({
                            "kaggle_public_score": public_score,
                            "kaggle_score_updated": time.time()
                        })
                        wandb.finish()
                        click.echo(f"Updated WandB run {wandb_run_id} with public score: {public_score}")
                    elif wandb.run is not None:
                        # Use active run
                        wandb.log({
                            "kaggle_public_score": public_score,
                            "kaggle_score_updated": time.time()
                        })
                        click.echo(f"Updated active WandB run with public score: {public_score}")
                    else:
                        click.echo(f"Latest public score: {public_score}. No WandB run specified.")
                        
                except (ValueError, IndexError) as e:
                    click.echo(f"Could not parse score from submission data: {e}")
            else:
                click.echo("Insufficient submission data returned.")
        else:
            click.echo("No submissions found for this competition.")
            
    except subprocess.CalledProcessError as e:
        click.echo(f"Error fetching submissions: {e.cmd} failed with exit code {e.returncode}", err=True)
        click.echo(f"Stdout: {e.stdout}", err=True)
        click.echo(f"Stderr: {e.stderr}", err=True)
    except FileNotFoundError:
        click.echo("Error: 'kaggle' command not found. Please ensure Kaggle API is installed and configured in your PATH.", err=True)