import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List

from src.opencode_command import opencode_command_args

from ..base import AgentResult, PipelineContext, Stage, StageResult
from .preparation_support import (
    append_prep_report_section,
    ensure_prep_events_path,
    fenced_block,
)

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
OPENCODE_CONFIG_PATH = REPO_ROOT / "opencode.json"


class BaseOpencodeStage(Stage):
    """Shared OpenCode invocation helpers."""

    def __init__(self, model: str | None = None, agent: str | None = None):
        self.model = model or os.getenv("OPENCODE_MODEL", "minimax/MiniMax-M2.1")
        self.agent = agent or os.getenv("OPENCODE_AGENT", "Build")

    def _require_repo_dir(self, context: PipelineContext) -> str:
        repo_dir = context.local_context_path
        if not repo_dir:
            raise ValueError("No local_context_path available for opencode")
        return repo_dir

    def _extract_question(self, context: PipelineContext) -> str:
        note_body = context.metadata.get("note_body", "")
        trigger = context.metadata.get("trigger_pattern", "")
        question = note_body.replace(trigger, "").strip()
        return question or "No additional question provided."

    def _format_noteable_type(self, noteable_type: str) -> str:
        normalized = noteable_type.replace("_", " ").strip()
        if normalized == "MergeRequest":
            return "merge request"
        return normalized.lower()

    def _append_shared_context(
        self, prompt: List[str], context: PipelineContext, repo_dir: str
    ) -> None:
        thread_context_path = context.metadata.get("thread_context_path")
        if thread_context_path:
            relative_path = os.path.relpath(thread_context_path, repo_dir)
            prompt.append(f"Use the thread context in {relative_path}.")

        snapshot = context.code_snapshot or {}
        source_branch = snapshot.get("source_branch")
        target_branch = snapshot.get("target_branch")
        merge_request_state = snapshot.get("merge_request_state")
        if source_branch or target_branch:
            prompt.append(
                f"Current review scope is {source_branch or '?'} -> {target_branch or '?'}."
            )
        if merge_request_state:
            prompt.append(f"Merge request state: {merge_request_state}.")

    def _run_opencode(self, repo_dir: str, prompt: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        if OPENCODE_CONFIG_PATH.exists():
            env.setdefault("OPENCODE_CONFIG", str(OPENCODE_CONFIG_PATH))

        return subprocess.run(
            opencode_command_args(
                "run",
                "--format",
                "json",
                "--model",
                self.model,
                "--agent",
                self.agent,
                prompt,
            ),
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def _extract_text_events(self, lines: List[str]) -> str:
        chunks: List[str] = []
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue
            try:
                event = json.loads(trimmed)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "text":
                part = event.get("part", {})
                text = part.get("text")
                if text:
                    chunks.append(text)
        return "".join(chunks).strip()


class OpencodePreparationStage(BaseOpencodeStage):
    """Run a prep-oriented OpenCode pass before the main agent."""

    def __init__(
        self,
        model: str | None = None,
        agent: str | None = None,
        enabled: bool = True,
    ):
        super().__init__(model=model, agent=agent or "gitlab-prepare")
        self.enabled = enabled

    def _execute(self, context: PipelineContext) -> StageResult:
        if not self.enabled:
            return StageResult(context=context, should_stop=False)

        repo_dir = self._require_repo_dir(context)
        question = self._extract_question(context)
        prompt = self._build_prompt(context, repo_dir, question)
        events_path = ensure_prep_events_path(context, repo_dir)

        try:
            result = self._run_opencode(repo_dir, prompt)
            with open(events_path, "w", encoding="utf-8") as handle:
                handle.write(result.stdout)

            content = self._extract_text_events(result.stdout.splitlines())
            if not content:
                content = "No preparation summary generated."

            status = "success" if result.returncode == 0 else "failed"
            body = "\n".join(
                [
                    f"Status: {status}",
                    f"Agent: `{self.agent}`",
                    f"Model: `{self.model}`",
                    f"Events: `{os.path.basename(events_path)}`",
                    "",
                    "### Summary",
                    content,
                    "",
                    "### Stderr",
                    fenced_block(result.stderr),
                ]
            )
            append_prep_report_section(context, repo_dir, "OpenCode Preparation", body)

            if result.returncode != 0:
                logger.warning("OpenCode preparation failed: %s", result.stderr.strip())
        except Exception as exc:
            body = "\n".join(
                [
                    "Status: failed",
                    f"Agent: `{self.agent}`",
                    f"Model: `{self.model}`",
                    "",
                    "### Summary",
                    "Preparation run could not be completed.",
                    "",
                    "### Stderr",
                    fenced_block(str(exc)),
                ]
            )
            append_prep_report_section(context, repo_dir, "OpenCode Preparation", body)
            logger.warning("OpenCode preparation raised an exception: %s", exc)

        return StageResult(context=context, should_stop=False)

    def _build_prompt(
        self, context: PipelineContext, repo_dir: str, question: str
    ) -> str:
        noteable_type = self._format_noteable_type(
            context.metadata.get("noteable_type") or "thread"
        )
        prompt = [
            f"Prepare this GitLab {noteable_type} repository for work.",
            f"User request: {question}",
            "Work inside the checked out repository.",
            "Attempt to install dependencies and prepare any environment needed to analyze or work on the request.",
            "You may create non-repository environment artifacts, but do not edit tracked repository files.",
            "Summarize what you installed, what failed, and what still blocks progress.",
        ]
        self._append_shared_context(prompt, context, repo_dir)
        prompt.append(
            "Base the answer on the local repository and the provided GitLab context file."
        )
        return "\n\n".join(part for part in prompt if part)


class OpencodeIntegrationStage(BaseOpencodeStage):
    """Run opencode with JSON output and capture reply."""

    def _execute(self, context: PipelineContext) -> StageResult:
        self._validate_review_inputs(context)
        repo_dir = self._require_repo_dir(context)

        question = self._extract_question(context)
        prompt = self._build_prompt(context, repo_dir, question)
        result = self._run_opencode(repo_dir, prompt)

        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown opencode error"
            raise RuntimeError(f"opencode run failed: {error_msg}")

        events_path = os.path.join(repo_dir, "opencode_events.jsonl")
        reply_path = os.path.join(repo_dir, "opencode_reply.md")

        with open(events_path, "w", encoding="utf-8") as handle:
            handle.write(result.stdout)

        content = self._extract_text_events(result.stdout.splitlines())
        if not content:
            content = "No response generated."

        with open(reply_path, "w", encoding="utf-8") as handle:
            handle.write(content.strip() + "\n")

        context.agent_result = AgentResult(
            content=content.strip(),
            format="markdown",
            metadata={
                "agent_type": self.agent,
                "model": self.model,
                "opencode_events_path": events_path,
                "opencode_reply_path": reply_path,
            },
        )

        logger.info("Opencode integration completed")

        return StageResult(context=context, should_stop=False)

    def _validate_review_inputs(self, context: PipelineContext) -> None:
        if context.command not in {"oc_review", "oc_deepreview"}:
            return

        if context.metadata.get("noteable_type") != "MergeRequest":
            return

        snapshot = context.code_snapshot or {}
        merge_request_state = str(snapshot.get("merge_request_state") or "").lower()
        thread_context_path = context.metadata.get("thread_context_path")

        if merge_request_state and merge_request_state != "opened" and not thread_context_path:
            raise RuntimeError(
                "Cannot review this merge request reliably because it is not open and "
                "the GitLab merge request diff could not be fetched. Refusing to compare "
                "against the current target branch."
            )

    def _build_prompt(
        self, context: PipelineContext, repo_dir: str, question: str
    ) -> str:
        noteable_type = self._format_noteable_type(
            context.metadata.get("noteable_type") or "thread"
        )
        if context.command in {"oc_review", "oc_deepreview"}:
            prompt = self._build_review_prompt(noteable_type, question)
        else:
            prompt = self._build_question_prompt(noteable_type, question)

        self._append_shared_context(prompt, context, repo_dir)

        prep_report_path = context.metadata.get("prep_report_path")
        if prep_report_path:
            relative_path = os.path.relpath(prep_report_path, repo_dir)
            prompt.append(f"Review the preparation report in {relative_path} before answering.")

        prompt.append(
            "Base the answer on the local repository and the provided GitLab context file."
        )
        return "\n\n".join(part for part in prompt if part)

    def _build_question_prompt(self, noteable_type: str, question: str) -> List[str]:
        return [
            f"Answer this GitLab {noteable_type.lower()} question:",
            question,
            "Work inside the checked out repository.",
            "If this is a merge request, summarize the MR first and then provide a concise review.",
        ]

    def _build_review_prompt(self, noteable_type: str, question: str) -> List[str]:
        prompt = [
            f"Review this GitLab {noteable_type.lower()}.",
            "Work inside the checked out repository.",
            "Inspect the actual changed files and diff before writing findings.",
            "If this is a merge request, summarize the MR briefly before listing findings.",
            "If a GitLab merge request context file is available, treat its MR changes as the canonical diff.",
            "Do not infer additions or deletions by comparing the checked out repository to the current target branch when branch tips may have moved.",
        ]
        if question != "No additional question provided.":
            prompt.append(f"Additional reviewer request: {question}")
        return prompt
