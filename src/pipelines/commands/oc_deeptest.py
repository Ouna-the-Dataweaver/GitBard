from ..base import Pipeline, PreparationConfig, WorkspaceConfig
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import WorkspaceAcquisitionStage
from ..stages.issue_context_fetcher import IssueContextFetcherStage
from ..stages.opencode_integration import OpencodeIntegrationStage
from ..stages.note_updater import NoteUpdaterStage
from ..stages.workspace_preparation import WorkspacePreparationStage


class DeepTestCommand(Command):
    @property
    def name(self) -> str:
        return "oc_deeptest"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_deeptest"

    def get_pipeline(self) -> Pipeline:
        workspace_config = WorkspaceConfig(mode="fresh_clone", cleanup_required=True)
        preparation_config = PreparationConfig(routes=("repo_hook", "opencode"))
        return Pipeline(
            name="oc_deeptest",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                WorkspaceAcquisitionStage(workspace_config=workspace_config),
                IssueContextFetcherStage(),
                WorkspacePreparationStage(preparation_config=preparation_config),
                OpencodeIntegrationStage(),
                NoteUpdaterStage(),
            ],
        )
