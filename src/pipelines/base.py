from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import logging
import shutil

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Shared context passed through all pipeline stages"""

    webhook_payload: Dict[str, Any]
    command: Optional[str] = None
    project_info: Optional[Dict[str, Any]] = None
    code_snapshot: Optional[Dict[str, Any]] = None
    local_context_path: Optional[str] = None
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
            for stage in self.stages:
                result = stage.execute(context)
                context = result.context

                if result.should_stop:
                    if result.error:
                        context.metadata["pipeline_error"] = str(result.error)
                        logger.error(
                            f"Pipeline {self.name} stopped with error: {result.error}"
                        )
                    else:
                        logger.info(f"Pipeline {self.name} stopped early")
                    return result

            logger.info(f"Pipeline {self.name} completed successfully")
            return StageResult(context=context, should_stop=False, success=True)
        finally:
            for attr_name in ["local_context_path"]:
                path = getattr(context, attr_name, None)
                if path:
                    shutil.rmtree(path, ignore_errors=True)
