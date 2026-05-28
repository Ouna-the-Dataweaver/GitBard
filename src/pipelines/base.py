from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging
import os
import shutil

try:
    from src.gitlab_api import extract_noteable_iid, post_gitlab_note
except ModuleNotFoundError:
    from gitlab_api import extract_noteable_iid, post_gitlab_note

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkspaceConfig:
    """Workspace acquisition policy for a pipeline run."""

    mode: str = "fresh_clone"
    cleanup_required: bool = True


@dataclass(frozen=True)
class PreparationConfig:
    """Optional repository preparation steps."""

    routes: tuple[str, ...] = ()


@dataclass
class PipelineContext:
    """Shared context passed through all pipeline stages"""

    webhook_payload: Dict[str, Any]
    command: Optional[str] = None
    project_info: Optional[Dict[str, Any]] = None
    code_snapshot: Optional[Dict[str, Any]] = None
    local_context_path: Optional[str] = None
    workspace_cleanup_required: bool = False
    agent_result: Optional["AgentResult"] = None
    gitlab_note_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Structured result from agent execution"""

    content: str
    format: str = "markdown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """Result returned by each stage"""

    context: PipelineContext
    should_stop: bool = False
    error: Optional[Exception] = None
    success: bool = True


class Stage:
    """Base class for all pipeline stages"""

    def execute(self, context: PipelineContext) -> StageResult:
        """Execute stage - synchronous"""
        try:
            logger.info(f"Executing stage: {self.__class__.__name__}")
            result = self._execute(context)
            logger.info(f"Completed stage: {self.__class__.__name__}")
            return result
        except Exception as e:
            logger.error(f"Stage {self.__class__.__name__} failed: {e}", exc_info=True)
            return StageResult(
                context=context, should_stop=True, error=e, success=False
            )

    def _execute(self, context: PipelineContext) -> StageResult:
        """Actual implementation of stage logic"""
        raise NotImplementedError


class Pipeline:
    """Pipeline executes stages sequentially"""

    def __init__(self, name: str, stages: List[Stage]):
        self.name = name
        self.stages = stages

    def execute(self, context: PipelineContext) -> StageResult:
        """Execute all stages until completion or stop"""
        logger.info(f"Starting pipeline: {self.name}")

        try:
            for index, stage in enumerate(self.stages):
                self._publish_progress(context, stage)
                result = stage.execute(context)
                context = result.context

                if result.should_stop:
                    if result.error:
                        context.metadata["pipeline_error"] = str(result.error)
                        logger.error(
                            f"Pipeline {self.name} stopped with error: {result.error}"
                        )
                        self._publish_error(context, self.stages[index + 1 :])
                    else:
                        logger.info(f"Pipeline {self.name} stopped early")
                    return result

            logger.info(f"Pipeline {self.name} completed successfully")
            return StageResult(context=context, should_stop=False, success=True)
        finally:
            for attr_name in ["local_context_path"]:
                path = getattr(context, attr_name, None)
                if path and context.workspace_cleanup_required:
                    shutil.rmtree(path, ignore_errors=True)

    def _publish_error(
        self, context: PipelineContext, remaining_stages: List[Stage]
    ) -> None:
        for stage in remaining_stages:
            if stage.__class__.__name__ != "NoteUpdaterStage":
                continue

            result = stage.execute(context)
            if not result.success:
                logger.error(
                    "Pipeline %s failed to publish error: %s", self.name, result.error
                )
            return

    def _publish_progress(self, context: PipelineContext, stage: Stage) -> None:
        if os.getenv("GITBARD_PROGRESS_NOTES", "1").lower() in {"0", "false", "no"}:
            return

        stage_name = stage.__class__.__name__
        if stage_name in {"HookResolverStage", "NoteUpdaterStage"}:
            return

        payload = context.webhook_payload
        project_id = payload.get("project", {}).get("id")
        noteable_type = context.metadata.get("noteable_type")
        noteable_iid = extract_noteable_iid(payload)
        if not project_id or not noteable_type or not noteable_iid:
            return

        message = self._progress_message(stage_name, stage)
        if not message:
            return

        try:
            post_gitlab_note(
                project_id,
                noteable_type,
                noteable_iid,
                message,
                project=payload.get("project"),
            )
        except Exception:
            logger.exception("Pipeline %s failed to publish progress note", self.name)

    def _progress_message(self, stage_name: str, stage: Stage) -> str:
        messages = {
            "SnapshotResolverStage": "🤖 OpenCode progress: resolving target revision.",
            "WorkspaceAcquisitionStage": "🤖 OpenCode progress: preparing workspace.",
            "IssueContextFetcherStage": "🤖 OpenCode progress: collecting GitLab context.",
            "WorkspacePreparationStage": "🤖 OpenCode progress: running preparation.",
        }
        if stage_name == "OpencodeIntegrationStage":
            model = getattr(stage, "model", "unknown")
            agent = getattr(stage, "agent", "unknown")
            return (
                "🤖 OpenCode progress: running model "
                f"`{model}` with agent `{agent}`."
            )
        return messages.get(stage_name, "")
