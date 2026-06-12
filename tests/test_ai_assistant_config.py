from click.testing import CliRunner

import ai_assistant_config
from main import cli


def test_second_opinion_requires_at_least_two_assistants(tmp_path, monkeypatch):
    """Second-opinion scaffolding needs at least two detected CLIs."""
    monkeypatch.setattr(ai_assistant_config.shutil, "which", lambda command: None)

    result = CliRunner().invoke(
        cli,
        ["ai-config", "second-opinion", "--workspace-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Need at least two supported assistant CLIs" in result.output
    assert not (tmp_path / ".prepkit" / "second-opinion").exists()


def test_second_opinion_scaffolds_symmetric_scripts(tmp_path, monkeypatch):
    """Each detected assistant gets scripts for the other detected assistants."""
    installed_commands = {"claude": "/usr/bin/claude", "codex": "/usr/bin/codex"}
    monkeypatch.setattr(
        ai_assistant_config.shutil,
        "which",
        lambda command: installed_commands.get(command),
    )

    result = CliRunner().invoke(
        cli,
        ["ai-config", "second-opinion", "--workspace-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Detected assistant CLIs: claude-code, codex" in result.output

    base_dir = tmp_path / ".prepkit" / "second-opinion"
    assert (base_dir / "context.md").exists()

    claude_to_codex = base_dir / "claude-code" / "ask-codex.sh"
    codex_to_claude = base_dir / "codex" / "ask-claude-code.sh"
    assert claude_to_codex.exists()
    assert codex_to_claude.exists()
    assert not (base_dir / "claude-code" / "ask-claude-code.sh").exists()

    assert 'codex exec "$PROMPT" < /dev/null' in claude_to_codex.read_text()
    assert 'claude -p "$PROMPT" < /dev/null' in codex_to_claude.read_text()
    assert "ask-codex.sh" in (base_dir / "claude-code" / "README.md").read_text()
