import click
import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

@click.group()
def ai_config():
    """Configure AI coding assistants for optimal PrepKit workflows."""
    pass

@ai_config.command()
@click.argument('assistant', type=click.Choice(['claude-code', 'github-copilot', 'gemini-cli', 'all']))
@click.option('--workspace-dir', type=click.Path(), default='.', help="Target workspace directory (default: current directory)")
def setup(assistant: str, workspace_dir: str) -> None:
    """Set up AI assistant configuration files in the workspace."""
    workspace_path = Path(workspace_dir).resolve()
    config_source = Path(__file__).parent.parent / 'configs' / 'ai-assistants'
    
    click.echo(f"Setting up {assistant} configuration in {workspace_path}")
    
    if assistant == 'all':
        assistants_to_setup = ['claude-code', 'github-copilot', 'gemini-cli']
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
    elif assistant == 'gemini-cli':
        setup_gemini_specific(workspace_path)

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

def setup_gemini_specific(workspace_path: Path) -> None:
    """Set up Gemini CLI specific configuration."""
    gemini_dir = workspace_path / '.prepkit' / 'gemini-cli' 
    gemini_dir.mkdir(parents=True, exist_ok=True)
    
    # Create shell scripts for common tasks
    scripts = {
        'analyze-cp.sh': '''#!/bin/bash
# Analyze competitive programming code with Gemini

if [ $# -ne 1 ]; then
    echo "Usage: $0 <cpp_file>"
    exit 1
fi

gemini-cli "
As an expert in competitive programming, analyze this C++ code:

$(cat $1)

Please check:
1. Algorithm correctness and complexity
2. Edge cases and boundary conditions
3. Input/output format correctness  
4. Potential optimization opportunities
5. PrepKit preprocessing compatibility

Provide specific improvements and explain reasoning.
"
''',
        'optimize-code.sh': '''#!/bin/bash
# Optimize code for competitive programming

if [ $# -ne 1 ]; then
    echo "Usage: $0 <cpp_file>" 
    exit 1
fi

gemini-cli "
Optimize this C++ competitive programming code for performance:

$(cat $1)

Focus on:
- Time complexity improvements
- Memory usage optimization
- Constant factor optimizations
- PrepKit constexpr opportunities
- Code size reduction for minification

Provide optimized version with explanations.
"
''',
        'generate-tests.sh': '''#!/bin/bash
# Generate test cases with Gemini

if [ $# -ne 1 ]; then
    echo "Usage: $0 <problem_statement_file>"
    exit 1
fi

gemini-cli "
Generate comprehensive test cases for this competitive programming problem:

$(cat $1)

Include:
- Sample input/output from problem  
- Edge cases (min/max constraints)
- Corner cases (empty, single elements)
- Stress test cases (large inputs)

Format each as:
INPUT:
[test case]
EXPECTED OUTPUT:  
[expected result]
"
'''
    }
    
    for script_name, script_content in scripts.items():
        script_file = gemini_dir / script_name
        with open(script_file, 'w') as f:
            f.write(script_content)
        script_file.chmod(0o755)  # Make executable
        click.echo(f"🔧 Created Gemini script: {script_name}")

@ai_config.command()
@click.option('--assistant', type=click.Choice(['claude-code', 'github-copilot', 'gemini-cli']))
def status(assistant: Optional[str]) -> None:
    """Show status of AI assistant configurations."""
    workspace_path = Path('.').resolve()
    ai_config_dir = workspace_path / '.prepkit' / 'ai-assistants'
    
    if not ai_config_dir.exists():
        click.echo("❌ No AI assistant configurations found. Run 'setup' first.")
        return
    
    assistants_to_check = [assistant] if assistant else ['claude-code', 'github-copilot', 'gemini-cli']
    
    for ai_assistant in assistants_to_check:
        config_file = ai_config_dir / f"{ai_assistant}.md"
        if config_file.exists():
            click.echo(f"✅ {ai_assistant}: Configured")
            if ai_assistant == 'github-copilot':
                vscode_settings = workspace_path / '.vscode' / 'settings.json'
                if vscode_settings.exists():
                    click.echo(f"   📁 VS Code settings: {vscode_settings}")
            elif ai_assistant == 'gemini-cli':
                gemini_dir = workspace_path / '.prepkit' / 'gemini-cli'
                if gemini_dir.exists():
                    scripts = list(gemini_dir.glob('*.sh'))
                    click.echo(f"   🔧 Scripts available: {len(scripts)}")
        else:
            click.echo(f"❌ {ai_assistant}: Not configured")

@ai_config.command()
@click.argument('assistant', type=click.Choice(['claude-code', 'github-copilot', 'gemini-cli']))
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