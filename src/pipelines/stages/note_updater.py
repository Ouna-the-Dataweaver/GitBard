from ..base import Stage, StageResult, PipelineContext
import logging
from src.gitlab_api import extract_noteable_iid, post_gitlab_note, update_gitlab_note

logger = logging.getLogger(__name__)


class NoteUpdaterStage(Stage):
    """Update the initial note with agent results or error notification"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        project_id = payload.get("project", {}).get("id")
        noteable_type = context.metadata.get("noteable_type")
        noteable_iid = extract_noteable_iid(payload)

        if context.metadata.get("pipeline_error"):
            error_msg = context.metadata.get("pipeline_error", "Unknown error")
            self._publish_note(
                context,
                project_id,
                noteable_type,
                noteable_iid,
                f"❌ **OpenCode Error**\n\nPipeline failed: {error_msg}",
                project=payload.get("project"),
            )
            logger.info("Updated note with error notification")
            return StageResult(context=context, should_stop=False)

        result = context.agent_result
        content = result.content if result else "No results generated"

        self._publish_note(
            context,
            project_id,
            noteable_type,
            noteable_iid,
            f"🤖 **OpenCode Results**\n\n{content}",
            project=payload.get("project"),
        )

        logger.info("Updated note with agent results")

        return StageResult(context=context, should_stop=False)

    def _publish_note(
        self,
        context: PipelineContext,
        project_id,
        noteable_type,
        noteable_iid,
        body: str,
        project=None,
    ):
        if context.gitlab_note_id:
            note_response = update_gitlab_note(
                project_id,
                noteable_type,
                noteable_iid,
                context.gitlab_note_id,
                body,
                project=project,
            )
            if note_response:
                return note_response

        note_response = post_gitlab_note(
            project_id,
            noteable_type,
            noteable_iid,
            body,
            project=project,
        )
        if note_response:
            context.gitlab_note_id = note_response.get("id")
        return note_response
