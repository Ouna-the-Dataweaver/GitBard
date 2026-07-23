import sys
from unittest.mock import MagicMock

from src.pipelines.base import PipelineContext
from src.pipelines.stages.opencode_integration import (
    BaseOpencodeStage,
    OpencodeErrorDetector,
    OpencodeIntegrationStage,
    format_agent_steps_details,
    parse_opencode_output,
    summarize_opencode_error,
)


def _patch_opencode_stream(monkeypatch, handler):
    def wrapped(self, args, cwd, env, detector, progress_callback=None):
        return handler(self, args, cwd, env, detector)

    monkeypatch.setattr(
        "src.pipelines.stages.opencode_integration.BaseOpencodeStage._run_opencode_streaming",
        wrapped,
    )


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

    def fake_run(self, args, cwd, env, detector):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["env"] = env
        return MagicMock(
            returncode=0,
            stdout='{"type":"text","part":{"text":"Answer"}}\n'
            '{"type":"text","part":{"text":" ready"}}\n',
            stderr="",
        )

    _patch_opencode_stream(monkeypatch, fake_run)

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
    assert (tmp_path / "opencode_reply.md").read_text(
        encoding="utf-8"
    ) == "Answer ready\n"


def test_parse_opencode_output_supports_text_variants_and_agent_steps():
    output = "\n".join(
        [
            '{"type":"step_start","part":{"type":"step-start"}}',
            '{"type":"tool_use","part":{"type":"tool","tool":"bash","state":{"status":"completed","title":"Run tests"}}}',
            '{"type":"message.part.updated","properties":{"part":{"id":"one","type":"text","text":"Draft"}}}',
            '{"type":"text","part":{"id":"one","text":"Answer"}}',
            '{"type":"message.part.updated","properties":{"part":{"id":"two","type":"text","text":" ready"}}}',
            '{"type":"step_finish","part":{"type":"step-finish","reason":"stop","tokens":{"output":42}}}',
        ]
    )

    parsed = parse_opencode_output(output)

    assert parsed.text == "Answer ready"
    assert parsed.steps == [
        "⏳ Agent turn 1 started",
        "✅ `bash` — Run tests",
        "✅ Agent turn 1 finished — stop, 42 output tokens",
    ]
    assert "<summary>Agent steps (3)</summary>" in format_agent_steps_details(
        parsed.steps
    )


def test_parse_opencode_output_falls_back_to_plain_stdout():
    parsed = parse_opencode_output("plain final response\n")

    assert parsed.text == "plain final response"
    assert parsed.invalid_line_count == 1


def test_opencode_agent_progress_updates_existing_note(monkeypatch, tmp_path):
    updated = []

    def fake_update(
        project_id, noteable_type, noteable_iid, note_id, body, project=None
    ):
        updated.append(body)
        return {"id": note_id}

    monkeypatch.setattr(
        "src.pipelines.stages.opencode_integration.update_gitlab_note", fake_update
    )
    context = PipelineContext(
        webhook_payload={
            "project": {"id": 1},
            "object_attributes": {
                "noteable_type": "MergeRequest",
                "noteable_iid": 2,
            },
        },
        local_context_path=str(tmp_path),
        gitlab_note_id=9,
        metadata={"noteable_type": "MergeRequest"},
    )
    output = (
        '{"type":"tool_use","part":{"type":"tool","tool":"read",'
        '"state":{"status":"completed","title":"src/app.py"}}}\n'
    )

    OpencodeIntegrationStage()._publish_agent_progress(context, output)

    assert len(updated) == 1
    assert "🤖 **OpenCode is still working**" in updated[0]
    assert "<summary>Agent steps (1)</summary>" in updated[0]
    assert "✅ `read` — src/app.py" in updated[0]
    assert context.metadata["agent_steps"] == ["✅ `read` — src/app.py"]


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

    def fake_run(self, args, cwd, env, detector):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    _patch_opencode_stream(monkeypatch, fake_run)

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

    def fake_run(self, args, cwd, env, detector):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    _patch_opencode_stream(monkeypatch, fake_run)

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
    monkeypatch.setenv("OPENCODE_COMMAND", "opencode-safe")
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

    def fake_run(self, args, cwd, env, detector):
        captured["args"] = args
        return MagicMock(returncode=0, stdout="", stderr="")

    _patch_opencode_stream(monkeypatch, fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert stage.model_source == "env"
    assert stage.agent_source == "env"
    assert captured["args"][0] == "opencode-safe"
    assert "--print-logs" in captured["args"]
    assert captured["args"][captured["args"].index("--log-level") + 1] == "DEBUG"
    assert (
        captured["args"][captured["args"].index("--model") + 1] == "openai/gpt-4.1-mini"
    )
    assert captured["args"][captured["args"].index("--agent") + 1] == "Reviewer"


def test_opencode_error_detector_stops_after_repeated_provider_errors():

    detector = OpencodeErrorDetector(max_errors=2)

    assert not detector.observe(
        "INFO service=llm providerID=minimax modelID=MiniMax-M2.7 stream"
    )
    assert detector.observed_provider == "minimax"
    assert detector.observed_model == "MiniMax-M2.7"
    assert not detector.observe("INFO service=provider init")
    assert not detector.observe(
        'ERROR service=llm error={"statusCode":429,"responseBody":"rate_limit_error"}'
    )
    assert detector.observe('ERROR service=llm error={"name":"AI_APICallError"}')
    assert detector.error_count == 2
    assert "AI_APICallError" in detector.last_error


def test_opencode_error_detector_extracts_overloaded_message_from_error_value():
    detector = OpencodeErrorDetector(max_errors=3)

    overloaded_line = (
        'timestamp=2026-07-06T09:21:24.614Z level=ERROR run=abc message="stream error" '
        "providerID=zai-coding-plan modelID=glm-5.2 "
        "session.id=ses_x small=false agent=deep_review mode=all "
        'error.error="AI_APICallError: The service may be temporarily overloaded, '
        'please try again later"'
    )

    assert not detector.observe(overloaded_line)
    assert detector.error_count == 1
    assert "AI_APICallError" in detector.last_error
    assert "temporarily overloaded" in detector.last_error
    assert "provider=zai-coding-plan" in detector.last_error
    assert "model=glm-5.2" in detector.last_error


def test_opencode_error_summary_extracts_retry_error_from_error_value():
    retry_line = (
        'timestamp=2026-07-06T09:21:57.061Z level=ERROR run=abc message="stream error" '
        "providerID=zai-coding-plan modelID=glm-5.2 "
        'error.error="AI_RetryError: Failed after 5 attempts. Last error: '
        'The service may be temporarily overloaded, please try again later"'
    )

    summary = summarize_opencode_error(retry_line)

    assert "type=AI_RetryError" in summary
    assert "Failed after 5 attempts" in summary
    assert "provider=zai-coding-plan" in summary


def test_opencode_error_summary_excludes_verbose_request_payload():
    noisy_error = (
        "ERROR service=llm providerID=minimax modelID=MiniMax-M2.7 "
        'error={"requestBody":{"system":"full system prompt",'
        '"tools":[{"name":"zai-vision_extract_text_from_screenshot",'
        '"input_schema":{"properties":{"prompt":{"description":"huge schema"}}}}],'
        '"tool_choice":{"type":"auto"}},"statusCode":429,'
        '"responseBody":"{\\"type\\":\\"error\\",\\"error\\":{\\"type\\":'
        '\\"rate_limit_error\\",\\"message\\":\\"usage limit exceeded (2056)\\"},'
        '\\"request_id\\":\\"0665ac5db826cbcccf3123e0f7848029\\"}",'
        '"isRetryable":true} stream error'
    )

    summary = summarize_opencode_error(noisy_error)

    assert "status=429" in summary
    assert "type=rate_limit_error" in summary
    assert "message=usage limit exceeded (2056)" in summary
    assert "request_id=0665ac5db826cbcccf3123e0f7848029" in summary
    assert "retryable=true" in summary
    assert "full system prompt" not in summary
    assert "input_schema" not in summary
    assert "zai-vision" not in summary


def test_opencode_integration_reports_summarized_failure(monkeypatch, tmp_path):
    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(tmp_path),
        metadata={
            "note_body": "/oc_ask check this",
            "trigger_pattern": "/oc_ask",
        },
    )
    stage = OpencodeIntegrationStage()

    def fake_run(self, args, cwd, env, detector):
        return MagicMock(
            returncode=1,
            stdout="",
            stderr=(
                'ERROR service=llm error={"requestBody":{"system":"secret prompt"},'
                '"statusCode":429,"responseBody":"{\\"type\\":\\"error\\",'
                '\\"error\\":{\\"type\\":\\"rate_limit_error\\",\\"message\\":'
                '\\"usage limit exceeded (2056)\\"},\\"request_id\\":\\"req_123\\"}",'
                '"isRetryable":true} stream error'
            ),
        )

    _patch_opencode_stream(monkeypatch, fake_run)

    result = stage.execute(context)

    assert result.should_stop
    error_text = str(result.error)
    assert "opencode run failed" in error_text
    assert "status=429" in error_text
    assert "type=rate_limit_error" in error_text
    assert "secret prompt" not in error_text
    assert "requestBody" not in error_text


def test_opencode_streaming_writes_live_logs(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCODE_HEARTBEAT_SECONDS", "0")
    stage = BaseOpencodeStage()
    detector = OpencodeErrorDetector()

    result = stage._run_opencode_streaming(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ],
        str(tmp_path),
        {},
        detector,
    )

    assert result.returncode == 0
    assert (tmp_path / "opencode_stdout.jsonl").read_text(encoding="utf-8") == "out\n"
    assert (tmp_path / "opencode_stderr.log").read_text(encoding="utf-8") == "err\n"
    status = (tmp_path / "opencode_status.log").read_text(encoding="utf-8")
    assert "started pid=" in status
    assert "finished returncode=0" in status


def test_opencode_streaming_publishes_periodic_agent_progress(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENCODE_HEARTBEAT_SECONDS", "0")
    monkeypatch.setenv("GITBARD_AGENT_PROGRESS_INTERVAL_SECONDS", "1")
    stage = BaseOpencodeStage()
    progress_outputs = []

    result = stage._run_opencode_streaming(
        [
            sys.executable,
            "-c",
            (
                "import time; "
                'print(\'{"type":"tool_use","part":{"type":"tool",'
                '"tool":"read","state":{"status":"completed",'
                '"title":"app.py"}}}\', flush=True); '
                "time.sleep(1.2)"
            ),
        ],
        str(tmp_path),
        {},
        OpencodeErrorDetector(),
        progress_callback=progress_outputs.append,
    )

    assert result.returncode == 0
    assert progress_outputs
    assert parse_opencode_output(progress_outputs[-1]).steps == ["✅ `read` — app.py"]


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

    def fake_run(self, args, cwd, env, detector):
        captured["args"] = args
        captured["env"] = env
        return MagicMock(returncode=0, stdout="", stderr="")

    _patch_opencode_stream(monkeypatch, fake_run)

    result = stage.execute(context)

    assert not result.should_stop
    assert captured["args"][captured["args"].index("--agent") + 1] == "gitlab-review"
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

    def fake_run(self, args, cwd, env, detector):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    _patch_opencode_stream(monkeypatch, fake_run)

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


def test_opencode_integration_uses_thread_context_and_state_for_review(
    monkeypatch, tmp_path
):
    thread_context_path = tmp_path / "gitlab_thread_context.md"
    thread_context_path.write_text("# MR context\n", encoding="utf-8")

    context = PipelineContext(
        webhook_payload={},
        command="oc_review",
        local_context_path=str(tmp_path),
        code_snapshot={
            "source_branch": "feature",
            "target_branch": "main",
            "merge_request_state": "merged",
        },
        metadata={
            "note_body": "/oc_review",
            "trigger_pattern": "/oc_review",
            "noteable_type": "MergeRequest",
            "thread_context_path": str(thread_context_path),
        },
    )
    stage = OpencodeIntegrationStage(agent="gitlab-review")
    captured = {}

    def fake_run(self, args, cwd, env, detector):
        captured["prompt"] = args[-1]
        return MagicMock(returncode=0, stdout="", stderr="")

    _patch_opencode_stream(monkeypatch, fake_run)

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


def test_opencode_integration_rejects_historical_review_without_thread_context(
    tmp_path,
):
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
    assert "Cannot review this merge request reliably because it is not open" in str(
        result.error
    )
