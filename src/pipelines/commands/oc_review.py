from ..base import Pipeline, WorkspaceConfig
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import WorkspaceAcquisitionStage
from ..stages.issue_context_fetcher import IssueContextFetcherStage
from ..stages.opencode_integration import OpencodeIntegrationStage
from ..stages.note_updater import NoteUpdaterStage


class ReviewCommand(Command):
    @property
    def name(self) -> str:
        return "oc_review"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_review"

    @property
    def description(self) -> str:
        return "Runs the review agent when a merge request note requests review."

    def get_pipeline(self) -> Pipeline:
        workspace_config = WorkspaceConfig(mode="fresh_clone", cleanup_required=True)
        return Pipeline(
            name="oc_review",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                WorkspaceAcquisitionStage(workspace_config=workspace_config),
                IssueContextFetcherStage(),
                OpencodeIntegrationStage(agent="gitlab-review"),
                NoteUpdaterStage(),
            ],
        )
