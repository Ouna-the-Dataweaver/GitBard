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

    def fake_run(args, cwd, check, capture_output, text, env):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["env"] = env
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
            "If this is a merge request, summarize the MR first and then provide a concise review.",
            "Use the thread context in gitlab_issue_content.md.",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )
    assert captured["env"]["OPENCODE_CONFIG"].endswith("/GitBard/opencode.json")
    assert context.agent_result is not None
    assert context.agent_result.content == "Answer ready"
    assert (tmp_path / "opencode_events.jsonl").exists()
    assert (tmp_path / "opencode_reply.md").read_text(encoding="utf-8") == "Answer ready\n"


def test_opencode_integration_includes_prep_report_when_present(monkeypatch, tmp_path):
    prep_report_path = tmp_path / "opencode_prep_report.md"
    prep_report_path.write_text("# Prep\n", encoding="utf-8")

    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_ask why is the pipeline failing?",
            "trigger_pattern": "/oc_ask",
            "prep_report_path": str(prep_report_path),
        },
    )
    stage = OpencodeIntegrationStage()
    captured = {}

    def fake_run(args, cwd, check, capture_output, text, env):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["prompt"] == "\n\n".join(
        [
            "Answer this GitLab thread question:",
            "why is the pipeline failing?",
            "Work inside the checked out repository.",
            "If this is a merge request, summarize the MR first and then provide a concise review.",
            "Review the preparation report in opencode_prep_report.md before answering.",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )


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

    def fake_run(args, cwd, check, capture_output, text, env):
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

    def fake_run(args, cwd, check, capture_output, text, env):
        captured["args"] = args
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["args"][5] == "openai/gpt-4.1-mini"
    assert captured["args"][7] == "Reviewer"


def test_opencode_integration_uses_review_prompt_and_agent(monkeypatch, tmp_path):
    context = PipelineContext(
        webhook_payload={},
        command="oc_review",
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_review focus on auth changes",
            "trigger_pattern": "/oc_review",
            "noteable_type": "MergeRequest",
        },
    )
    stage = OpencodeIntegrationStage(agent="gitlab-review")
    captured = {}

    def fake_run(args, cwd, check, capture_output, text, env):
        captured["args"] = args
        captured["env"] = env
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["args"][7] == "gitlab-review"
    assert captured["args"][-1] == "\n\n".join(
        [
            "Review this GitLab merge request.",
            "Work inside the checked out repository.",
            "Inspect the actual changed files and diff before writing findings.",
            "If this is a merge request, summarize the MR briefly before listing findings.",
            "If a GitLab merge request context file is available, treat its MR changes as the canonical diff.",
            "Do not infer additions or deletions by comparing the checked out repository to the current target branch when branch tips may have moved.",
            "Additional reviewer request: focus on auth changes",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )
    assert captured["env"]["OPENCODE_CONFIG"].endswith("/GitBard/opencode.json")


def test_opencode_integration_strips_mention_for_review_request(monkeypatch, tmp_path):
    context = PipelineContext(
        webhook_payload={},
        command="oc_review",
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "@nid-bugbard focus on auth changes",
            "trigger_pattern": "@nid-bugbard",
            "noteable_type": "MergeRequest",
        },
    )
    stage = OpencodeIntegrationStage(agent="gitlab-review")
    captured = {}

    def fake_run(args, cwd, check, capture_output, text, env):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["prompt"] == "\n\n".join(
        [
            "Review this GitLab merge request.",
            "Work inside the checked out repository.",
            "Inspect the actual changed files and diff before writing findings.",
            "If this is a merge request, summarize the MR briefly before listing findings.",
            "If a GitLab merge request context file is available, treat its MR changes as the canonical diff.",
            "Do not infer additions or deletions by comparing the checked out repository to the current target branch when branch tips may have moved.",
            "Additional reviewer request: focus on auth changes",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )


def test_opencode_integration_uses_thread_context_and_state_for_review(monkeypatch, tmp_path):
    thread_context_path = tmp_path / "gitlab_thread_context.md"
    thread_context_path.write_text("# MR context\n", encoding="utf-8")

    context = PipelineContext(
        webhook_payload={},
        command="oc_review",
        local_context_path=str(tmp_path),
        code_snapshot={"source_branch": "feature", "target_branch": "main", "merge_request_state": "merged"},
        metadata={
            "note_body": "/oc_review",
            "trigger_pattern": "/oc_review",
            "noteable_type": "MergeRequest",
            "thread_context_path": str(thread_context_path),
        },
    )
    stage = OpencodeIntegrationStage(agent="gitlab-review")
    captured = {}

    def fake_run(args, cwd, check, capture_output, text, env):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("src.pipelines.stages.opencode_integration.subprocess.run", fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["prompt"] == "\n\n".join(
        [
            "Review this GitLab merge request.",
            "Work inside the checked out repository.",
            "Inspect the actual changed files and diff before writing findings.",
            "If this is a merge request, summarize the MR briefly before listing findings.",
            "If a GitLab merge request context file is available, treat its MR changes as the canonical diff.",
            "Do not infer additions or deletions by comparing the checked out repository to the current target branch when branch tips may have moved.",
            "Use the thread context in gitlab_thread_context.md.",
            "Current review scope is feature -> main.",
            "Merge request state: merged.",
            "Base the answer on the local repository and the provided GitLab context file.",
        ]
    )


def test_opencode_integration_rejects_historical_review_without_thread_context(tmp_path):
    context = PipelineContext(
        webhook_payload={},
        command="oc_review",
        local_context_path=str(tmp_path),
        code_snapshot={"merge_request_state": "merged"},
        metadata={
            "note_body": "/oc_review",
            "trigger_pattern": "/oc_review",
            "noteable_type": "MergeRequest",
        },
    )
    stage = OpencodeIntegrationStage(agent="gitlab-review")

    result = stage.execute(context)

    assert result.should_stop
    assert (
        "Cannot review this merge request reliably because it is not open"
        in str(result.error)
    )
