import click
import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, List


SECOND_OPINION_ASSISTANTS = {
    "claude-code": {
        "commands": ["claude"],
        "label": "Claude Code",
        "invoke": '{command} -p "$PROMPT" < /dev/null',
    },
    "codex": {
        "commands": ["codex"],
        "label": "Codex",
        "invoke": '{command} exec "$PROMPT" < /dev/null',
    },
    "antigravity-cli": {
        "commands": ["antigravity"],
        "label": "Antigravity",
        "invoke": '{command} "$PROMPT" < /dev/null',
    },
}

@click.group()
def ai_config():
    """Configure AI coding assistants for optimal PrepKit workflows."""
    pass

@ai_config.command()
@click.argument('assistant', type=click.Choice(['claude-code', 'github-copilot', 'antigravity-cli', 'all']))
@click.option('--workspace-dir', type=click.Path(), default='.', help="Target workspace directory (default: current directory)")
def setup(assistant: str, workspace_dir: str) -> None:
    """Set up AI assistant configuration files in the workspace."""
    workspace_path = Path(workspace_dir).resolve()
    config_source = Path(__file__).parent.parent / 'configs' / 'ai-assistants'
    
    click.echo(f"Setting up {assistant} configuration in {workspace_path}")
    
    if assistant == 'all':
        assistants_to_setup = ['claude-code', 'github-copilot', 'antigravity-cli']
    else:
        assistants_to_setup = [assistant]
    
    for ai_assistant in assistants_to_setup:
        setup_assistant_config(ai_assistant, config_source, workspace_path)
    
    click.echo(f"✅ AI assistant configuration complete!")

def setup_assistant_config(assistant: str, config_source: Path, workspace_path: Path) -> None:
    """Set up configuration for a specific AI assistant."""
    ai_config_dir = workspace_path / '.prepkit' / 'ai-assistants'
    ai_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy configuration file
    config_file = config_source / f"{assistant}.md"
    if config_file.exists():
        dest_file = ai_config_dir / f"{assistant}.md"
        shutil.copy2(config_file, dest_file)
        click.echo(f"📋 Copied {assistant} configuration to {dest_file}")
    
    # Setup assistant-specific files
    if assistant == 'github-copilot':
        setup_copilot_specific(workspace_path)
    elif assistant == 'claude-code':
        setup_claude_code_specific(workspace_path)
    elif assistant == 'antigravity-cli':
        setup_antigravity_specific(workspace_path)


def detect_installed_second_opinion_assistants() -> Dict[str, str]:
    """Return supported assistant names mapped to their detected CLI command."""
    installed = {}
    for assistant, config in SECOND_OPINION_ASSISTANTS.items():
        for command in config["commands"]:
            resolved = shutil.which(command)
            if resolved:
                installed[assistant] = command
                break
    return installed


def _render_second_opinion_script(target_name: str, target_command: str) -> str:
    target_config = SECOND_OPINION_ASSISTANTS[target_name]
    invocation = target_config["invoke"].format(command=target_command)
    return f'''#!/bin/bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <question or review request>" >&2
    exit 1
fi

ROOT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
CONTEXT_FILE="$ROOT_DIR/.prepkit/second-opinion/context.md"
REQUEST="$*"

if [ -f "$CONTEXT_FILE" ]; then
    CONTEXT="$(cat "$CONTEXT_FILE")"
else
    CONTEXT="No shared project context file found."
fi

PROMPT="$(cat <<EOF
You are giving an independent second opinion on a PrepKit task.

Shared project context:
$CONTEXT

Request:
$REQUEST

Respond with:
- the strongest technical concern or alternative you see
- concrete files or commands to inspect next
- assumptions that should be verified by local tests or measurements
EOF
)"

{invocation}
'''


def scaffold_second_opinion(workspace_path: Path, installed: Dict[str, str]) -> None:
    """Create symmetric second-opinion scripts for the installed assistants."""
    base_dir = workspace_path / '.prepkit' / 'second-opinion'
    base_dir.mkdir(parents=True, exist_ok=True)

    context_file = base_dir / 'context.md'
    if not context_file.exists():
        context_file.write_text('''# PrepKit Second-Opinion Context

Summarize the current task, constraints, rejected ideas, and local verification commands here before asking another assistant for review.

Ground rules:
- Treat second opinions as proposals, not truth.
- Verify suggestions with local tests, benchmarks, or targeted code inspection.
- Prefer concrete file paths, commands, and measurable claims.
''')
        click.echo(f"🧭 Created shared context primer: {context_file}")

    for source_name in installed:
        source_dir = base_dir / source_name
        source_dir.mkdir(parents=True, exist_ok=True)

        target_names = [name for name in installed if name != source_name]
        readme_lines = [
            f"# Second opinions for {SECOND_OPINION_ASSISTANTS[source_name]['label']}",
            "",
            "Use these scripts to ask a different installed assistant for an independent review.",
            "Update `../context.md` first so the consulted assistant has project-specific grounding.",
            "",
        ]

        for target_name in target_names:
            script_name = f"ask-{target_name}.sh"
            script_file = source_dir / script_name
            script_file.write_text(_render_second_opinion_script(target_name, installed[target_name]))
            script_file.chmod(0o755)
            readme_lines.append(f"- `{script_name}` asks {SECOND_OPINION_ASSISTANTS[target_name]['label']}.")

        (source_dir / "README.md").write_text("\n".join(readme_lines) + "\n")
        click.echo(f"🔁 Created {len(target_names)} second-opinion script(s) for {source_name}")

def setup_copilot_specific(workspace_path: Path) -> None:
    """Set up GitHub Copilot specific configuration."""
    vscode_dir = workspace_path / '.vscode'
    vscode_dir.mkdir(exist_ok=True)
    
    # Settings for Copilot optimization
    settings = {
        "github.copilot.enable": {
            "*": True,
            "cpp": True,
            "python": True,
            "yaml": True
        },
        "github.copilot.inlineSuggest.enable": True,
        "github.copilot.advanced": {
            "indentationMode": {
                "cpp": "space",
                "python": "space"
            }
        },
        "editor.inlineSuggest.enabled": True,
        "editor.suggest.insertMode": "replace"
    }
    
    settings_file = vscode_dir / 'settings.json'
    existing_settings = {}
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            existing_settings = json.load(f)
    
    # Merge settings
    existing_settings.update(settings)
    
    with open(settings_file, 'w') as f:
        json.dump(existing_settings, f, indent=2)
    
    click.echo(f"⚙️  Updated VS Code settings for Copilot at {settings_file}")
    
    # Create snippets for competitive programming
    snippets_dir = vscode_dir / 'snippets'
    snippets_dir.mkdir(exist_ok=True)
    
    cpp_snippets = {
        "prepkit_main": {
            "prefix": "prepkit_main",
            "body": [
                "#include <iostream>",
                "#include <vector>", 
                "#include <algorithm>",
                "using namespace std;",
                "",
                "constexpr int MOD = 1000000007;",
                "",
                "int main() {",
                "    ios::sync_with_stdio(false);",
                "    cin.tie(nullptr);",
                "    ",
                "    $0",
                "    ",
                "    return 0;",
                "}"
            ],
            "description": "PrepKit main template with fast IO"
        },
        "prepkit_debug": {
            "prefix": "prepkit_debug",
            "body": [
                "#ifdef LOCAL_DEBUG",
                "#define dbg(x) cerr << #x << \" = \" << (x) << endl",
                "#else", 
                "#define dbg(x)",
                "#endif"
            ],
            "description": "PrepKit debug utilities"
        }
    }
    
    with open(snippets_dir / 'cpp.json', 'w') as f:
        json.dump(cpp_snippets, f, indent=2)
    
    click.echo(f"📝 Created C++ snippets for competitive programming")

def setup_claude_code_specific(workspace_path: Path) -> None:
    """Set up Claude Code specific configuration."""
    claude_dir = workspace_path / '.prepkit' / 'claude-code'
    claude_dir.mkdir(parents=True, exist_ok=True)
    
    # Create context prompt files
    prompts = {
        'setup.md': '''# PrepKit Context for Claude Code

This project uses PrepKit for competitive programming and ML workflows.

Key features:
- C++ preprocessing: Include resolution, constexpr replacement, minification
- Kaggle automation: Notebook/submission handling with WandB integration  
- Experiment management: Hydra, Optuna, WandB integration
- Plugin architecture: Extensible for multiple languages

When working on competitive programming problems:
- Focus on single-file output compatibility
- Use constexpr for compile-time constants
- Consider code size for platforms like Codingame
- Ensure preprocessing-friendly include patterns
''',
        'review.md': '''# Code Review Checklist for Claude Code

For competitive programming solutions:
1. ✅ Algorithm correctness and complexity analysis
2. ✅ Edge case handling and boundary conditions
3. ✅ Integer overflow and numeric precision
4. ✅ Input/output format compliance
5. ✅ PrepKit preprocessing compatibility
6. ✅ Constexpr optimization opportunities
7. ✅ Memory usage optimization
8. ✅ Code minification readiness

For experiment management:
1. ✅ Proper WandB logging configuration
2. ✅ Hydra config structure and defaults
3. ✅ Error handling for external APIs (Kaggle)
4. ✅ Type hints and documentation
''',
        'debugging.md': '''# Debugging Guide for Claude Code

Common competitive programming issues:
- Off-by-one errors in array indexing
- Integer overflow (use long long)
- Wrong input/output format
- Time limit exceeded (algorithm choice)
- Memory limit exceeded (data structure size)

PrepKit-specific issues:
- Include path resolution failures
- Constexpr replacement not working
- Minification breaking code structure
- WandB logging connection issues
'''
    }
    
    for filename, content in prompts.items():
        prompt_file = claude_dir / filename
        with open(prompt_file, 'w') as f:
            f.write(content)
        click.echo(f"📄 Created Claude Code prompt: {filename}")

def setup_antigravity_specific(workspace_path: Path) -> None:
    """Set up Antigravity CLI specific guidance."""
    antigravity_dir = workspace_path / '.prepkit' / 'antigravity-cli'
    antigravity_dir.mkdir(parents=True, exist_ok=True)

    guide_file = antigravity_dir / 'second-opinion.md'
    guide_file.write_text('''# Antigravity CLI Second-Opinion Guide

Use `prepkit ai-config second-opinion` to create scripts that ask other installed assistants for independent review.

Before asking for review:
- update `.prepkit/second-opinion/context.md`
- include the concrete files, commands, and measurements already checked
- verify any recommendation with local tests or benchmarks
''')
    click.echo(f"📄 Created Antigravity CLI guide: {guide_file}")

@ai_config.command()
@click.option('--assistant', type=click.Choice(['claude-code', 'github-copilot', 'antigravity-cli']))
def status(assistant: Optional[str]) -> None:
    """Show status of AI assistant configurations."""
    workspace_path = Path('.').resolve()
    ai_config_dir = workspace_path / '.prepkit' / 'ai-assistants'
    
    if not ai_config_dir.exists():
        click.echo("❌ No AI assistant configurations found. Run 'setup' first.")
        return
    
    assistants_to_check = [assistant] if assistant else ['claude-code', 'github-copilot', 'antigravity-cli']
    
    for ai_assistant in assistants_to_check:
        config_file = ai_config_dir / f"{ai_assistant}.md"
        if config_file.exists():
            click.echo(f"✅ {ai_assistant}: Configured")
            if ai_assistant == 'github-copilot':
                vscode_settings = workspace_path / '.vscode' / 'settings.json'
                if vscode_settings.exists():
                    click.echo(f"   📁 VS Code settings: {vscode_settings}")
            elif ai_assistant == 'antigravity-cli':
                guide_file = workspace_path / '.prepkit' / 'antigravity-cli' / 'second-opinion.md'
                if guide_file.exists():
                    click.echo(f"   📄 Antigravity guide: {guide_file}")
        else:
            click.echo(f"❌ {ai_assistant}: Not configured")


@ai_config.command(name="second-opinion")
@click.option('--workspace-dir', type=click.Path(), default='.', help="Target workspace directory (default: current directory)")
def second_opinion(workspace_dir: str) -> None:
    """Scaffold cross-AI second-opinion scripts for installed assistant CLIs."""
    workspace_path = Path(workspace_dir).resolve()
    installed = detect_installed_second_opinion_assistants()

    if len(installed) < 2:
        click.echo("❌ Need at least two supported assistant CLIs installed for second-opinion scaffolding.")
        supported = ", ".join(SECOND_OPINION_ASSISTANTS.keys())
        click.echo(f"   Supported assistants: {supported}")
        return

    detected = ", ".join(installed.keys())
    click.echo(f"Detected assistant CLIs: {detected}")
    scaffold_second_opinion(workspace_path, installed)
    click.echo("✅ Cross-AI second-opinion scaffolding complete!")

@ai_config.command()
@click.argument('assistant', type=click.Choice(['claude-code', 'github-copilot', 'antigravity-cli']))
def docs(assistant: str) -> None:
    """Open documentation for an AI assistant."""
    workspace_path = Path('.').resolve()
    config_file = workspace_path / '.prepkit' / 'ai-assistants' / f"{assistant}.md"
    
    if config_file.exists():
        click.echo(f"📖 Opening {assistant} documentation...")
        # Try to open with default markdown viewer
        try:
            import subprocess
            subprocess.run(['open', str(config_file)], check=False)  # macOS
        except:
            try:
                subprocess.run(['xdg-open', str(config_file)], check=False)  # Linux
            except:
                click.echo(f"📄 Configuration file: {config_file}")
    else:
        click.echo(f"❌ No configuration found for {assistant}. Run setup first.")

if __name__ == '__main__':
    ai_config()
