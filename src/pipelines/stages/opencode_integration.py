import json
import logging
import os
import subprocess
from typing import List

from ..base import Stage, StageResult, PipelineContext, AgentResult

logger = logging.getLogger(__name__)


class OpencodeIntegrationStage(Stage):
    """Run opencode with JSON output and capture reply."""

    def __init__(self, model: str = "minimax/MiniMax-M2.1", agent: str = "Build"):
        self.model = model
        self.agent = agent

    def _execute(self, context: PipelineContext) -> StageResult:
        repo_dir = context.local_context_path
        if not repo_dir:
            raise ValueError("No local_context_path available for opencode")

        question = self._extract_question(context)
        prompt = f"Answer this GitLab thread question:\n\n{question}".strip()
        issue_context_path = context.metadata.get("issue_context_path")
        if issue_context_path:
            relative_path = os.path.relpath(issue_context_path, repo_dir)
            prompt = f"{prompt}\n\nUse the issue thread context in {relative_path}."

        result = subprocess.run(
            [
                "opencode",
                "run",
                "--format",
                "json",
                "--model",
                self.model,
                "--agent",
                self.agent,
                prompt,
            ],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
        )

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

    def _extract_question(self, context: PipelineContext) -> str:
        note_body = context.metadata.get("note_body", "")
        trigger = context.metadata.get("trigger_pattern", "")
        question = note_body.replace(trigger, "").strip()
        return question or "No additional question provided."

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
