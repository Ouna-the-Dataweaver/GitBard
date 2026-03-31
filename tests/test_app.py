from fastapi.testclient import TestClient

import app


client = TestClient(app.app)


def test_health_includes_gitlab_user():
    response = client.get("/health")

    assert response.status_code == 200
    assert "gitlab_user" in response.json()


def test_webhook_replies_to_bot_mention(monkeypatch):
    payload = {
        "object_kind": "note",
        "user": {"username": "alice"},
        "project": {"id": 1},
        "merge_request": {"iid": 42},
        "object_attributes": {
            "note": "hello @nid-bugbard can you see this?",
            "noteable_type": "MergeRequest",
            "noteable_iid": 42,
        },
    }

    monkeypatch.setattr(app, "GITLAB_USER", "nid-bugbard")

    captured = {}

    def fake_post(project_id, noteable_type, noteable_iid, body, project=None):
        captured["project_id"] = project_id
        captured["noteable_type"] = noteable_type
        captured["noteable_iid"] = noteable_iid
        captured["body"] = body
        captured["project"] = project
        return {"id": 99}

    monkeypatch.setattr(app, "post_gitlab_note", fake_post)

    response = client.post("/webhook", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "completed", "trigger": "mention"}
    assert captured["project_id"] == 1
    assert captured["noteable_type"] == "MergeRequest"
    assert captured["noteable_iid"] == 42
    assert captured["project"] == {"id": 1}
    assert "Ping received" in captured["body"]


def test_webhook_ignores_self_authored_note(monkeypatch):
    payload = {
        "object_kind": "note",
        "user": {"username": "nid-bugbard"},
        "project": {"id": 1},
        "object_attributes": {
            "note": "@nid-bugbard checking loop prevention",
            "noteable_type": "Issue",
            "noteable_iid": 7,
        },
    }

    monkeypatch.setattr(app, "GITLAB_USER", "nid-bugbard")

    response = client.post("/webhook", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "reason": "self_note"}
