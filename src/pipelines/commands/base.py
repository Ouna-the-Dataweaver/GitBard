from abc import ABC, abstractmethod
from typing import Any

from ..base import Pipeline


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
        return "gitlab-review"

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

    def admin_document_id(self) -> str:
        return self.name.replace("_", "-")

    def to_admin_document(self, *, now_iso: str) -> dict[str, Any]:
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
            "updatedAt": now_iso,
        }

    @abstractmethod
    def get_pipeline(self) -> Pipeline:
        """Return the pipeline for this command"""
        pass
