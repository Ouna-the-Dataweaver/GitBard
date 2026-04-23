import pytest

from src.pipelines.base import PreparationConfig, WorkspaceConfig
from src.pipelines.builder import (
    PipelineBuildConfig,
    available_stage_ids,
    build_pipeline,
    normalize_preset,
    resolve_stage_ids,
    supported_presets,
)
from src.pipelines.stages.context_builder import WorkspaceAcquisitionStage
from src.pipelines.stages.opencode_integration import OpencodeIntegrationStage
from src.pipelines.stages.workspace_preparation import WorkspacePreparationStage


def test_builder_exposes_current_building_blocks():
    assert available_stage_ids() == (
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "WorkspacePreparationStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    )
    assert supported_presets() == ("review", "ask", "test", "deep_test")


def test_builder_normalizes_legacy_preset_alias():
    assert normalize_preset("deeptest") == "deep_test"


def test_builder_resolves_preset_stage_ids():
    stage_ids = resolve_stage_ids(PipelineBuildConfig(name="review", preset="review"))

    assert stage_ids == (
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    )


def test_builder_builds_configured_stage_instances():
    pipeline = build_pipeline(
        PipelineBuildConfig(
            name="review",
            preset="review",
            workspace_config=WorkspaceConfig(mode="fresh_clone", cleanup_required=False),
            agent="gitlab-review",
        )
    )

    workspace_stage = pipeline.stages[2]
    opencode_stage = pipeline.stages[4]

    assert pipeline.name == "review"
    assert isinstance(workspace_stage, WorkspaceAcquisitionStage)
    assert workspace_stage.workspace_config.cleanup_required is False
    assert isinstance(opencode_stage, OpencodeIntegrationStage)
    assert opencode_stage.agent == "gitlab-review"


def test_builder_builds_preparation_stage_from_deep_test_preset():
    pipeline = build_pipeline(
        PipelineBuildConfig(
            name="deep",
            preset="deep_test",
            preparation_config=PreparationConfig(routes=("repo_hook", "opencode")),
        )
    )

    prep_stage = pipeline.stages[4]
    assert isinstance(prep_stage, WorkspacePreparationStage)
    assert prep_stage.preparation_config.routes == ("repo_hook", "opencode")


def test_builder_rejects_unknown_stage_id():
    with pytest.raises(ValueError, match="Unknown pipeline stage"):
        build_pipeline(
            PipelineBuildConfig(
                name="bad",
                preset="review",
                stage_ids=("HookResolverStage", "FakeStage"),
            )
        )
