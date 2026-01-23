from ..base import Stage, StageResult, PipelineContext
import os
import tempfile
import subprocess
import logging

logger = logging.getLogger(__name__)


class ContextBuilderStage(Stage):
    """Stage C: Build local directory with resolved repo state"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        project = payload.get("project", {})

        temp_dir = tempfile.mkdtemp(prefix="opencode_")
        context.local_context_path = temp_dir

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
            subprocess.run(
                ["git", "checkout", context.code_snapshot["branch"]],
                cwd=temp_dir,
                check=True,
                capture_output=True,
            )

        logger.info(f"Built local context at: {temp_dir}")

        return StageResult(context=context, should_stop=False)
