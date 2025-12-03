"""Configuration file loading for PrepKit."""
import os
import yaml
import click
from typing import Dict, Any


def load_config() -> Dict[str, Any]:
    """Load prepkit_config.yaml from current directory if it exists."""
    config_file_path = os.path.join(os.getcwd(), "prepkit_config.yaml")
    if os.path.exists(config_file_path):
        try:
            with open(config_file_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            click.echo(f"Warning: Error reading prepkit_config.yaml: {e}. Using defaults.", err=True)
            return {}
    return {}
