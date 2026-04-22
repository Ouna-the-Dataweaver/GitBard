from ..base import Pipeline, WorkspaceConfig
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import WorkspaceAcquisitionStage
from ..stages.issue_context_fetcher import IssueContextFetcherStage
from ..stages.opencode_integration import OpencodeIntegrationStage
from ..stages.note_updater import NoteUpdaterStage


class AskCommand(Command):
    @property
    def name(self) -> str:
        return "oc_ask"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_ask"

    @property
    def description(self) -> str:
        return "Runs the opencode CLI and posts its response back to the thread."

    def get_pipeline(self) -> Pipeline:
        workspace_config = WorkspaceConfig(mode="fresh_clone", cleanup_required=True)
        return Pipeline(
            name="oc_ask",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                WorkspaceAcquisitionStage(workspace_config=workspace_config),
                IssueContextFetcherStage(),
                OpencodeIntegrationStage(),
                NoteUpdaterStage(),
            ],
        )
