import logging
import os
import subprocess
import time

from ..base import PipelineContext, Stage, StageResult
from .preparation_support import append_prep_report_section, fenced_block

logger = logging.getLogger(__name__)


class RepoHookPreparationStage(Stage):
    """Run an optional repo-defined setup hook."""

    def __init__(self, enabled: bool = True, script_name: str = ".gitbard.sh"):
        self.enabled = enabled
        self.script_name = script_name

    def _execute(self, context: PipelineContext) -> StageResult:
        if not self.enabled:
            return StageResult(context=context, should_stop=False)

        repo_dir = context.local_context_path
        if not repo_dir:
            raise ValueError("No local_context_path available for repo hook")

        script_path = os.path.join(repo_dir, self.script_name)
        if not os.path.exists(script_path):
            logger.info("Repo hook skipped: %s not found", self.script_name)
            return StageResult(context=context, should_stop=False)

        started_at = time.monotonic()
        try:
            result = subprocess.run(
                ["bash", self.script_name],
                cwd=repo_dir,
                check=False,
                capture_output=True,
                text=True,
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except Exception as exc:
            exit_code = -1
            stdout = ""
            stderr = str(exc)

        duration = time.monotonic() - started_at
        status = "success" if exit_code == 0 else "failed"
        body = "\n".join(
            [
                f"Status: {status}",
                f"Script: `{self.script_name}`",
                f"Exit code: `{exit_code}`",
                f"Duration: `{duration:.2f}s`",
                "",
                "### Stdout",
                fenced_block(stdout),
                "",
                "### Stderr",
                fenced_block(stderr),
            ]
        )
        append_prep_report_section(context, repo_dir, "Repo Hook", body)

        if exit_code != 0:
            logger.warning("Repo hook %s failed with exit code %s", self.script_name, exit_code)

        return StageResult(context=context, should_stop=False)
