from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .base import Pipeline, PreparationConfig, Stage, WorkspaceConfig


@dataclass(frozen=True)
class StageBlock:
    """Metadata and factory for a reusable pipeline stage."""

    id: str
    name: str
    description: str
    factory: Callable[["PipelineBuildConfig"], Stage]
    provider: str = "core"
    category: str = "core"
    required_after: tuple[str, ...] = ()
    required_before: tuple[str, ...] = ()
    config_schema: tuple[dict[str, Any], ...] = ()
    context_schema: dict[str, Any] = field(default_factory=dict)


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
    step_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    context_policies: dict[str, dict[str, Any]] = field(default_factory=dict)


def _step_config(config: PipelineBuildConfig, stage_id: str) -> dict[str, Any]:
    return config.step_configs.get(stage_id, {})


def _workspace_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.context_builder import WorkspaceAcquisitionStage

    step = _step_config(config, "WorkspaceAcquisitionStage")
    workspace_config = WorkspaceConfig(
        mode=str(step.get("mode") or config.workspace_config.mode),
        cleanup_required=bool(
            step.get("cleanupAfterRun", config.workspace_config.cleanup_required)
        ),
    )
    return WorkspaceAcquisitionStage(workspace_config=workspace_config)


def _preparation_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.workspace_preparation import WorkspacePreparationStage

    step = _step_config(config, "WorkspacePreparationStage")
    routes = step.get("routes")
    if isinstance(routes, list):
        preparation_config = PreparationConfig(routes=tuple(str(route) for route in routes))
    else:
        preparation_config = config.preparation_config
    return WorkspacePreparationStage(preparation_config=preparation_config)


def _opencode_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.opencode_integration import OpencodeIntegrationStage

    step = _step_config(config, "OpencodeIntegrationStage")
    return OpencodeIntegrationStage(
        model=step.get("modelName") or config.model,
        agent=step.get("agentName") or config.agent,
    )


def _hook_resolver_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.hook_resolver import HookResolverStage

    return HookResolverStage()


def _snapshot_resolver_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.snapshot_resolver import SnapshotResolverStage

    return SnapshotResolverStage()


def _issue_context_fetcher_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.issue_context_fetcher import IssueContextFetcherStage

    step = _step_config(config, "IssueContextFetcherStage")
    context_policy = config.context_policies.get("IssueContextFetcherStage", {})
    return IssueContextFetcherStage(
        filename=str(
            context_policy.get("filename")
            or step.get("filename")
            or "gitlab_thread_context.md"
        ),
        write_to_workspace=bool(context_policy.get("writeToWorkspace", True)),
        pass_to_next=bool(context_policy.get("passToNext", True)),
    )


def _note_updater_stage(config: PipelineBuildConfig) -> Stage:
    from .stages.note_updater import NoteUpdaterStage

    return NoteUpdaterStage()


STAGE_BLOCKS: dict[str, StageBlock] = {
    "HookResolverStage": StageBlock(
        id="HookResolverStage",
        name="Hook Resolver",
        description="Detect trigger commands and post initial status",
        factory=_hook_resolver_stage,
        provider="gitlab",
        category="trigger",
        required_before=("SnapshotResolverStage",),
        context_schema={
            "produces": ["command", "note_body", "noteable_type", "gitlab_note_id"],
            "default": {"passToNext": True, "writeToWorkspace": False},
        },
    ),
    "SnapshotResolverStage": StageBlock(
        id="SnapshotResolverStage",
        name="Snapshot Resolver",
        description="Resolve code snapshot SHA and branch ref",
        factory=_snapshot_resolver_stage,
        provider="gitlab",
        category="snapshot",
        required_after=("HookResolverStage",),
        required_before=("WorkspaceAcquisitionStage",),
        context_schema={
            "produces": ["code_snapshot"],
            "default": {"passToNext": True, "writeToWorkspace": False},
        },
    ),
    "WorkspaceAcquisitionStage": StageBlock(
        id="WorkspaceAcquisitionStage",
        name="Workspace Acquisition",
        description="Clone repository into local workspace",
        factory=_workspace_stage,
        provider="git",
        category="workspace",
        required_after=("SnapshotResolverStage",),
        config_schema=(
            {
                "key": "mode",
                "label": "Workspace Mode",
                "type": "select",
                "options": ["fresh_clone"],
                "default": "fresh_clone",
            },
            {
                "key": "cleanupAfterRun",
                "label": "Cleanup After Run",
                "type": "boolean",
                "default": True,
            },
        ),
        context_schema={
            "produces": ["local_context_path"],
            "default": {"passToNext": True, "writeToWorkspace": False},
        },
    ),
    "IssueContextFetcherStage": StageBlock(
        id="IssueContextFetcherStage",
        name="Context Fetcher",
        description="Fetch GitLab issue/MR discussion thread",
        factory=_issue_context_fetcher_stage,
        provider="gitlab",
        category="context",
        required_after=("WorkspaceAcquisitionStage",),
        config_schema=(
            {
                "key": "filename",
                "label": "Context Filename",
                "type": "text",
                "default": "gitlab_thread_context.md",
            },
        ),
        context_schema={
            "produces": ["thread_context_path"],
            "default": {
                "passToNext": True,
                "writeToWorkspace": True,
                "filename": "gitlab_thread_context.md",
            },
        },
    ),
    "WorkspacePreparationStage": StageBlock(
        id="WorkspacePreparationStage",
        name="Workspace Preparation",
        description="Run workspace preparation routes",
        factory=_preparation_stage,
        provider="core",
        category="preparation",
        required_after=("WorkspaceAcquisitionStage",),
        required_before=("OpencodeIntegrationStage",),
        config_schema=(
            {
                "key": "routes",
                "label": "Preparation Routes",
                "type": "multi_select",
                "options": ["repo_hook", "opencode"],
                "default": [],
            },
        ),
        context_schema={
            "produces": ["prep_report_path", "prep_events_path"],
            "default": {
                "passToNext": True,
                "writeToWorkspace": True,
                "filename": "opencode_prep_report.md",
            },
        },
    ),
    "OpencodeIntegrationStage": StageBlock(
        id="OpencodeIntegrationStage",
        name="OpenCode Integration",
        description="Execute OpenCode AI agent on workspace",
        factory=_opencode_stage,
        provider="opencode",
        category="agent",
        required_after=("WorkspaceAcquisitionStage",),
        required_before=("NoteUpdaterStage",),
        config_schema=(
            {
                "key": "agentName",
                "label": "Agent",
                "type": "agent",
                "default": "Build",
            },
            {
                "key": "modelName",
                "label": "Model",
                "type": "model",
                "default": "minimax/MiniMax-M2.1",
            },
        ),
        context_schema={
            "consumes": ["thread_context_path", "prep_report_path"],
            "produces": ["agent_result", "opencode_events_path", "opencode_reply_path"],
            "default": {
                "passToNext": True,
                "writeToWorkspace": True,
                "filename": "opencode_reply.md",
            },
        },
    ),
    "NoteUpdaterStage": StageBlock(
        id="NoteUpdaterStage",
        name="Note Updater",
        description="Post pipeline results as GitLab note",
        factory=_note_updater_stage,
        provider="gitlab",
        category="output",
        required_after=("OpencodeIntegrationStage",),
        context_schema={
            "consumes": ["agent_result"],
            "default": {"passToNext": False, "writeToWorkspace": False},
        },
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


def available_step_metadata() -> list[dict[str, Any]]:
    return [
        {
            "id": block.id,
            "stageId": block.id,
            "name": block.name,
            "description": block.description,
            "provider": block.provider,
            "category": block.category,
            "requiredAfter": list(block.required_after),
            "requiredBefore": list(block.required_before),
            "configSchema": list(block.config_schema),
            "contextSchema": block.context_schema,
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
