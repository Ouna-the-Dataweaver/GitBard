from src.gitlab_api import normalize_gitlab_url, update_gitlab_note


def test_normalize_gitlab_url_uses_project_web_url_for_project_scoped_env(monkeypatch):
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/group/repo")

    project = {
        "web_url": "https://gitlab.example.com/group/repo",
        "path_with_namespace": "group/repo",
    }

    assert normalize_gitlab_url(project=project) == "https://gitlab.example.com"


def test_normalize_gitlab_url_preserves_relative_root_from_project_metadata(monkeypatch):
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com/group/repo")

    project = {
        "web_url": "https://gitlab.example.com/gitlab/group/repo",
        "path_with_namespace": "group/repo",
    }

    assert normalize_gitlab_url(project=project) == "https://gitlab.example.com/gitlab"


def test_update_gitlab_note_uses_existing_note_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"id": 99}

    def fake_put(url, headers, json, timeout):
        calls.append((url, headers, json, timeout))
        return FakeResponse()

    monkeypatch.setenv("GITLAB_PAT", "secret")
    monkeypatch.setenv("GITLAB_URL", "https://gitlab.example.com")
    monkeypatch.setattr("src.gitlab_api.requests.put", fake_put)

    response = update_gitlab_note(123, "MergeRequest", 7, 99, "body")

    assert response == {"id": 99}
    assert calls == [
        (
            "https://gitlab.example.com/api/v4/projects/123/merge_requests/7/notes/99",
            {"PRIVATE-TOKEN": "secret"},
            {"body": "body"},
            15,
        )
    ]
