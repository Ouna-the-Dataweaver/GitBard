from ..base import Pipeline
from .base import Command
from ..stages.hook_resolver import HookResolverStage
from ..stages.snapshot_resolver import SnapshotResolverStage
from ..stages.context_builder import ContextBuilderStage
from ..stages.agent_executor import AgentExecutorStage
from ..stages.note_updater import NoteUpdaterStage


class AskCommand(Command):
    @property
    def name(self) -> str:
        return "oc_ask"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_ask"

    def get_pipeline(self) -> Pipeline:
        return Pipeline(
            name="oc_ask",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                ContextBuilderStage(),
                AgentExecutorStage(agent_type="general"),
                NoteUpdaterStage(),
            ],
        )
