from ..base import Pipeline
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import ContextBuilderStage
from ..stages.agent_executor import AgentExecutorStage
from ..stages.note_updater import NoteUpdaterStage


class ReviewCommand(Command):
    @property
    def name(self) -> str:
        return "oc_review"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_review"

    def get_pipeline(self) -> Pipeline:
        return Pipeline(
            name="oc_review",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                ContextBuilderStage(),
                AgentExecutorStage(agent_type="review"),
                NoteUpdaterStage(),
            ],
        )
