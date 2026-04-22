from ..base import Stage, StageResult, PipelineContext
import logging

logger = logging.getLogger(__name__)


class SnapshotResolverStage(Stage):
    """Stage B: Resolve code snapshot (SHA/branch)"""

    @staticmethod
    def _resolve_merge_request_sha(mr: dict) -> str | None:
        diff_refs = mr.get("diff_refs") or {}
        last_commit = mr.get("last_commit") or {}

        for candidate in (
            diff_refs.get("head_sha"),
            mr.get("sha"),
            last_commit.get("id"),
            mr.get("squash_commit_sha"),
            mr.get("merge_commit_sha"),
        ):
            if candidate:
                return str(candidate)
        return None

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        noteable_type = context.metadata.get("noteable_type")
        project = payload.get("project", {})

        snapshot = {}

        if noteable_type == "MergeRequest":
            mr = payload.get("merge_request", {})
            snapshot["sha"] = self._resolve_merge_request_sha(mr)
            snapshot["source_branch"] = mr.get("source_branch")
            snapshot["target_branch"] = mr.get("target_branch")
            snapshot["merge_request_iid"] = mr.get("iid")
            snapshot["merge_request_state"] = mr.get("state")
            snapshot["branch"] = snapshot["source_branch"] or project.get(
                "default_branch"
            )
        elif noteable_type == "Issue":
            snapshot["sha"] = None
            snapshot["branch"] = project.get("default_branch") or "main"

        context.code_snapshot = snapshot
        logger.info(f"Resolved code snapshot: {snapshot}")

        return StageResult(context=context, should_stop=False)
