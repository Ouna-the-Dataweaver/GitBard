from ..base import Stage, StageResult, PipelineContext, AgentResult
import logging

logger = logging.getLogger(__name__)


class AgentExecutorStage(Stage):
    """Stage D: Run OpenCode agent with appropriate prompt"""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type

    def _execute(self, context: PipelineContext) -> StageResult:
        if self.agent_type == "review":
            prompt = self._build_review_prompt(context)
        elif self.agent_type == "general":
            prompt = self._build_general_prompt(context)
        else:
            prompt = self._build_generic_prompt(context)

        result = AgentResult(
            content=f"Agent result for {self.agent_type}: {prompt[:100]}...",
            format="markdown",
            metadata={"agent_type": self.agent_type},
        )
        context.agent_result = result

        logger.info(f"Agent {self.agent_type} executed")

        return StageResult(context=context, should_stop=False)

    def _build_review_prompt(self, context: PipelineContext) -> str:
        return f"Review the code in {context.local_context_path}"

    def _build_general_prompt(self, context: PipelineContext) -> str:
        return f"Answer questions about the code in {context.local_context_path}"

    def _build_generic_prompt(self, context: PipelineContext) -> str:
        return "Analyze the code"
