from unittest.mock import MagicMock

from src.pipelines.base import PipelineContext
from src.pipelines.stages.opencode_integration import OpencodeIntegrationStage


def test_opencode_integration_uses_question_and_issue_context(monkeypatch, tmp_path):
    issue_context_path = tmp_path / "gitlab_issue_content.md"
    issue_context_path.write_text("# Issue context\n", encoding="utf-8")

    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_ask why is the pipeline failing?",
            "trigger_pattern": "/oc_ask",
            "thread_context_path": str(issue_context_path),
        },
    )
    stage = OpencodeIntegrationStage()
    captured = {}

    def fake_run(args, cwd, check, capture_output, text):
        captured["args"] = args
        captured["cwd"] = cwd
        return MagicMock(
            returncode=0,
            stdout='{"type":"text","part":{"text":"Answer"}}\n'
            '{"type":"text","part":{"text":" ready"}}\n',
            stderr="",
        )

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["cwd"] == str(tmp_path)
    assert captured["args"][-1] == "\n\n".join(
        [
            "Answer this GitLab thread question:",
            "why is the pipeline failing?",
            "Work inside the checked out repository.",
            "Use the thread context in gitlab_issue_content.md.",
            "If this is a merge request, summarize the MR first and then provide a concise review.",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )
    assert context.agent_result is not None
    assert context.agent_result.content == "Answer ready"
    assert (tmp_path / "opencode_events.jsonl").exists()
    assert (tmp_path / "opencode_reply.md").read_text(encoding="utf-8") == "Answer ready\n"


def test_opencode_integration_defaults_when_question_missing(monkeypatch, tmp_path):
    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_ask",
            "trigger_pattern": "/oc_ask",
        },
    )
    stage = OpencodeIntegrationStage()
    captured = {}

    def fake_run(args, cwd, check, capture_output, text):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["prompt"] == "\n\n".join(
        [
            "Answer this GitLab thread question:",
            "No additional question provided.",
            "Work inside the checked out repository.",
            "If this is a merge request, summarize the MR first and then provide a concise review.",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )
    assert context.agent_result is not None
    assert context.agent_result.content == "No response generated."


def test_opencode_integration_uses_env_model_and_agent(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCODE_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("OPENCODE_AGENT", "Reviewer")

    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_ask check this",
            "trigger_pattern": "/oc_ask",
        },
    )
    stage = OpencodeIntegrationStage()
    captured = {}

    def fake_run(args, cwd, check, capture_output, text):
        captured["args"] = args
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["args"][5] == "openai/gpt-4.1-mini"
    assert captured["args"][7] == "Reviewer"
