import os
from typing import Optional

from ..base import PipelineContext

PREP_REPORT_FILENAME = "opencode_prep_report.md"
PREP_EVENTS_FILENAME = "opencode_prep_events.jsonl"


def ensure_prep_report_path(context: PipelineContext, repo_dir: str) -> str:
    report_path = context.metadata.get("prep_report_path")
    if isinstance(report_path, str) and report_path:
        return report_path

    report_path = os.path.join(repo_dir, PREP_REPORT_FILENAME)
    context.metadata["prep_report_path"] = report_path
    return report_path


def ensure_prep_events_path(context: PipelineContext, repo_dir: str) -> str:
    events_path = context.metadata.get("prep_events_path")
    if isinstance(events_path, str) and events_path:
        return events_path

    events_path = os.path.join(repo_dir, PREP_EVENTS_FILENAME)
    context.metadata["prep_events_path"] = events_path
    return events_path


def append_prep_report_section(
    context: PipelineContext, repo_dir: str, title: str, body: str
) -> str:
    report_path = ensure_prep_report_path(context, repo_dir)
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as handle:
            existing = handle.read().rstrip()
        prefix = existing + "\n\n"
    else:
        prefix = "# Repository Preparation Report\n\n"

    content = f"{prefix}## {title}\n\n{body.strip()}\n"
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return report_path


def fenced_block(text: Optional[str]) -> str:
    if not text:
        return "_empty_"
    return f"```text\n{text.rstrip()}\n```"
