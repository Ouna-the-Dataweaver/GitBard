import json
import logging
import os
import re
import selectors
import subprocess
import time
from pathlib import Path
from typing import List

from src.opencode_command import DEFAULT_OPENCODE_MODEL, opencode_command_args

from ..base import AgentResult, PipelineContext, Stage, StageResult
from .preparation_support import (
    append_prep_report_section,
    ensure_prep_events_path,
    fenced_block,
)

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
OPENCODE_CONFIG_PATH = REPO_ROOT / "opencode.json"
DEFAULT_MAX_OPENCODE_ERRORS = 12
MAX_OPENCODE_ERROR_LINES = 8
MAX_OPENCODE_ERROR_CHARS = 2000
DEFAULT_OPENCODE_HEARTBEAT_SECONDS = 60
LLM_LOG_PATTERN = re.compile(r"\bproviderID=(?P<provider>\S+)\s+modelID=(?P<model>\S+)")
LOG_FIELD_PATTERNS = {
    "service": re.compile(r"\bservice=(?P<value>\S+)"),
    "provider": re.compile(r"\bproviderID=(?P<value>\S+)"),
    "model": re.compile(r"\bmodelID=(?P<value>\S+)"),
    "status": re.compile(r'"statusCode"\s*:\s*(?P<value>\d+)'),
    "request_id": re.compile(r'"request_id"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"'),
    "retryable": re.compile(r'"isRetryable"\s*:\s*(?P<value>true|false)'),
}
ERROR_TYPE_PATTERN = re.compile(r'"type"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"')
ERROR_NAME_PATTERN = re.compile(r'"name"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"')
ERROR_MESSAGE_PATTERN = re.compile(r'"message"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"')
ERROR_VALUE_PATTERN = re.compile(r'\berror\.error="(?P<value>(?:\\.|[^"\\])*)"')


class OpencodeErrorDetector:
    """Detect repeated OpenCode provider failures from debug log lines."""

    ERROR_MARKERS = (
        "AI_APICallError",
        "AI_RetryError",
        "APIConnectionError",
        "APITimeoutError",
        "AuthenticationError",
        "rate_limit_error",
        "usage limit exceeded",
        "maxRetriesExceeded",
        "stream error",
        "statusCode\":401",
        "statusCode\":403",
        "statusCode\":429",
        "401 Unauthorized",
        "403 Forbidden",
        "429",
    )

    def __init__(self, max_errors: int = DEFAULT_MAX_OPENCODE_ERRORS):
        self.max_errors = max_errors
        self.error_count = 0
        self.last_error = ""
        self.observed_provider = ""
        self.observed_model = ""

    def observe(self, line: str) -> bool:
        self._observe_runtime_model(line)
        if not self._is_error_line(line):
            return False

        self.error_count += 1
        self.last_error = summarize_opencode_error_line(line)
        logger.warning(
            "OpenCode provider error event %s/%s: %s",
            self.error_count,
            self.max_errors,
            self.last_error,
        )
        return self.error_count >= self.max_errors

    def _is_error_line(self, line: str) -> bool:
        if not line.strip():
            return False
        if "ERROR" not in line and "error" not in line:
            return False
        return any(marker in line for marker in self.ERROR_MARKERS)

    def _observe_runtime_model(self, line: str) -> None:
        match = LLM_LOG_PATTERN.search(line)
        if not match:
            return
        self.observed_provider = match.group("provider")
        self.observed_model = match.group("model")


def summarize_opencode_error(stderr: str) -> str:
    """Return a compact, publishable summary of noisy OpenCode debug stderr."""

    summaries = []
    for line in stderr.splitlines():
        if not _is_publishable_error_line(line):
            continue

        summary = summarize_opencode_error_line(line)
        if summary and summary not in summaries:
            summaries.append(summary)
        if len(summaries) >= MAX_OPENCODE_ERROR_LINES:
            break

    if not summaries:
        summaries = [line.strip() for line in stderr.splitlines() if line.strip()][
            -MAX_OPENCODE_ERROR_LINES:
        ]

    summary = "\n".join(summaries).strip()
    if not summary:
        return "Unknown opencode error"
    if len(summary) > MAX_OPENCODE_ERROR_CHARS:
        return summary[:MAX_OPENCODE_ERROR_CHARS].rstrip() + "\n... truncated"
    return summary


def summarize_opencode_error_line(line: str) -> str:
    searchable = line.replace('\\"', '"')
    fields = {
        name: _unescape_log_value(match.group("value"))
        for name, pattern in LOG_FIELD_PATTERNS.items()
        if (match := pattern.search(searchable))
    }

    error_types = [
        _unescape_log_value(match.group("value"))
        for match in ERROR_TYPE_PATTERN.finditer(searchable)
    ]
    error_names = [
        _unescape_log_value(match.group("value"))
        for match in ERROR_NAME_PATTERN.finditer(searchable)
        if _unescape_log_value(match.group("value")).endswith("Error")
    ]
    if error_types or error_names:
        fields["type"] = _choose_error_type([*error_types, *error_names])

    message_match = ERROR_MESSAGE_PATTERN.search(searchable)
    if message_match:
        fields["message"] = _unescape_log_value(message_match.group("value"))
    elif "usage limit exceeded" in searchable:
        fields["message"] = "usage limit exceeded"
    elif "rate_limit_error" in searchable:
        fields["type"] = fields.get("type", "rate_limit_error")

    error_value_match = ERROR_VALUE_PATTERN.search(searchable)
    if error_value_match:
        error_type, error_message = _split_error_value(
            _unescape_log_value(error_value_match.group("value"))
        )
        if error_type:
            fields.setdefault("type", error_type)
        if error_message:
            fields.setdefault("message", error_message)

    if not fields:
        return _compact_plain_error_line(line)

    parts = []
    for key in (
        "service",
        "provider",
        "model",
        "status",
        "type",
        "message",
        "request_id",
        "retryable",
    ):
        value = fields.get(key)
        if value:
            parts.append(f"{key}={value}")
    return "OpenCode provider error: " + " ".join(parts)


def _is_publishable_error_line(line: str) -> bool:
    return OpencodeErrorDetector()._is_error_line(line)


def _choose_error_type(error_types: list[str]) -> str:
    for error_type in reversed(error_types):
        if error_type not in {"error", "auto"}:
            return error_type
    return error_types[-1]


def _unescape_log_value(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def _split_error_value(value: str) -> tuple[str, str]:
    """Split an `error.error="Type: message"` log value into type and message.

    OpenCode emits provider failures as `error.error="AI_APICallError: ..."` or
    `error.error="AI_RetryError: ..."`. The prefix before the first ": " is the
    error type when it is a single whitespace-free token; the remainder is the
    human-readable message.
    """
    if ": " not in value:
        return "", value
    prefix, _, rest = value.partition(": ")
    if prefix.strip() and not any(ch.isspace() for ch in prefix):
        return prefix, rest
    return "", value


def _compact_plain_error_line(line: str) -> str:
    line = line.strip()
    if len(line) <= 240:
        return line
    return line[:240].rstrip() + " ..."


class BaseOpencodeStage(Stage):
    """Shared OpenCode invocation helpers."""

    def __init__(self, model: str | None = None, agent: str | None = None):
        env_model = os.getenv("OPENCODE_MODEL")
        env_agent = os.getenv("OPENCODE_AGENT")
        self.model = model or env_model or DEFAULT_OPENCODE_MODEL
        self.agent = agent or env_agent or "Build"
        self.model_source = "pipeline" if model else "env" if env_model else "default"
        self.agent_source = "pipeline" if agent else "env" if env_agent else "default"

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

        args = opencode_command_args(
            "run",
            "--format",
            "json",
            "--print-logs",
            "--log-level",
            "DEBUG",
            "--model",
            self.model,
            "--agent",
            self.agent,
            prompt,
        )
        max_errors = int(
            os.getenv("OPENCODE_MAX_ERROR_EVENTS", DEFAULT_MAX_OPENCODE_ERRORS)
        )
        detector = OpencodeErrorDetector(max_errors=max_errors)
        logger.info(
            "Starting OpenCode run cwd=%s command=%s model=%s model_source=%s "
            "agent=%s agent_source=%s config=%s max_error_events=%s prompt_chars=%s",
            repo_dir,
            self._format_command_for_log(args),
            self.model,
            self.model_source,
            self.agent,
            self.agent_source,
            env.get("OPENCODE_CONFIG", ""),
            max_errors,
            len(prompt),
        )
        result = self._run_opencode_streaming(args, repo_dir, env, detector)
        logger.info(
            "OpenCode run finished returncode=%s requested_model=%s requested_agent=%s "
            "observed_provider=%s observed_model=%s provider_error_events=%s "
            "last_error=%s",
            result.returncode,
            self.model,
            self.agent,
            detector.observed_provider or "unknown",
            detector.observed_model or "unknown",
            detector.error_count,
            detector.last_error or "none",
        )
        return result

    def _format_command_for_log(self, args: list[str]) -> list[str]:
        if not args:
            return args
        return [*args[:-1], f"<prompt chars={len(args[-1])}>"]

    def _run_opencode_streaming(
        self,
        args: list[str],
        repo_dir: str,
        env: dict[str, str],
        detector: OpencodeErrorDetector,
    ) -> subprocess.CompletedProcess:
        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []
        stdout_log_path = os.path.join(repo_dir, "opencode_stdout.jsonl")
        stderr_log_path = os.path.join(repo_dir, "opencode_stderr.log")
        status_log_path = os.path.join(repo_dir, "opencode_status.log")
        heartbeat_seconds = int(
            os.getenv("OPENCODE_HEARTBEAT_SECONDS", DEFAULT_OPENCODE_HEARTBEAT_SECONDS)
        )

        process = subprocess.Popen(
            args,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
        )

        selector = selectors.DefaultSelector()
        if process.stdout:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        if process.stderr:
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")

        started_at = time.monotonic()
        last_output_at = started_at
        last_heartbeat_at = started_at
        self._write_opencode_status(
            status_log_path,
            "started "
            f"pid={process.pid} stdout_log={stdout_log_path} stderr_log={stderr_log_path}",
        )
        logger.info(
            "OpenCode live logs stdout=%s stderr=%s status=%s pid=%s",
            stdout_log_path,
            stderr_log_path,
            status_log_path,
            process.pid,
        )

        try:
            with open(stdout_log_path, "w", encoding="utf-8") as stdout_log, open(
                stderr_log_path, "w", encoding="utf-8"
            ) as stderr_log:
                while selector.get_map():
                    selected = selector.select(timeout=0.5)
                    if not selected:
                        now = time.monotonic()
                        if heartbeat_seconds > 0 and now - last_heartbeat_at >= heartbeat_seconds:
                            self._log_opencode_heartbeat(
                                status_log_path,
                                started_at,
                                last_output_at,
                                stdout_log_path,
                                stderr_log_path,
                            )
                            last_heartbeat_at = now

                    for key, _ in selected:
                        line = key.fileobj.readline()
                        if line == "":
                            selector.unregister(key.fileobj)
                            continue

                        last_output_at = time.monotonic()
                        if key.data == "stdout":
                            stdout_chunks.append(line)
                            stdout_log.write(line)
                            stdout_log.flush()
                        else:
                            stderr_chunks.append(line)
                            stderr_log.write(line)
                            stderr_log.flush()
                            if detector.observe(line):
                                self._terminate_opencode(process)
                                error_summary = summarize_opencode_error(
                                    "\n".join(
                                        [*stderr_chunks, detector.last_error]
                                    )
                                )
                                message = (
                                    "OpenCode stopped after "
                                    f"{detector.error_count} provider error log events.\n"
                                    f"{error_summary}"
                                )
                                self._write_opencode_status(status_log_path, message)
                                return subprocess.CompletedProcess(
                                    args,
                                    (
                                        process.returncode
                                        if process.returncode is not None
                                        else -9
                                    ),
                                    "".join(stdout_chunks),
                                    message,
                                )

                    if process.poll() is not None:
                        for key in list(selector.get_map().values()):
                            remainder = key.fileobj.read()
                            if remainder:
                                if key.data == "stdout":
                                    stdout_chunks.append(remainder)
                                    stdout_log.write(remainder)
                                    stdout_log.flush()
                                else:
                                    stderr_chunks.append(remainder)
                                    stderr_log.write(remainder)
                                    stderr_log.flush()
                            selector.unregister(key.fileobj)
        finally:
            selector.close()

        self._write_opencode_status(
            status_log_path,
            f"finished returncode={process.returncode} elapsed_s={int(time.monotonic() - started_at)}",
        )
        return subprocess.CompletedProcess(
            args,
            process.wait(),
            "".join(stdout_chunks),
            "".join(stderr_chunks),
        )

    def _terminate_opencode(self, process: subprocess.Popen) -> None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def _log_opencode_heartbeat(
        self,
        status_log_path: str,
        started_at: float,
        last_output_at: float,
        stdout_log_path: str,
        stderr_log_path: str,
    ) -> None:
        now = time.monotonic()
        message = (
            f"still running elapsed_s={int(now - started_at)} "
            f"last_output_s={int(now - last_output_at)}"
        )
        logger.info(
            "OpenCode %s stdout=%s stderr=%s",
            message,
            stdout_log_path,
            stderr_log_path,
        )
        self._write_opencode_status(status_log_path, message)

    def _write_opencode_status(self, status_log_path: str, message: str) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(status_log_path, "a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")

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
            stderr_summary = (
                summarize_opencode_error(result.stderr) if result.stderr.strip() else ""
            )
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
                    fenced_block(stderr_summary),
                ]
            )
            append_prep_report_section(context, repo_dir, "OpenCode Preparation", body)

            if result.returncode != 0:
                logger.warning("OpenCode preparation failed: %s", stderr_summary)
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
            error_msg = summarize_opencode_error(result.stderr)
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
