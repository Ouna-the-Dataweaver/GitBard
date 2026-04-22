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
