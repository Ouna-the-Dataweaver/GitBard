from ..base import Stage, StageResult, PipelineContext, WorkspaceConfig
import os
import tempfile
import subprocess
import logging

logger = logging.getLogger(__name__)


class WorkspaceAcquisitionStage(Stage):
    """Build a working directory for the pipeline."""

    def __init__(self, workspace_config: WorkspaceConfig | None = None):
        self.workspace_config = workspace_config or WorkspaceConfig()

    def _execute(self, context: PipelineContext) -> StageResult:
        if self.workspace_config.mode != "fresh_clone":
            raise ValueError(
                f"Unsupported workspace mode: {self.workspace_config.mode}"
            )

        payload = context.webhook_payload
        project = payload.get("project", {})

        temp_dir = tempfile.mkdtemp(prefix="opencode_")
        context.local_context_path = temp_dir
        context.workspace_cleanup_required = self.workspace_config.cleanup_required
        context.metadata["workspace_cleanup_required"] = (
            self.workspace_config.cleanup_required
        )

        git_http_url = project.get("git_http_url")
        if not git_http_url:
            raise ValueError("No git_http_url in project")

        gitlab_pat = os.getenv("GITLAB_PAT", "")

        auth_url = git_http_url.replace("https://", f"https://gitlab:{gitlab_pat}@")

        subprocess.run(
            ["git", "clone", auth_url, temp_dir], check=True, capture_output=True
        )

        if context.code_snapshot.get("sha"):
            subprocess.run(
                ["git", "checkout", context.code_snapshot["sha"]],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )
        elif context.code_snapshot.get("branch"):
            self._checkout_branch_or_merge_request_ref(context, temp_dir)

        logger.info(f"Built local context at: {temp_dir}")

        return StageResult(context=context, should_stop=False)

    def _checkout_branch_or_merge_request_ref(
        self, context: PipelineContext, repo_dir: str
    ) -> None:
        branch = context.code_snapshot["branch"]

        try:
            subprocess.run(
                ["git", "checkout", branch],
                cwd=repo_dir,
                check=True,
                capture_output=True,
            )
            return
        except subprocess.CalledProcessError as exc:
            mr_iid = context.code_snapshot.get("merge_request_iid")
            if not mr_iid:
                raise

            logger.info(
                "Branch %s is unavailable, attempting merge request ref for !%s",
                branch,
                mr_iid,
            )

            local_ref = f"mr-{mr_iid}"
            refspec = f"refs/merge-requests/{mr_iid}/head:refs/heads/{local_ref}"

            try:
                subprocess.run(
                    ["git", "fetch", "origin", refspec],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "checkout", local_ref],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )
                return
            except subprocess.CalledProcessError:
                stderr = exc.stderr.decode("utf-8", errors="ignore").strip()
                raise RuntimeError(
                    "Failed to check out source branch "
                    f"'{branch}'. The source branch may have been deleted and "
                    f"merge request ref !{mr_iid} is no longer available."
                    + (f" Original git error: {stderr}" if stderr else "")
                ) from exc


class ContextBuilderStage(WorkspaceAcquisitionStage):
    """Backward-compatible alias for older imports."""
