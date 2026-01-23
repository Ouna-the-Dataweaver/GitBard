import pytest
from unittest.mock import patch, MagicMock
from src.pipelines.stages.hook_resolver import HookResolverStage
from src.pipelines.base import PipelineContext


def test_hook_resolver_detects_command():
    payload = {
        "object_kind": "note",
        "object_attributes": {
            "note": "Please /oc_review this",
            "noteable_type": "MergeRequest",
        },
        "project": {"id": 1},
        "merge_request": {"iid": 42},
    }
    context = PipelineContext(webhook_payload=payload)
    stage = HookResolverStage()

    with patch("src.app_old.post_gitlab_note") as mock_post:
        mock_post.return_value = {"id": 123}
        result = stage.execute(context)

    assert not result.should_stop
    assert context.command == "oc_review"


def test_hook_resolver_ignores_non_note():
    payload = {
        "object_kind": "merge_request",
        "object_attributes": {"noteable_type": "MergeRequest"},
    }
    context = PipelineContext(webhook_payload=payload)
    stage = HookResolverStage()

    result = stage.execute(context)

    assert result.should_stop


def test_hook_resolver_ignores_no_command():
    payload = {
        "object_kind": "note",
        "object_attributes": {
            "note": "This is just a comment",
            "noteable_type": "MergeRequest",
        },
        "project": {"id": 1},
    }
    context = PipelineContext(webhook_payload=payload)
    stage = HookResolverStage()

    result = stage.execute(context)

    assert result.should_stop
