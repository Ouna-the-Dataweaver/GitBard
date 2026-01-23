import pytest
from src.pipelines.stages.snapshot_resolver import SnapshotResolverStage
from src.pipelines.base import PipelineContext


def test_snapshot_resolver_mr():
    payload = {
        "object_kind": "note",
        "object_attributes": {"noteable_type": "MergeRequest"},
        "merge_request": {
            "diff_refs": {"head_sha": "abc123"},
            "source_branch": "feature",
            "target_branch": "main",
        },
    }
    context = PipelineContext(webhook_payload=payload)
    context.metadata["noteable_type"] = "MergeRequest"
    stage = SnapshotResolverStage()

    result = stage.execute(context)

    assert not result.should_stop
    assert context.code_snapshot["sha"] == "abc123"
    assert context.code_snapshot["source_branch"] == "feature"


def test_snapshot_resolver_issue():
    payload = {
        "object_kind": "note",
        "object_attributes": {"noteable_type": "Issue"},
        "issue": {"iid": 1},
    }
    context = PipelineContext(webhook_payload=payload)
    context.metadata["noteable_type"] = "Issue"
    stage = SnapshotResolverStage()

    result = stage.execute(context)

    assert not result.should_stop
    assert context.code_snapshot["branch"] == "main"
    assert context.code_snapshot["sha"] is None
