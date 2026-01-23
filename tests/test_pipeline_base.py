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
