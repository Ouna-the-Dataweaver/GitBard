from ..base import Stage, StageResult, PipelineContext
import logging

logger = logging.getLogger(__name__)


class NoteUpdaterStage(Stage):
    """Update the initial note with agent results or error notification"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        project_id = payload.get("project", {}).get("id")
        noteable_type = context.metadata.get("noteable_type")
        noteable_iid = self._get_noteable_iid(payload)

        if context.metadata.get("pipeline_error"):
            from src.app_old import post_gitlab_note

            error_msg = context.metadata.get("pipeline_error", "Unknown error")
            post_gitlab_note(
                project_id,
                noteable_type,
                noteable_iid,
                f"❌ **OpenCode Error**\n\nPipeline failed: {error_msg}",
            )
            logger.info("Updated note with error notification")
            return StageResult(context=context, should_stop=False)

        from src.app_old import post_gitlab_note

        result = context.agent_result
        content = result.content if result else "No results generated"

        post_gitlab_note(
            project_id,
            noteable_type,
            noteable_iid,
            f"🤖 **OpenCode Results**\n\n{content}",
        )

        logger.info("Updated note with agent results")

        return StageResult(context=context, should_stop=False)

    def _get_noteable_iid(self, payload: dict) -> int:
        noteable_type = payload.get("object_attributes", {}).get("noteable_type")
        if noteable_type == "MergeRequest":
            return payload.get("merge_request", {}).get("iid")
        elif noteable_type == "Issue":
            return payload.get("issue", {}).get("iid")
        return payload.get("object_attributes", {}).get("noteable_id")
