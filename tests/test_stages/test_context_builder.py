import pytest
from unittest.mock import patch, MagicMock
from src.pipelines.stages.context_builder import ContextBuilderStage
from src.pipelines.base import PipelineContext


def test_context_builder_creates_temp_dir():
    payload = {
        "object_kind": "note",
        "project": {"git_http_url": "https://gitlab.com/test/repo.git"},
    }
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "main"}
    stage = ContextBuilderStage()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        result = stage.execute(context)

    assert not result.should_stop
    assert context.local_context_path is not None
    assert context.local_context_path.startswith("/tmp/opencode_")


def test_context_builder_no_git_url():
    payload = {"object_kind": "note", "project": {}}
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "main"}
    stage = ContextBuilderStage()

    result = stage.execute(context)

    assert result.should_stop
    assert result.error is not None
