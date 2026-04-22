from pathlib import Path
from unittest.mock import MagicMock

from src.pipelines.base import PipelineContext
from src.pipelines.stages.repo_hook_preparation import RepoHookPreparationStage


def test_repo_hook_stage_skips_when_disabled(tmp_path):
    context = PipelineContext(webhook_payload={}, local_context_path=str(tmp_path))
    stage = RepoHookPreparationStage(enabled=False)

    result = stage.execute(context)

    assert not result.should_stop
    assert "prep_report_path" not in context.metadata


def test_repo_hook_stage_skips_when_script_missing(tmp_path):
    context = PipelineContext(webhook_payload={}, local_context_path=str(tmp_path))
    stage = RepoHookPreparationStage(enabled=True)

    result = stage.execute(context)

    assert not result.should_stop
    assert "prep_report_path" not in context.metadata


def test_repo_hook_stage_runs_script_and_records_output(monkeypatch, tmp_path):
    (tmp_path / ".gitbard.sh").write_text("echo setup\n", encoding="utf-8")
    context = PipelineContext(webhook_payload={}, local_context_path=str(tmp_path))
    stage = RepoHookPreparationStage(enabled=True)

    def fake_run(args, cwd, check, capture_output, text):
        assert args == ["bash", ".gitbard.sh"]
        assert cwd == str(tmp_path)
        return MagicMock(returncode=0, stdout="installed", stderr="")

    monkeypatch.setattr(
        "src.pipelines.stages.repo_hook_preparation.subprocess.run", fake_run
    )

    result = stage.execute(context)

    assert not result.should_stop
    report_path = Path(context.metadata["prep_report_path"])
    content = report_path.read_text(encoding="utf-8")
    assert "## Repo Hook" in content
    assert "Status: success" in content
    assert "installed" in content


def test_repo_hook_stage_records_failure_without_stopping(monkeypatch, tmp_path):
    (tmp_path / ".gitbard.sh").write_text("exit 1\n", encoding="utf-8")
    context = PipelineContext(webhook_payload={}, local_context_path=str(tmp_path))
    stage = RepoHookPreparationStage(enabled=True)

    monkeypatch.setattr(
        "src.pipelines.stages.repo_hook_preparation.subprocess.run",
        lambda args, cwd, check, capture_output, text: MagicMock(
            returncode=1, stdout="", stderr="missing dependency"
        ),
    )

    result = stage.execute(context)

    assert not result.should_stop
    report_path = Path(context.metadata["prep_report_path"])
    content = report_path.read_text(encoding="utf-8")
    assert "Status: failed" in content
    assert "missing dependency" in content
