from ..base import Stage, StageResult, PipelineContext
import logging

logger = logging.getLogger(__name__)


class SnapshotResolverStage(Stage):
    """Stage B: Resolve code snapshot (SHA/branch)"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        noteable_type = context.metadata.get("noteable_type")

        snapshot = {}

        if noteable_type == "MergeRequest":
            mr = payload.get("merge_request", {})
            snapshot["sha"] = mr.get("diff_refs", {}).get("head_sha")
            snapshot["source_branch"] = mr.get("source_branch")
            snapshot["target_branch"] = mr.get("target_branch")
        elif noteable_type == "Issue":
            snapshot["sha"] = None
            snapshot["branch"] = "main"

        context.code_snapshot = snapshot
        logger.info(f"Resolved code snapshot: {snapshot}")

        return StageResult(context=context, should_stop=False)
