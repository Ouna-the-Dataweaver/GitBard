from src.pipelines.base import PipelineContext, PreparationConfig
from src.pipelines.stages.workspace_preparation import WorkspacePreparationStage


def test_workspace_preparation_stage_is_noop_when_no_routes():
    context = PipelineContext(webhook_payload={})
    stage = WorkspacePreparationStage()

    result = stage.execute(context)

    assert not result.should_stop


def test_workspace_preparation_stage_runs_routes_in_order(monkeypatch):
    context = PipelineContext(webhook_payload={})
    stage = WorkspacePreparationStage(
        preparation_config=PreparationConfig(routes=("repo_hook", "opencode"))
    )
    calls: list[str] = []

    def fake_repo_execute(self, context_arg):
        calls.append("repo_hook")
        return type("Result", (), {"context": context_arg, "should_stop": False})()

    def fake_opencode_execute(self, context_arg):
        calls.append("opencode")
        return type("Result", (), {"context": context_arg, "should_stop": False})()

    monkeypatch.setattr(
        "src.pipelines.stages.repo_hook_preparation.RepoHookPreparationStage.execute",
        fake_repo_execute,
    )
    monkeypatch.setattr(
        "src.pipelines.stages.opencode_integration.OpencodePreparationStage.execute",
        fake_opencode_execute,
    )

    result = stage.execute(context)

    assert not result.should_stop
    assert calls == ["repo_hook", "opencode"]


def test_workspace_preparation_stage_rejects_unknown_route():
    context = PipelineContext(webhook_payload={})
    stage = WorkspacePreparationStage(
        preparation_config=PreparationConfig(routes=("unknown",))
    )

    result = stage.execute(context)

    assert result.should_stop
    assert "Unsupported workspace preparation route: unknown" in str(result.error)
