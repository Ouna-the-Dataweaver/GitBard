from fastapi.testclient import TestClient

import src.admin_api as admin_api
from app import app


client = TestClient(app)


def test_admin_metadata_endpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(admin_api, "_ADMIN_SETTINGS_PATH", tmp_path / "settings.json")
    response = client.get("/api/admin/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "trigger_types" in data
    assert "pipeline_presets" in data
    assert "gitlab-review" in data["agents"]
    assert any(
        option["name"] == "gitlab-review"
        and "Reviews merge requests" in option["description"]
        for option in data["agent_options"]
    )
    assert any(option["name"] == "Build" for option in data["agent_options"])
    assert any(option["name"] == "minimax/MiniMax-M2.1" for option in data["model_options"])
    assert any(
        step["id"] == "OpencodeIntegrationStage"
        and step["provider"] == "opencode"
        and any(field["key"] == "modelName" for field in step["configSchema"])
        for step in data["available_steps"]
    )


def test_opencode_settings_controls_visible_models(tmp_path, monkeypatch):
    monkeypatch.setattr(admin_api, "_ADMIN_SETTINGS_PATH", tmp_path / "settings.json")

    response = client.put(
        "/api/admin/settings/opencode",
        json={
            "available_model_options": [
                {"name": "openai/gpt-5.4", "provider": "openai"},
                {"name": "anthropic/claude-sonnet-4.5", "provider": "anthropic"},
            ],
            "selected_models": ["openai/gpt-5.4"],
        },
    )
    assert response.status_code == 200

    metadata = client.get("/api/admin/metadata").json()
    assert metadata["models"] == ["openai/gpt-5.4"]
    assert metadata["model_options"] == [
        {"name": "openai/gpt-5.4", "provider": "openai"}
    ]


def test_opencode_settings_reload_models(tmp_path, monkeypatch):
    monkeypatch.setattr(admin_api, "_ADMIN_SETTINGS_PATH", tmp_path / "settings.json")

    class FakeCompletedProcess:
        returncode = 0
        stdout = "openai/gpt-5.4\nanthropic/claude-sonnet-4.5\n"
        stderr = ""

    def fake_run(*args, **kwargs):
        assert args[0] == ["opencode", "models"]
        return FakeCompletedProcess()

    monkeypatch.setattr(admin_api.subprocess, "run", fake_run)
    response = client.post("/api/admin/settings/opencode/reload-models")
    assert response.status_code == 200
    data = response.json()
    assert data["last_model_reload_error"] is None
    assert {option["name"] for option in data["available_model_options"]} == {
        "openai/gpt-5.4",
        "anthropic/claude-sonnet-4.5",
    }


def test_admin_pipelines_endpoint_returns_seeded_data():
    response = client.get("/api/admin/pipelines")
    assert response.status_code == 200
    data = response.json()
    assert len(data["pipelines"]) >= 2
    assert any(item["id"] == "oc-review" for item in data["pipelines"])


def test_admin_preview_endpoint_compiles_pipeline():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "custom-review",
            "name": "Custom Review",
            "preset": "review",
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/custom_review",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "WorkspaceAcquisitionStage" in data["compiled_pipeline"]["stages"]


def test_admin_preview_rejects_broken_custom_stage_contract():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "custom-stages",
            "name": "Custom Stages",
            "preset": "review",
            "stages": [
                "HookResolverStage",
                "SnapshotResolverStage",
                "NoteUpdaterStage",
            ],
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/custom_stages",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any(
        "NoteUpdaterStage requires OpencodeIntegrationStage before it" in error
        for error in data["errors"]
    )


def test_admin_preview_with_context_and_step_settings():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "configured-steps",
            "name": "Configured Steps",
            "preset": "review",
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/configured_steps",
            },
            "stepSettings": {
                "OpencodeIntegrationStage": {
                    "agentName": "gitlab-review",
                    "modelName": "openai/gpt-5.4",
                },
                "IssueContextFetcherStage": {
                    "filename": "mr_context.md",
                },
            },
            "contextHandling": {
                "IssueContextFetcherStage": {
                    "passToNext": True,
                    "writeToWorkspace": True,
                    "filename": "mr_context.md",
                }
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert (
        data["compiled_pipeline"]["stepSettings"]["OpencodeIntegrationStage"][
            "modelName"
        ]
        == "openai/gpt-5.4"
    )
    assert (
        data["compiled_pipeline"]["contextHandling"]["IssueContextFetcherStage"][
            "filename"
        ]
        == "mr_context.md"
    )


def test_admin_preview_rejects_unknown_stage():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "bad-stage",
            "name": "Bad Stage",
            "preset": "review",
            "stages": ["HookResolverStage", "FakeStage"],
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/bad_stage",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any("Unknown stage(s): FakeStage" in e for e in data["errors"])


def test_admin_preview_rejects_duplicate_stages():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "dup-stage",
            "name": "Dup Stage",
            "preset": "review",
            "stages": [
                "HookResolverStage",
                "HookResolverStage",
            ],
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/dup_stage",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any("Duplicate stage(s): HookResolverStage" in e for e in data["errors"])


def test_admin_preview_rejects_empty_stages():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "empty-stage",
            "name": "Empty Stage",
            "preset": "review",
            "stages": [],
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/empty_stage",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert any("stages cannot be empty" in e for e in data["errors"])


def test_admin_preview_fallback_to_preset_stages():
    response = client.post(
        "/api/admin/pipelines/preview",
        json={
            "id": "preset-fallback",
            "name": "Preset Fallback",
            "preset": "deep_test",
            "trigger": {
                "type": "slash_command",
                "scope": "merge_request",
                "commandText": "/deep_test",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "WorkspacePreparationStage" in data["compiled_pipeline"]["stages"]


def test_admin_ui_route_has_fallback_shell():
    response = client.get("/admin")
    assert response.status_code == 200
    assert "GitBard Admin UI" in response.text
