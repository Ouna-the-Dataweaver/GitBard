from pathlib import Path
from unittest.mock import MagicMock

from src.pipelines.base import PipelineContext
from src.pipelines.stages.opencode_integration import OpencodePreparationStage


def _patch_opencode_stream(monkeypatch, handler):
    def wrapped(self, args, cwd, env, detector, progress_callback=None):
        return handler(self, args, cwd, env, detector)

    monkeypatch.setattr(
        "src.pipelines.stages.opencode_integration.BaseOpencodeStage._run_opencode_streaming",
        wrapped,
    )


def test_opencode_preparation_writes_events_and_report(monkeypatch, tmp_path):
    issue_context_path = tmp_path / "gitlab_thread_context.md"
    issue_context_path.write_text("# Context\n", encoding="utf-8")

    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_ask prepare the project",
            "trigger_pattern": "/oc_ask",
            "thread_context_path": str(issue_context_path),
            "noteable_type": "MergeRequest",
        },
        code_snapshot={"source_branch": "feature", "target_branch": "main"},
    )
    stage = OpencodePreparationStage()
    captured = {}

    def fake_run(self, args, cwd, env, detector):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["env"] = env
        return MagicMock(
            returncode=0,
            stdout='{"type":"text","part":{"text":"## Installed or Prepared\\n- uv sync"}}\n',
            stderr="",
        )

    _patch_opencode_stream(monkeypatch, fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["cwd"] == str(tmp_path)
    assert captured["args"][captured["args"].index("--agent") + 1] == "gitlab-prepare"
    assert (
        "Prepare this GitLab merge request repository for work." in captured["args"][-1]
    )
    assert "User request: prepare the project" in captured["args"][-1]
    assert "Use the thread context in gitlab_thread_context.md." in captured["args"][-1]
    assert "Current review scope is feature -> main." in captured["args"][-1]
    assert (tmp_path / "opencode_prep_events.jsonl").exists()
    report_path = Path(context.metadata["prep_report_path"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "## OpenCode Preparation" in content
    assert "Status: success" in content
    assert "uv sync" in content


def test_opencode_preparation_records_failure_without_stopping(monkeypatch, tmp_path):
    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={"note_body": "/oc_ask", "trigger_pattern": "/oc_ask"},
    )
    stage = OpencodePreparationStage()

    def fake_run(self, args, cwd, env, detector):
        return MagicMock(
            returncode=1,
            stdout="",
            stderr="toolchain missing",
        )

    _patch_opencode_stream(monkeypatch, fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    report_path = Path(context.metadata["prep_report_path"])
    content = report_path.read_text(encoding="utf-8")
    assert "Status: failed" in content
    assert "toolchain missing" in content
