from src.pipelines.base import AgentResult, PipelineContext
from src.pipelines.stages.note_updater import NoteUpdaterStage


def test_note_updater_updates_existing_progress_note(monkeypatch):
    updated = []
    posted = []

    def fake_update(
        project_id, noteable_type, noteable_iid, note_id, body, project=None
    ):
        updated.append((project_id, noteable_type, noteable_iid, note_id, body))
        return {"id": note_id}

    def fake_post(project_id, noteable_type, noteable_iid, body, project=None):
        posted.append((project_id, noteable_type, noteable_iid, body))
        return {"id": 100}

    monkeypatch.setattr(
        "src.pipelines.stages.note_updater.update_gitlab_note", fake_update
    )
    monkeypatch.setattr("src.pipelines.stages.note_updater.post_gitlab_note", fake_post)

    context = PipelineContext(
        webhook_payload={
            "project": {"id": 123},
            "object_attributes": {
                "noteable_type": "MergeRequest",
                "noteable_iid": 7,
            },
        },
        gitlab_note_id=99,
        agent_result=AgentResult(content="done"),
        metadata={"noteable_type": "MergeRequest"},
    )

    result = NoteUpdaterStage().execute(context)

    assert result.success
    assert posted == []
    assert updated == [
        (
            123,
            "MergeRequest",
            7,
            99,
            "🤖 **OpenCode Results**\n\ndone",
        )
    ]


def test_note_updater_includes_collapsed_agent_steps(monkeypatch):
    updated = []

    def fake_update(
        project_id, noteable_type, noteable_iid, note_id, body, project=None
    ):
        updated.append(body)
        return {"id": note_id}

    monkeypatch.setattr(
        "src.pipelines.stages.note_updater.update_gitlab_note", fake_update
    )

    context = PipelineContext(
        webhook_payload={
            "project": {"id": 1},
            "object_attributes": {
                "noteable_type": "MergeRequest",
                "noteable_iid": 2,
            },
        },
        agent_result=AgentResult(content="done"),
        gitlab_note_id=9,
        metadata={
            "noteable_type": "MergeRequest",
            "agent_steps": ["✅ `read` — src/app.py"],
        },
    )

    result = NoteUpdaterStage().execute(context)

    assert result.success
    assert "🤖 **OpenCode Results**\n\ndone" in updated[0]
    assert "<summary>Agent steps (1)</summary>" in updated[0]
    assert "✅ `read` — src/app.py" in updated[0]
