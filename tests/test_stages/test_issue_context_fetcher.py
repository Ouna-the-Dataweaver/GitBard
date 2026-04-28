from src.pipelines.base import PipelineContext
from src.pipelines.stages.issue_context_fetcher import IssueContextFetcherStage


class FakeResponse:
    def __init__(self, url: str, text: str = "<html>not json</html>"):
        self.url = url
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        raise ValueError("not json")


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload
        self.text = ""

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_issue_context_fetcher_uses_noteable_iid_and_skips_non_json(monkeypatch, tmp_path):
    payload = {
        "project": {
            "id": 2679,
            "web_url": "https://gitlab.example.com/group/repo",
            "path_with_namespace": "group/repo",
        },
        "object_attributes": {
            "noteable_type": "Issue",
            "noteable_iid": 223,
            "noteable_id": 999,
        },
    }
    context = PipelineContext(
        webhook_payload=payload,
        local_context_path=str(tmp_path),
        metadata={"noteable_type": "Issue"},
    )
    stage = IssueContextFetcherStage()
    called_urls = []

    monkeypatch.setenv("GITLAB_PAT", "test-token")
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/group/repo")

    def fake_get(url, headers, timeout):
        called_urls.append(url)
        return FakeResponse(url)

    monkeypatch.setattr("src.pipelines.stages.issue_context_fetcher.requests.get", fake_get)

    result = stage.execute(context)

    assert not result.should_stop
    assert called_urls == [
        "https://gitlab.example.com/api/v4/projects/2679/issues/223",
        "https://gitlab.example.com/api/v4/projects/2679/issues/223/notes",
    ]
    assert "thread_context_path" not in context.metadata


def test_issue_context_fetcher_writes_merge_request_context(monkeypatch, tmp_path):
    payload = {
        "project": {
            "id": 2679,
            "web_url": "https://gitlab.example.com/group/repo",
            "path_with_namespace": "group/repo",
        },
        "object_attributes": {
            "noteable_type": "MergeRequest",
            "noteable_iid": 77,
        },
    }
    context = PipelineContext(
        webhook_payload=payload,
        local_context_path=str(tmp_path),
        metadata={"noteable_type": "MergeRequest"},
    )
    stage = IssueContextFetcherStage()

    monkeypatch.setenv("GITLAB_PAT", "test-token")
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/group/repo")

    responses = {
        "https://gitlab.example.com/api/v4/projects/2679/merge_requests/77": JsonResponse(
            {
                "title": "Add db changes",
                "state": "opened",
                "source_branch": "db",
                "target_branch": "main",
                "description": "Implements db updates.",
                "web_url": "https://gitlab.example.com/group/repo/-/merge_requests/77",
            }
        ),
        "https://gitlab.example.com/api/v4/projects/2679/merge_requests/77/notes": JsonResponse(
            [
                {
                    "author": {"name": "Alice"},
                    "created_at": "2026-03-31T10:00:00Z",
                    "body": "/oc_test Summarize this MR and do a small review, please?",
                }
            ]
        ),
        "https://gitlab.example.com/api/v4/projects/2679/merge_requests/77/changes": JsonResponse(
            {
                "changes": [
                    {
                        "old_path": "app.py",
                        "new_path": "app.py",
                        "diff": "@@ -1 +1 @@\n-old\n+new",
                    }
                ]
            }
        ),
    }

    def fake_get(url, headers, timeout):
        return responses[url]

    monkeypatch.setattr("src.pipelines.stages.issue_context_fetcher.requests.get", fake_get)

    result = stage.execute(context)

    assert not result.should_stop
    thread_context_path = context.metadata["thread_context_path"]
    with open(thread_context_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "# GitLab Merge Request Context" in content
    assert "Branches: db -> main" in content
    assert "## Changes" in content
    assert "```diff" in content


def test_issue_context_fetcher_can_pass_context_without_file(monkeypatch, tmp_path):
    payload = {
        "project": {
            "id": 2679,
            "web_url": "https://gitlab.example.com/group/repo",
            "path_with_namespace": "group/repo",
        },
        "object_attributes": {
            "noteable_type": "Issue",
            "noteable_iid": 223,
        },
    }
    context = PipelineContext(
        webhook_payload=payload,
        local_context_path=str(tmp_path),
        metadata={"noteable_type": "Issue"},
    )
    stage = IssueContextFetcherStage(write_to_workspace=False, pass_to_next=True)

    monkeypatch.setenv("GITLAB_PAT", "test-token")
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/group/repo")

    responses = {
        "https://gitlab.example.com/api/v4/projects/2679/issues/223": JsonResponse(
            {
                "title": "Bug",
                "state": "opened",
                "description": "Something broke.",
            }
        ),
        "https://gitlab.example.com/api/v4/projects/2679/issues/223/notes": JsonResponse(
            []
        ),
    }

    def fake_get(url, headers, timeout):
        return responses[url]

    monkeypatch.setattr("src.pipelines.stages.issue_context_fetcher.requests.get", fake_get)

    result = stage.execute(context)

    assert not result.should_stop
    assert "thread_context_path" not in context.metadata
    assert "# GitLab Issue Context" in context.metadata["thread_context_content"]
