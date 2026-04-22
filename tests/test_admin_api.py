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


def test_admin_ui_route_has_fallback_shell():
    response = client.get("/admin")
    assert response.status_code == 200
    assert "GitBard Admin UI" in response.text
