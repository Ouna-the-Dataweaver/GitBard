from pathlib import Path

import pytest
from src.pipelines.base import Pipeline, Stage, StageResult, PipelineContext


class MockStage(Stage):
    def _execute(self, context: PipelineContext) -> StageResult:
        context.metadata["executed"] = True
        return StageResult(context=context, should_stop=False)


def test_pipeline_execution():
    context = PipelineContext(webhook_payload={})
    stages = [MockStage(), MockStage()]
    pipeline = Pipeline(name="test", stages=stages)

    result = pipeline.execute(context)

    assert result.success
    assert context.metadata["executed"]


def test_pipeline_stop_on_error():
    class ErrorStage(Stage):
        def _execute(self, context: PipelineContext) -> StageResult:
            raise ValueError("Test error")

    context = PipelineContext(webhook_payload={})
    stages = [MockStage(), ErrorStage(), MockStage()]
    pipeline = Pipeline(name="test", stages=stages)

    result = pipeline.execute(context)

    assert not result.success
    assert result.error is not None


def test_pipeline_publishes_error_to_remaining_note_updater():
    class ErrorStage(Stage):
        def _execute(self, context: PipelineContext) -> StageResult:
            raise ValueError("opencode failed")

    class NoteUpdaterStage(Stage):
        def _execute(self, context: PipelineContext) -> StageResult:
            context.metadata["published_error"] = context.metadata.get("pipeline_error")
            return StageResult(context=context)

    context = PipelineContext(webhook_payload={})
    pipeline = Pipeline(name="test", stages=[ErrorStage(), NoteUpdaterStage()])

    result = pipeline.execute(context)

    assert not result.success
    assert context.metadata["pipeline_error"] == "opencode failed"
    assert context.metadata["published_error"] == "opencode failed"


def test_pipeline_publishes_progress_notes(monkeypatch):
    posted = []
    updated = []

    def fake_post(project_id, noteable_type, noteable_iid, body, project=None):
        posted.append((project_id, noteable_type, noteable_iid, body))
        return {"id": 99}

    def fake_update(project_id, noteable_type, noteable_iid, note_id, body, project=None):
        updated.append((project_id, noteable_type, noteable_iid, note_id, body))
        return {"id": note_id}

    monkeypatch.setattr("src.pipelines.base.post_gitlab_note", fake_post)
    monkeypatch.setattr("src.pipelines.base.update_gitlab_note", fake_update)
    monkeypatch.setattr("src.pipelines.base.time.monotonic", lambda: 10.0)

    context = PipelineContext(
        webhook_payload={
            "object_kind": "note",
            "project": {"id": 123},
            "object_attributes": {
                "noteable_type": "Issue",
                "noteable_iid": 7,
            },
        },
        command="oc_ask",
        metadata={"noteable_type": "Issue"},
    )
    pipeline = Pipeline(name="test", stages=[MockStage()])

    result = pipeline.execute(context)

    assert result.success
    assert posted == []

    MockStage.__name__ = "WorkspaceAcquisitionStage"
    try:
        pipeline = Pipeline(name="test", stages=[MockStage()])
        pipeline.execute(context)
    finally:
        MockStage.__name__ = "MockStage"

    assert posted[-1] == (
        123,
        "Issue",
        7,
        "🤖 **OpenCode progress (1/1)**\n\nPreparing workspace.",
    )
    assert updated == []

    context.gitlab_note_id = 99
    context.metadata.pop("progress_note_last_publish_at", None)
    MockStage.__name__ = "WorkspaceAcquisitionStage"
    try:
        pipeline = Pipeline(name="test", stages=[MockStage()])
        pipeline.execute(context)
    finally:
        MockStage.__name__ = "MockStage"

    assert updated[-1] == (
        123,
        "Issue",
        7,
        99,
        "🤖 **OpenCode progress (1/1)**\n\nPreparing workspace.",
    )


def test_pipeline_throttles_progress_note_updates(monkeypatch):
    updated = []

    class SnapshotStage(MockStage):
        pass

    class WorkspaceStage(MockStage):
        pass

    SnapshotStage.__name__ = "SnapshotResolverStage"
    WorkspaceStage.__name__ = "WorkspaceAcquisitionStage"

    def fake_update(project_id, noteable_type, noteable_iid, note_id, body, project=None):
        updated.append(body)
        return {"id": note_id}

    monkeypatch.setattr("src.pipelines.base.update_gitlab_note", fake_update)
    monkeypatch.setattr("src.pipelines.base.time.monotonic", lambda: 10.5)

    context = PipelineContext(
        webhook_payload={
            "object_kind": "note",
            "project": {"id": 123},
            "object_attributes": {
                "noteable_type": "Issue",
                "noteable_iid": 7,
            },
        },
        command="oc_ask",
        gitlab_note_id=99,
        metadata={
            "noteable_type": "Issue",
            "progress_note_last_publish_at": 10.0,
        },
    )
    pipeline = Pipeline(name="test", stages=[SnapshotStage(), WorkspaceStage()])

    result = pipeline.execute(context)

    assert result.success
    assert updated == []


def test_pipeline_progress_note_step_count(monkeypatch):
    updated = []
    timestamps = iter([10.0, 11.1])

    class SnapshotStage(MockStage):
        pass

    class WorkspaceStage(MockStage):
        pass

    SnapshotStage.__name__ = "SnapshotResolverStage"
    WorkspaceStage.__name__ = "WorkspaceAcquisitionStage"

    def fake_update(project_id, noteable_type, noteable_iid, note_id, body, project=None):
        updated.append(body)
        return {"id": note_id}

    monkeypatch.setattr("src.pipelines.base.update_gitlab_note", fake_update)
    monkeypatch.setattr("src.pipelines.base.time.monotonic", lambda: next(timestamps))

    context = PipelineContext(
        webhook_payload={
            "object_kind": "note",
            "project": {"id": 123},
            "object_attributes": {
                "noteable_type": "Issue",
                "noteable_iid": 7,
            },
        },
        command="oc_ask",
        gitlab_note_id=99,
        metadata={"noteable_type": "Issue"},
    )
    pipeline = Pipeline(name="test", stages=[SnapshotStage(), WorkspaceStage()])

    result = pipeline.execute(context)

    assert result.success
    assert updated == [
        "🤖 **OpenCode progress (1/2)**\n\nResolving target revision.",
        "🤖 **OpenCode progress (2/2)**\n\nPreparing workspace.",
    ]


def test_pipeline_should_stop():
    class StopStage(Stage):
        def _execute(self, context: PipelineContext) -> StageResult:
            return StageResult(context=context, should_stop=True)

    context = PipelineContext(webhook_payload={})
    stages = [MockStage(), StopStage(), MockStage()]
    pipeline = Pipeline(name="test", stages=stages)

    result = pipeline.execute(context)

    assert result.success
    assert context.metadata.get("final_executed") is None


def test_pipeline_cleans_up_workspace_when_requested(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "marker.txt").write_text("x", encoding="utf-8")

    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(workspace),
        workspace_cleanup_required=True,
    )
    pipeline = Pipeline(name="test", stages=[MockStage()])

    result = pipeline.execute(context)

    assert result.success
    assert not Path(context.local_context_path).exists()


def test_pipeline_keeps_workspace_when_cleanup_not_requested(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    context = PipelineContext(
        webhook_payload={},
        local_context_path=str(workspace),
        workspace_cleanup_required=False,
    )
    pipeline = Pipeline(name="test", stages=[MockStage()])

    result = pipeline.execute(context)

    assert result.success
    assert Path(context.local_context_path).exists()
