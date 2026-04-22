from ..base import PipelineContext, PreparationConfig, Stage, StageResult
from .opencode_integration import OpencodePreparationStage
from .repo_hook_preparation import RepoHookPreparationStage


class WorkspacePreparationStage(Stage):
    """Run the configured workspace preparation routes in order."""

    def __init__(self, preparation_config: PreparationConfig | None = None):
        self.preparation_config = preparation_config or PreparationConfig()

    def _execute(self, context: PipelineContext) -> StageResult:
        for stage in self._build_route_stages():
            result = stage.execute(context)
            context = result.context
            if result.should_stop:
                return result

        return StageResult(context=context, should_stop=False)

    def _build_route_stages(self) -> list[Stage]:
        stages: list[Stage] = []

        for route in self.preparation_config.routes:
            if route == "repo_hook":
                stages.append(RepoHookPreparationStage(enabled=True))
            elif route == "opencode":
                stages.append(OpencodePreparationStage(enabled=True))
            else:
                raise ValueError(f"Unsupported workspace preparation route: {route}")

        return stages
