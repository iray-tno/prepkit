"""Project management commands."""
import click
import shutil
import os
import yaml


@click.group(name="project")
def project():
    """Project management commands."""
    pass


@project.command(name="new")
@click.argument('project_name')
@click.option('--lang', default='cpp', help='Programming language for the boilerplate (e.g., cpp).')
@click.option('--type', default='atcoder-algorithm', help='Preconfigured project type (e.g., atcoder-algorithm, codingame, kaggle).')
def new(project_name, lang, type):
    """
    Creates a new project boilerplate in the specified directory.
    """
    boilerplate_path = os.path.join(os.path.dirname(__file__), '..', 'boilerplate', lang)
    project_configs_path = os.path.join(os.path.dirname(__file__), '..', 'boilerplate', 'project_configs.yaml')
    destination_path = os.path.join(os.getcwd(), project_name)

    if not os.path.exists(boilerplate_path):
        click.echo(f"Error: Boilerplate for language '{lang}' not found.", err=True)
        return

    if os.path.exists(destination_path):
        click.echo(f"Error: Project directory '{project_name}' already exists.", err=True)
        return

    try:
        shutil.copytree(boilerplate_path, destination_path)
        click.echo(f"Successfully created new {lang} project '{project_name}' at {destination_path}")

        # Load project configurations
        with open(project_configs_path, 'r') as f:
            all_project_configs = yaml.safe_load(f)

        selected_config = all_project_configs.get(type)
        if not selected_config:
            click.echo(f"Warning: Project type '{type}' not found in configurations. Using default settings.", err=True)
            selected_config = {}

        # Write prepkit_config.yaml to the new project directory
        prepkit_config_content = {
            "project_type": type,
            "cpp_preprocess": selected_config.get("cpp_preprocess", {"minify_output": False}) # Default to no minify
        }
        with open(os.path.join(destination_path, "prepkit_config.yaml"), 'w') as f:
            yaml.dump(prepkit_config_content, f, indent=2)
        click.echo(f"Generated prepkit_config.yaml for type '{type}' in {project_name}")

        # Setup Claude Code settings based on contest type
        claude_config = selected_config.get("claude_config", {})
        if claude_config:
            claude_dir = os.path.join(destination_path, ".claude")
            os.makedirs(claude_dir, exist_ok=True)

            # Determine which Claude settings template to use
            claude_settings_file = None
            if claude_config.get("enabled", False):
                platform = selected_config.get("contest_settings", {}).get("platform", "")
                if platform == "kaggle":
                    claude_settings_file = "kaggle_settings.json"
                elif platform == "codingame":
                    claude_settings_file = "codingame_settings.json"
                else:
                    claude_settings_file = "kaggle_settings.json"  # Default enabled config
            else:
                claude_settings_file = "disabled_settings.json"

            # Copy the appropriate Claude settings
            if claude_settings_file:
                claude_template_path = os.path.join(os.path.dirname(__file__), "..", "boilerplate", "claude_configs", claude_settings_file)
                claude_dest_path = os.path.join(claude_dir, "settings.json")

                try:
                    shutil.copy2(claude_template_path, claude_dest_path)
                    if claude_config.get("enabled", False):
                        click.echo(f"✓ Claude Code enabled for {type} ({claude_config.get('reason', 'AI assistance allowed')})")
                    else:
                        click.echo(f"✗ Claude Code disabled for {type} ({claude_config.get('reason', 'Contest rules prohibit AI assistance')})")
                except FileNotFoundError:
                    click.echo(f"Warning: Claude settings template '{claude_settings_file}' not found", err=True)

    except Exception as e:
        click.echo(f"Error creating project: {e}", err=True)
