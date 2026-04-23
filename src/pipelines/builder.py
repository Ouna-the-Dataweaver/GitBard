from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .base import Pipeline, PreparationConfig, Stage, WorkspaceConfig


@dataclass(frozen=True)
class StageBlock:
    """Metadata and factory for a reusable pipeline stage."""

    id: str
    name: str
    description: str
    factory: Callable[["PipelineBuildConfig"], Stage]


@dataclass(frozen=True)
class PipelineBuildConfig:
    """Declarative config used to build a runtime pipeline."""

    name: str
    preset: str
    stage_ids: tuple[str, ...] | None = None
    workspace_config: WorkspaceConfig = field(default_factory=WorkspaceConfig)
    preparation_config: PreparationConfig = field(default_factory=PreparationConfig)
    model: str | None = None
    agent: str | None = None


def _workspace_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.context_builder import WorkspaceAcquisitionStage

    return WorkspaceAcquisitionStage(workspace_config=config.workspace_config)


def _preparation_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.workspace_preparation import WorkspacePreparationStage

    return WorkspacePreparationStage(preparation_config=config.preparation_config)


def _opencode_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.opencode_integration import OpencodeIntegrationStage

    return OpencodeIntegrationStage(model=config.model, agent=config.agent)


def _hook_resolver_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.hook_resolver import HookResolverStage

    return HookResolverStage()


def _snapshot_resolver_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.snapshot_resolver import SnapshotResolverStage

    return SnapshotResolverStage()


def _issue_context_fetcher_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.issue_context_fetcher import IssueContextFetcherStage

    return IssueContextFetcherStage()


def _note_updater_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.note_updater import NoteUpdaterStage

    return NoteUpdaterStage()


STAGE_BLOCKS: dict[str, StageBlock] = {
    "HookResolverStage": StageBlock(
        id="HookResolverStage",
        name="Hook Resolver",
        description="Detect trigger commands and post initial status",
        factory=_hook_resolver_stage,
    ),
    "SnapshotResolverStage": StageBlock(
        id="SnapshotResolverStage",
        name="Snapshot Resolver",
        description="Resolve code snapshot SHA and branch ref",
        factory=_snapshot_resolver_stage,
    ),
    "WorkspaceAcquisitionStage": StageBlock(
        id="WorkspaceAcquisitionStage",
        name="Workspace Acquisition",
        description="Clone repository into local workspace",
        factory=_workspace_stage,
    ),
    "IssueContextFetcherStage": StageBlock(
        id="IssueContextFetcherStage",
        name="Context Fetcher",
        description="Fetch GitLab issue/MR discussion thread",
        factory=_issue_context_fetcher_stage,
    ),
    "WorkspacePreparationStage": StageBlock(
        id="WorkspacePreparationStage",
        name="Workspace Preparation",
        description="Run workspace preparation routes",
        factory=_preparation_stage,
    ),
    "OpencodeIntegrationStage": StageBlock(
        id="OpencodeIntegrationStage",
        name="OpenCode Integration",
        description="Execute OpenCode AI agent on workspace",
        factory=_opencode_stage,
    ),
    "NoteUpdaterStage": StageBlock(
        id="NoteUpdaterStage",
        name="Note Updater",
        description="Post pipeline results as GitLab note",
        factory=_note_updater_stage,
    ),
}

COMMON_OPENCODE_STAGE_IDS = (
    "HookResolverStage",
    "SnapshotResolverStage",
    "WorkspaceAcquisitionStage",
    "IssueContextFetcherStage",
    "OpencodeIntegrationStage",
    "NoteUpdaterStage",
)

PIPELINE_PRESET_STAGE_IDS: dict[str, tuple[str, ...]] = {
    "review": COMMON_OPENCODE_STAGE_IDS,
    "ask": COMMON_OPENCODE_STAGE_IDS,
    "test": COMMON_OPENCODE_STAGE_IDS,
    "deep_test": (
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "WorkspacePreparationStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    ),
}

PRESET_ALIASES = {
    "deeptest": "deep_test",
}


def normalize_preset(preset: str) -> str:
    normalized = preset.strip()
    return PRESET_ALIASES.get(normalized, normalized)


def available_stage_ids() -> tuple[str, ...]:
    return tuple(STAGE_BLOCKS)


def available_stage_metadata() -> list[dict[str, str]]:
    return [
        {
            "id": block.id,
            "name": block.name,
            "description": block.description,
        }
        for block in STAGE_BLOCKS.values()
    ]


def supported_presets() -> tuple[str, ...]:
    return tuple(PIPELINE_PRESET_STAGE_IDS)


def resolve_stage_ids(config: PipelineBuildConfig) -> tuple[str, ...]:
    if config.stage_ids is not None:
        return config.stage_ids

    preset = normalize_preset(config.preset)
    try:
        return PIPELINE_PRESET_STAGE_IDS[preset]
    except KeyError as exc:
        raise ValueError(f"Unsupported pipeline preset: {config.preset}") from exc


def build_pipeline(config: PipelineBuildConfig) -> Pipeline:
    stage_ids = resolve_stage_ids(config)
    stages: list[Stage] = []

    for stage_id in stage_ids:
        try:
            block = STAGE_BLOCKS[stage_id]
        except KeyError as exc:
            raise ValueError(f"Unknown pipeline stage: {stage_id}") from exc
        stages.append(block.factory(config))

    return Pipeline(name=config.name, stages=stages)
