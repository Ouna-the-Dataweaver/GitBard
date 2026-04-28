import logging
import os
from typing import Dict, List, Optional

import requests

from ..base import Stage, StageResult, PipelineContext
from src.gitlab_api import extract_noteable_iid, normalize_gitlab_url

logger = logging.getLogger(__name__)


class IssueContextFetcherStage(Stage):
    """Fetch GitLab issue or MR thread content and store it locally."""

    def __init__(
        self,
        filename: str = "gitlab_thread_context.md",
        write_to_workspace: bool = True,
        pass_to_next: bool = True,
    ):
        self.filename = filename
        self.write_to_workspace = write_to_workspace
        self.pass_to_next = pass_to_next

    def _execute(self, context: PipelineContext) -> StageResult:
        noteable_type = context.metadata.get("noteable_type")
        if noteable_type not in {"Issue", "MergeRequest"}:
            return StageResult(context=context, should_stop=False)

        repo_dir = context.local_context_path
        if not repo_dir:
            raise ValueError("No local_context_path available for thread context")

        project_id = context.webhook_payload.get("project", {}).get("id")
        noteable_iid = extract_noteable_iid(context.webhook_payload)

        if not project_id or not noteable_iid:
            logger.info("Thread context skipped: missing project_id or noteable_iid")
            return StageResult(context=context, should_stop=False)

        if noteable_type == "Issue":
            content = self._build_issue_content(
                project_id, noteable_iid, context.webhook_payload.get("project")
            )
        else:
            content = self._build_merge_request_content(
                project_id, noteable_iid, context.webhook_payload.get("project")
            )
        if not content:
            logger.info("Thread context skipped: no content fetched")
            return StageResult(context=context, should_stop=False)

        if self.pass_to_next:
            context.metadata["thread_context_content"] = content

        if self.write_to_workspace:
            issue_path = os.path.join(repo_dir, self.filename)
            with open(issue_path, "w", encoding="utf-8") as handle:
                handle.write(content)

            context.metadata["thread_context_path"] = issue_path
            logger.info("Thread context saved to %s", issue_path)
        else:
            context.metadata.pop("thread_context_path", None)
            logger.info("Thread context fetched without workspace file output")

        return StageResult(context=context, should_stop=False)

    def _build_issue_content(
        self, project_id: int, issue_iid: int, project: Optional[Dict[str, object]] = None
    ) -> Optional[str]:
        gitlab_pat = os.getenv("GITLAB_PAT", "")
        if not gitlab_pat:
            logger.warning("GITLAB_PAT not configured, cannot fetch issue context")
            return None

        gitlab_url = normalize_gitlab_url(project=project)

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

        try:
            issue = issue_resp.json()
            notes = notes_resp.json()
        except ValueError as exc:
            logger.error(
                "Issue context fetch returned non-JSON response for project %s issue %s: %s",
                project_id,
                issue_iid,
                exc,
            )
            logger.error("Issue response preview: %s", issue_resp.text[:200].strip())
            logger.error("Notes response preview: %s", notes_resp.text[:200].strip())
            return None

        return self._format_issue_markdown(issue, notes)

    def _build_merge_request_content(
        self, project_id: int, mr_iid: int, project: Optional[Dict[str, object]] = None
    ) -> Optional[str]:
        gitlab_pat = os.getenv("GITLAB_PAT", "")
        if not gitlab_pat:
            logger.warning("GITLAB_PAT not configured, cannot fetch MR context")
            return None

        gitlab_url = normalize_gitlab_url(project=project)
        headers = {"PRIVATE-TOKEN": gitlab_pat}
        mr_url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}"
        notes_url = (
            f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
        )
        changes_url = (
            f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/changes"
        )

        try:
            mr_resp = requests.get(mr_url, headers=headers, timeout=15)
            mr_resp.raise_for_status()
            notes_resp = requests.get(notes_url, headers=headers, timeout=15)
            notes_resp.raise_for_status()
            changes_resp = requests.get(changes_url, headers=headers, timeout=15)
            changes_resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to fetch MR context: %s", exc)
            return None

        try:
            mr = mr_resp.json()
            notes = notes_resp.json()
            changes = changes_resp.json()
        except ValueError as exc:
            logger.error(
                "MR context fetch returned non-JSON response for project %s MR %s: %s",
                project_id,
                mr_iid,
                exc,
            )
            logger.error("MR response preview: %s", mr_resp.text[:200].strip())
            logger.error("Notes response preview: %s", notes_resp.text[:200].strip())
            logger.error(
                "Changes response preview: %s", changes_resp.text[:200].strip()
            )
            return None

        return self._format_merge_request_markdown(mr, notes, changes)

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

    def _format_merge_request_markdown(
        self,
        merge_request: Dict[str, object],
        notes: List[Dict[str, object]],
        changes_payload: Dict[str, object],
    ) -> str:
        title = str(merge_request.get("title") or "")
        state = str(merge_request.get("state") or "")
        description = merge_request.get("description") or "No description provided."
        source_branch = str(merge_request.get("source_branch") or "")
        target_branch = str(merge_request.get("target_branch") or "")
        web_url = str(merge_request.get("web_url") or "")

        lines: List[str] = ["# GitLab Merge Request Context", "", f"Title: {title}"]
        if state:
            lines.append(f"State: {state}")
        if source_branch or target_branch:
            lines.append(f"Branches: {source_branch} -> {target_branch}".strip())
        if web_url:
            lines.append(f"URL: {web_url}")
        lines.extend(
            ["", "## Description", str(description).strip(), "", "## Notes"]
        )

        sorted_notes = sorted(notes, key=lambda note: str(note.get("created_at") or ""))
        if not sorted_notes:
            lines.append("No notes found.")
        else:
            for note in sorted_notes:
                author = note.get("author") or {}
                author_name = str(author.get("name") or "Unknown")
                created_at = str(note.get("created_at") or "")
                body = str(note.get("body") or "").strip() or "_No content_"
                header = f"### {author_name}"
                if created_at:
                    header = f"{header} ({created_at})"
                lines.extend(["", header, body])

        lines.extend(["", "## Changes"])
        changes = changes_payload.get("changes") or []
        if not changes:
            lines.append("No changes returned.")
            return "\n".join(lines).strip() + "\n"

        for change in changes:
            old_path = str(change.get("old_path") or "")
            new_path = str(change.get("new_path") or "")
            diff = str(change.get("diff") or "").strip()
            lines.extend(
                [
                    "",
                    f"### {new_path or old_path or 'unknown file'}",
                    f"- old_path: {old_path or '_unknown_'}",
                    f"- new_path: {new_path or '_unknown_'}",
                    "```diff",
                    diff or "# no diff returned",
                    "```",
                ]
            )

        return "\n".join(lines).strip() + "\n"
