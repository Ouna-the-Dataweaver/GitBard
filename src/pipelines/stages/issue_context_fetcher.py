import logging
import os
from typing import Dict, List, Optional

import requests

from ..base import Stage, StageResult, PipelineContext

logger = logging.getLogger(__name__)


class IssueContextFetcherStage(Stage):
    """Fetch issue thread content and store it locally."""

    def __init__(self, filename: str = "gitlab_issue_content.md"):
        self.filename = filename

    def _execute(self, context: PipelineContext) -> StageResult:
        if context.metadata.get("noteable_type") != "Issue":
            return StageResult(context=context, should_stop=False)

        repo_dir = context.local_context_path
        if not repo_dir:
            raise ValueError("No local_context_path available for issue context")

        project_id = context.webhook_payload.get("project", {}).get("id")
        issue_iid = context.webhook_payload.get("issue", {}).get("iid")
        if not issue_iid:
            issue_iid = context.webhook_payload.get("object_attributes", {}).get(
                "noteable_id"
            )

        if not project_id or not issue_iid:
            logger.info("Issue context skipped: missing project_id or issue_iid")
            return StageResult(context=context, should_stop=False)

        content = self._build_issue_content(project_id, issue_iid)
        if not content:
            logger.info("Issue context skipped: no content fetched")
            return StageResult(context=context, should_stop=False)

        issue_path = os.path.join(repo_dir, self.filename)
        with open(issue_path, "w", encoding="utf-8") as handle:
            handle.write(content)

        context.metadata["issue_context_path"] = issue_path
        logger.info("Issue context saved to %s", issue_path)

        return StageResult(context=context, should_stop=False)

    def _build_issue_content(self, project_id: int, issue_iid: int) -> Optional[str]:
        gitlab_pat = os.getenv("GITLAB_PAT", "")
        if not gitlab_pat:
            logger.warning("GITLAB_PAT not configured, cannot fetch issue context")
            return None

        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.example.com").rstrip("/")
        if "/api/" in gitlab_url:
            gitlab_url = gitlab_url.split("/api/")[0]
        elif "/-" in gitlab_url:
            gitlab_url = gitlab_url.split("/-")[0]

        headers = {"PRIVATE-TOKEN": gitlab_pat}
        issue_url = f"{gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}"
        notes_url = (
            f"{gitlab_url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes"
        )

        try:
            issue_resp = requests.get(issue_url, headers=headers, timeout=15)
            issue_resp.raise_for_status()
            notes_resp = requests.get(notes_url, headers=headers, timeout=15)
            notes_resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to fetch issue context: %s", exc)
            return None

        issue = issue_resp.json()
        notes = notes_resp.json()
        return self._format_issue_markdown(issue, notes)

    def _format_issue_markdown(
        self, issue: Dict[str, object], notes: List[Dict[str, object]]
    ) -> str:
        title = str(issue.get("title") or "")
        state = str(issue.get("state") or "")
        description = issue.get("description") or "No description provided."

        lines: List[str] = ["# GitLab Issue Context", "", f"Title: {title}"]
        if state:
            lines.append(f"State: {state}")
        lines.extend(["", "## Description", str(description).strip(), "", "## Notes"])

        sorted_notes = sorted(notes, key=lambda note: str(note.get("created_at") or ""))
        if not sorted_notes:
            lines.append("No notes found.")
            return "\n".join(lines).strip() + "\n"

        for note in sorted_notes:
            author = note.get("author") or {}
            author_name = str(author.get("name") or "Unknown")
            created_at = str(note.get("created_at") or "")
            body = str(note.get("body") or "").strip() or "_No content_"
            header = f"### {author_name}"
            if created_at:
                header = f"{header} ({created_at})"
            lines.extend(["", header, body])

        return "\n".join(lines).strip() + "\n"
