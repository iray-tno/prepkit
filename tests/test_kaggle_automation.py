from types import SimpleNamespace

from click.testing import CliRunner

import kaggle_automation
from main import cli


def test_update_scores_without_wandb_does_not_raise_nameerror(monkeypatch):
    """WandB availability is checked inside update-scores before use."""
    monkeypatch.setattr(kaggle_automation, "_get_wandb", lambda: None)

    result = CliRunner().invoke(
        cli,
        ["kaggle", "update-scores", "--competition", "example-competition"],
    )

    assert result.exit_code == 0
    assert "WandB not available. Cannot update experiment scores." in result.output
    assert "NameError" not in result.output


def test_update_scores_reports_latest_score_without_active_wandb_run(monkeypatch):
    fake_wandb = SimpleNamespace(run=None)
    fake_result = SimpleNamespace(
        stdout="fileName,date,description,publicScore,status\nsubmission.csv,now,msg,0.123,complete\n"
    )

    monkeypatch.setattr(kaggle_automation, "_get_wandb", lambda: fake_wandb)
    monkeypatch.setattr(kaggle_automation.subprocess, "run", lambda *args, **kwargs: fake_result)

    result = CliRunner().invoke(
        cli,
        ["kaggle", "update-scores", "--competition", "example-competition"],
    )

    assert result.exit_code == 0
    assert "Fetching latest submissions for competition: example-competition" in result.output
    assert "Latest public score: 0.123. No WandB run specified." in result.output
