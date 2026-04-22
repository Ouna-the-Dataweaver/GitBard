from ..base import Pipeline, WorkspaceConfig
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import WorkspaceAcquisitionStage
from ..stages.issue_context_fetcher import IssueContextFetcherStage
from ..stages.opencode_integration import OpencodeIntegrationStage
from ..stages.note_updater import NoteUpdaterStage


class TestCommand(Command):
    @property
    def name(self) -> str:
        return "oc_test"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_test"

    @property
    def description(self) -> str:
        return "Uses the same real opencode CLI path for ad hoc testing."

    def get_pipeline(self) -> Pipeline:
        workspace_config = WorkspaceConfig(mode="fresh_clone", cleanup_required=True)
        return Pipeline(
            name="oc_test",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                WorkspaceAcquisitionStage(workspace_config=workspace_config),
                IssueContextFetcherStage(),
                OpencodeIntegrationStage(),
                NoteUpdaterStage(),
            ],
        )
