from fastapi.testclient import TestClient

from app import app


client = TestClient(app)


def test_admin_metadata_endpoint():
    response = client.get("/api/admin/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "trigger_types" in data
    assert "pipeline_presets" in data


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


def test_admin_preview_with_custom_stages():
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
    assert data["valid"] is True
    assert data["compiled_pipeline"]["stages"] == [
        "HookResolverStage",
        "SnapshotResolverStage",
        "NoteUpdaterStage",
    ]


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
