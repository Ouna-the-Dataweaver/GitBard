from src.gitlab_api import normalize_gitlab_url


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
