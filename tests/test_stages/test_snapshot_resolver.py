import pytest
from src.pipelines.stages.snapshot_resolver import SnapshotResolverStage
from src.pipelines.base import PipelineContext


def test_snapshot_resolver_mr():
    payload = {
        "object_kind": "note",
        "project": {"default_branch": "main"},
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
    assert context.code_snapshot["merge_request_state"] is None
    assert context.code_snapshot["branch"] == "feature"


def test_snapshot_resolver_mr_falls_back_to_source_branch_when_sha_missing():
    payload = {
        "object_kind": "note",
        "project": {"default_branch": "main"},
        "object_attributes": {"noteable_type": "MergeRequest"},
        "merge_request": {
            "source_branch": "db",
            "target_branch": "main",
        },
    }
    context = PipelineContext(webhook_payload=payload)
    context.metadata["noteable_type"] = "MergeRequest"
    stage = SnapshotResolverStage()

    result = stage.execute(context)

    assert not result.should_stop
    assert context.code_snapshot["sha"] is None
    assert context.code_snapshot["branch"] == "db"


def test_snapshot_resolver_mr_uses_additional_sha_candidates():
    payload = {
        "object_kind": "note",
        "project": {"default_branch": "main"},
        "object_attributes": {"noteable_type": "MergeRequest"},
        "merge_request": {
            "iid": 76,
            "state": "merged",
            "source_branch": "prod_pure",
            "target_branch": "main",
            "last_commit": {"id": "deadbeef"},
            "merge_commit_sha": "merge123",
        },
    }
    context = PipelineContext(webhook_payload=payload)
    context.metadata["noteable_type"] = "MergeRequest"
    stage = SnapshotResolverStage()

    result = stage.execute(context)

    assert not result.should_stop
    assert context.code_snapshot["sha"] == "deadbeef"
    assert context.code_snapshot["merge_request_iid"] == 76
    assert context.code_snapshot["merge_request_state"] == "merged"


def test_snapshot_resolver_issue():
    payload = {
        "object_kind": "note",
        "project": {"default_branch": "trunk"},
        "object_attributes": {"noteable_type": "Issue"},
        "issue": {"iid": 1},
    }
    context = PipelineContext(webhook_payload=payload)
    context.metadata["noteable_type"] = "Issue"
    stage = SnapshotResolverStage()

    result = stage.execute(context)

    assert not result.should_stop
    assert context.code_snapshot["branch"] == "trunk"
    assert context.code_snapshot["sha"] is None
