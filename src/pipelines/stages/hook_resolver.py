from ..base import Stage, StageResult, PipelineContext
import logging
from src.gitlab_api import extract_noteable_iid, post_gitlab_note

logger = logging.getLogger(__name__)


class HookResolverStage(Stage):
    """Stage A: Detect commands from webhook and create initial note"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload

        if payload.get("object_kind") != "note":
            return StageResult(context=context, should_stop=True)

        note = payload.get("object_attributes", {}).get("note", "")
        noteable_type = payload.get("object_attributes", {}).get("noteable_type")

        if note.startswith("🤖 OpenCode"):
            logger.info("Skipping note posted by ourselves")
            return StageResult(context=context, should_stop=True)

        trigger_pattern = context.metadata.get("trigger_pattern")
        display_trigger = context.metadata.get("display_trigger")

        if context.command:
            command_name = context.command
        else:
            from ..registry import detect_command

            command = detect_command(note)

            if not command:
                logger.info(f"No command detected in note: {note}")
                return StageResult(context=context, should_stop=True)

            command_name = command.name
            trigger_pattern = command.trigger_pattern
            display_trigger = command.trigger_pattern

        context.command = command_name
        context.metadata["noteable_type"] = noteable_type
        context.metadata["note_body"] = note
        context.metadata["trigger_pattern"] = trigger_pattern or command_name
        context.metadata["display_trigger"] = display_trigger or trigger_pattern or command_name

        project_id = payload.get("project", {}).get("id")
        noteable_iid = extract_noteable_iid(payload)

        note_response = post_gitlab_note(
            project_id,
            noteable_type,
            noteable_iid,
            "🤖 OpenCode started working on "
            f"`{context.metadata['display_trigger']}`...",
            project=payload.get("project"),
        )

        if note_response:
            context.gitlab_note_id = note_response.get("id")

        return StageResult(context=context, should_stop=False)
