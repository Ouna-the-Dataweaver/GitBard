from abc import ABC, abstractmethod
from typing import Any

from ..base import Pipeline, PreparationConfig, WorkspaceConfig
from ..builder import PipelineBuildConfig, STAGE_BLOCKS, build_pipeline, resolve_stage_ids


class Command(ABC):
    """Base class for all commands"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (e.g., 'oc_review')"""
        pass

    @property
    @abstractmethod
    def trigger_pattern(self) -> str:
        """Pattern to detect command in webhook (e.g., '/oc_review')"""
        pass

    @property
    def scope(self) -> str:
        return "merge_request"

    @property
    def preset(self) -> str:
        return self.name.removeprefix("oc_")

    @property
    def agent_name(self) -> str:
        return "Build"

    @property
    def opencode_agent(self) -> str | None:
        if self.agent_name == "Build":
            return None
        return self.agent_name

    @property
    def description(self) -> str:
        return ""

    @property
    def timeout_seconds(self) -> int:
        return 1800

    @property
    def enable_repo_hook(self) -> bool:
        return False

    @property
    def enable_opencode_preparation(self) -> bool:
        return False

    @property
    def allow_dependency_install(self) -> bool:
        return False

    @property
    def workspace_config(self) -> WorkspaceConfig:
        return WorkspaceConfig(mode="fresh_clone", cleanup_required=True)

    @property
    def preparation_config(self) -> PreparationConfig:
        routes: list[str] = []
        if self.enable_repo_hook:
            routes.append("repo_hook")
        if self.enable_opencode_preparation:
            routes.append("opencode")
        return PreparationConfig(routes=tuple(routes))

    @property
    def stage_ids(self) -> tuple[str, ...] | None:
        return None

    def admin_document_id(self) -> str:
        return self.name.replace("_", "-")

    def to_admin_document(self, *, now_iso: str) -> dict[str, Any]:
        stage_ids = list(
            resolve_stage_ids(
                PipelineBuildConfig(
                    name=self.name,
                    preset=self.preset,
                    stage_ids=self.stage_ids,
                )
            )
        )
        step_settings: dict[str, dict[str, Any]] = {}
        context_handling: dict[str, dict[str, Any]] = {}
        for stage_id in stage_ids:
            block = STAGE_BLOCKS.get(stage_id)
            if not block:
                continue
            values = {
                str(field["key"]): field["default"]
                for field in block.config_schema
                if "default" in field
            }
            if values:
                step_settings[stage_id] = values
            default_context = block.context_schema.get("default", {})
            if isinstance(default_context, dict):
                context_handling[stage_id] = dict(default_context)
        if "OpencodeIntegrationStage" in stage_ids:
            step_settings["OpencodeIntegrationStage"] = {
                **step_settings.get("OpencodeIntegrationStage", {}),
                "agentName": self.agent_name,
                "modelName": "minimax/MiniMax-M2.1",
            }
        return {
            "id": self.admin_document_id(),
            "name": f"{self.name.replace('_', ' ').title()} Pipeline",
            "enabled": True,
            "description": self.description,
            "preset": self.preset,
            "trigger": {
                "type": "slash_command",
                "scope": self.scope,
                "commandText": self.trigger_pattern,
                "mentionTarget": "@nid-bugbard",
            },
            "filters": {
                "projectAllowlist": [],
                "branchPatterns": [],
                "labelFilters": [],
                "authorAllowlist": [],
                "authorDenylist": [],
            },
            "execution": {
                "mode": self.preset,
                "agentName": self.agent_name,
                "modelName": "minimax/MiniMax-M2.1",
                "questionTemplate": "{{note_body_without_trigger}}",
                "timeoutSeconds": self.timeout_seconds,
                "maxConcurrentRuns": 1,
            },
            "workspace": {
                "mode": "fresh_clone",
                "cleanupAfterRun": True,
                "checkoutStrategy": "source_branch",
            },
            "preparation": {
                "enableRepoHook": self.enable_repo_hook,
                "enableOpencodePreparation": self.enable_opencode_preparation,
                "allowDependencyInstall": self.allow_dependency_install,
            },
            "output": {
                "postMode": "new_note",
                "includeArtifactsInNote": True,
                "keepEventsJsonl": True,
                "keepRenderedReplyMarkdown": True,
            },
            "stages": stage_ids,
            "stepSettings": step_settings,
            "contextHandling": context_handling,
            "updatedAt": now_iso,
        }

    def get_pipeline(self) -> Pipeline:
        """Return the pipeline for this command"""
        return build_pipeline(
            PipelineBuildConfig(
                name=self.name,
                preset=self.preset,
                stage_ids=self.stage_ids,
                workspace_config=self.workspace_config,
                preparation_config=self.preparation_config,
                agent=self.opencode_agent,
            )
        )
