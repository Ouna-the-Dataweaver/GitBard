from ..base import Pipeline
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import ContextBuilderStage
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

    def get_pipeline(self) -> Pipeline:
        return Pipeline(
            name="oc_test",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                ContextBuilderStage(),
                IssueContextFetcherStage(),
                OpencodeIntegrationStage(),
                NoteUpdaterStage(),
            ],
        )
