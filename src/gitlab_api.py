import logging
import os
from typing import Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

import requests

logger = logging.getLogger(__name__)


def _strip_gitlab_suffix(path: str) -> str:
    if "/api/" in path:
        return path.split("/api/", 1)[0]
    if "/-/" in path:
        return path.split("/-/", 1)[0]
    if path.endswith("/-"):
        return path[:-2]
    return path


def _normalize_project_url(project_url: str) -> str:
    parsed = urlsplit(project_url)
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _derive_base_url_from_project(project: Optional[Mapping[str, object]]) -> Optional[str]:
    if not project:
        return None

    path_with_namespace = str(project.get("path_with_namespace") or "").strip("/")

    for key in ("web_url", "git_http_url"):
        project_url = str(project.get(key) or "").strip()
        if not project_url:
            continue

        normalized = _normalize_project_url(project_url)
        parsed = urlsplit(normalized)
        project_path = parsed.path.rstrip("/")

        if path_with_namespace and project_path.endswith(f"/{path_with_namespace}"):
            base_path = project_path[: -(len(path_with_namespace) + 1)]
        else:
            parts = [part for part in project_path.split("/") if part]
            base_path = "/" + "/".join(parts[:-2]) if len(parts) > 2 else ""

        return urlunsplit(
            (parsed.scheme, parsed.netloc, _strip_gitlab_suffix(base_path.rstrip("/")), "", "")
        ).rstrip("/")

    return None


def normalize_gitlab_url(
    gitlab_url: Optional[str] = None, project: Optional[Mapping[str, object]] = None
) -> str:
    derived = _derive_base_url_from_project(project)
    if derived:
        return derived

    base_url = (gitlab_url or os.getenv("GITLAB_URL", "https://gitlab.example.com")).rstrip("/")
    parsed = urlsplit(base_url)
    return urlunsplit(
        (parsed.scheme, parsed.netloc, _strip_gitlab_suffix(parsed.path.rstrip("/")), "", "")
    ).rstrip("/")


def extract_noteable_iid(payload: dict) -> Optional[int]:
    attributes = payload.get("object_attributes", {})
    noteable_type = attributes.get("noteable_type")
    noteable_iid = attributes.get("noteable_iid")
    if noteable_iid:
        return noteable_iid
    if noteable_type == "MergeRequest":
        return payload.get("merge_request", {}).get("iid")
    if noteable_type == "Issue":
        return payload.get("issue", {}).get("iid")
    return attributes.get("noteable_id")


def is_self_authored_note(payload: dict, bot_username: str) -> bool:
    normalized_username = bot_username.strip().lstrip("@")
    if not normalized_username:
        return False
    author_username = str(payload.get("user", {}).get("username") or "").strip()
    return author_username == normalized_username


def post_gitlab_note(project_id, noteable_type, noteable_iid, body, project=None):
    """Post a note (comment) to a GitLab issue or MR."""
    gitlab_pat = os.getenv("GITLAB_PAT", "")
    if not gitlab_pat:
        logger.warning("GITLAB_PAT not configured, cannot post note")
        return None

    gitlab_url = normalize_gitlab_url(project=project)
    if noteable_type == "MergeRequest":
        url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{noteable_iid}/notes"
    elif noteable_type == "Issue":
        url = f"{gitlab_url}/api/v4/projects/{project_id}/issues/{noteable_iid}/notes"
    else:
        logger.warning("Unsupported noteable_type: %s", noteable_type)
        return None

    headers = {"PRIVATE-TOKEN": gitlab_pat}
    data = {"body": body}

    logger.debug("Posting note to %s", url)
    resp = None
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=15)
        resp.raise_for_status()
        logger.info("Posted note to %s #%s", noteable_type, noteable_iid)
        return resp.json()
    except Exception as exc:
        logger.error("Failed to post note: %s", exc)
        if resp is not None:
            logger.error("GitLab response: %s", resp.text)
        return None
