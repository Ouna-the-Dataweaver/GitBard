import pytest
import subprocess
from unittest.mock import patch, MagicMock
from src.pipelines.stages.context_builder import ContextBuilderStage, WorkspaceAcquisitionStage
from src.pipelines.base import PipelineContext, WorkspaceConfig


def test_workspace_acquisition_creates_temp_dir_and_sets_cleanup():
    payload = {
        "object_kind": "note",
        "project": {"git_http_url": "https://gitlab.com/test/repo.git"},
    }
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "main"}
    stage = WorkspaceAcquisitionStage()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        result = stage.execute(context)

    assert not result.should_stop
    assert context.local_context_path is not None
    assert context.local_context_path.startswith("/tmp/opencode_")
    assert context.workspace_cleanup_required is True
    assert context.metadata["workspace_cleanup_required"] is True


def test_context_builder_alias_still_works():
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


def test_workspace_acquisition_no_git_url():
    payload = {"object_kind": "note", "project": {}}
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "main"}
    stage = WorkspaceAcquisitionStage()

    result = stage.execute(context)

    assert result.should_stop
    assert result.error is not None


def test_workspace_acquisition_stops_on_clone_failure():
    payload = {
        "object_kind": "note",
        "project": {"git_http_url": "https://gitlab.com/test/repo.git"},
    }
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "main"}
    stage = WorkspaceAcquisitionStage()

    with patch("subprocess.run", side_effect=RuntimeError("clone failed")):
        result = stage.execute(context)

    assert result.should_stop
    assert str(result.error) == "clone failed"


def test_workspace_acquisition_supports_config_object():
    payload = {
        "object_kind": "note",
        "project": {"git_http_url": "https://gitlab.com/test/repo.git"},
    }
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "main"}
    stage = WorkspaceAcquisitionStage(
        workspace_config=WorkspaceConfig(mode="fresh_clone", cleanup_required=False)
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        result = stage.execute(context)

    assert not result.should_stop
    assert context.workspace_cleanup_required is False


def test_workspace_acquisition_fetches_merge_request_ref_when_branch_missing():
    payload = {
        "object_kind": "note",
        "project": {"git_http_url": "https://gitlab.com/test/repo.git"},
    }
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "prod_pure", "merge_request_iid": 76}
    stage = WorkspaceAcquisitionStage()

    def run_side_effect(args, **kwargs):
        if args[:2] == ["git", "checkout"] and args[2] == "prod_pure":
            raise subprocess.CalledProcessError(1, args, stderr=b"pathspec failed")
        return MagicMock()

    with patch("subprocess.run", side_effect=run_side_effect) as mock_run:
        result = stage.execute(context)

    assert not result.should_stop
    commands = [call.args[0] for call in mock_run.call_args_list]
    assert ["git", "checkout", "prod_pure"] in commands
    assert [
        "git",
        "fetch",
        "origin",
        "refs/merge-requests/76/head:refs/heads/mr-76",
    ] in commands
    assert ["git", "checkout", "mr-76"] in commands


def test_workspace_acquisition_reports_missing_merge_request_ref():
    payload = {
        "object_kind": "note",
        "project": {"git_http_url": "https://gitlab.com/test/repo.git"},
    }
    context = PipelineContext(webhook_payload=payload)
    context.code_snapshot = {"branch": "prod_pure", "merge_request_iid": 76}
    stage = WorkspaceAcquisitionStage()

    def run_side_effect(args, **kwargs):
        if args[:2] == ["git", "checkout"] and args[2] == "prod_pure":
            raise subprocess.CalledProcessError(1, args, stderr=b"pathspec failed")
        if args[:2] == ["git", "fetch"]:
            raise subprocess.CalledProcessError(1, args, stderr=b"ref missing")
        return MagicMock()

    with patch("subprocess.run", side_effect=run_side_effect):
        result = stage.execute(context)

    assert result.should_stop
    assert "merge request ref !76 is no longer available" in str(result.error)
