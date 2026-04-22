from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any

from fastapi import APIRouter, HTTPException

from src.pipelines.registry import COMMANDS

router = APIRouter(prefix="/api/admin", tags=["admin"])

PIPELINE_PRESET_STAGES = {
    "review": [
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    ],
    "ask": [
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    ],
    "test": [
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    ],
    "deep_test": [
        "HookResolverStage",
        "SnapshotResolverStage",
        "WorkspaceAcquisitionStage",
        "IssueContextFetcherStage",
        "WorkspacePreparationStage",
        "OpencodeIntegrationStage",
        "NoteUpdaterStage",
    ],
}

SUPPORTED_TRIGGER_TYPES = [
    "slash_command",
    "mention",
    "issue_event",
    "merge_request_event",
]
SUPPORTED_SCOPES = ["issue", "merge_request", "both"]
SUPPORTED_PRESETS = list(PIPELINE_PRESET_STAGES.keys())


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return base or "pipeline"


def _default_pipeline_document() -> dict[str, Any]:
    return {
        "id": "new-pipeline",
        "name": "New Pipeline",
        "enabled": True,
        "description": "",
        "preset": "review",
        "trigger": {
            "type": "slash_command",
            "scope": "merge_request",
            "commandText": "/oc_review",
            "mentionTarget": "@nid-bugbard",
        },
        "filters": {
            "projectAllowlist": [],
            "branchPatterns": [],
            "labelFilters": [],
            "authorAllowlist": [],
            "authorDenylist": [],
        },
        "execution": {
            "mode": "review",
            "agentName": "gitlab-review",
            "modelName": "minimax/MiniMax-M2.1",
            "questionTemplate": "{{note_body_without_trigger}}",
            "timeoutSeconds": 1800,
            "maxConcurrentRuns": 1,
        },
        "workspace": {
            "mode": "fresh_clone",
            "cleanupAfterRun": True,
            "checkoutStrategy": "source_branch",
        },
        "preparation": {
            "enableRepoHook": False,
            "enableOpencodePreparation": False,
            "allowDependencyInstall": False,
        },
        "output": {
            "postMode": "new_note",
            "includeArtifactsInNote": True,
            "keepEventsJsonl": True,
            "keepRenderedReplyMarkdown": True,
        },
        "updatedAt": _utcnow(),
    }


def _seed_pipelines() -> dict[str, dict[str, Any]]:
    now = _utcnow()
    return {
        cmd.admin_document_id(): cmd.to_admin_document(now_iso=now) for cmd in COMMANDS
    }


_PIPELINES: dict[str, dict[str, Any]] = _seed_pipelines()


def _pipeline_summary(document: dict[str, Any]) -> dict[str, Any]:
    trigger = document.get("trigger", {})
    execution = document.get("execution", {})
    return {
        "id": document["id"],
        "name": document["name"],
        "enabled": document.get("enabled", True),
        "description": document.get("description", ""),
        "triggerType": trigger.get("type"),
        "triggerText": trigger.get("commandText") or trigger.get("mentionTarget") or "",
        "scope": trigger.get("scope"),
        "preset": document.get("preset") or execution.get("mode"),
        "updatedAt": document.get("updatedAt"),
    }


def _coerce_pipeline_document(payload: dict[str, Any]) -> dict[str, Any]:
    document = deepcopy(_default_pipeline_document())
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(document.get(key), dict):
            document[key].update(value)
        else:
            document[key] = value

    document["id"] = _slugify(
        str(document.get("id") or document.get("name") or "pipeline")
    )
    document["preset"] = str(document.get("preset") or document["execution"]["mode"])
    document["execution"]["mode"] = str(
        document["execution"].get("mode") or document["preset"]
    )
    document["updatedAt"] = _utcnow()
    return document


def _validate_pipeline(
    payload: dict[str, Any],
    *,
    existing_id: str | None = None,
) -> dict[str, Any]:
    document = _coerce_pipeline_document(payload)
    errors: list[str] = []
    warnings: list[str] = []

    if document["preset"] not in SUPPORTED_PRESETS:
        errors.append(f"Unsupported preset: {document['preset']}")

    trigger = document["trigger"]
    trigger_type = trigger.get("type")
    if trigger_type not in SUPPORTED_TRIGGER_TYPES:
        errors.append(f"Unsupported trigger type: {trigger_type}")

    scope = trigger.get("scope")
    if scope not in SUPPORTED_SCOPES:
        errors.append(f"Unsupported scope: {scope}")

    if (
        trigger_type == "slash_command"
        and not str(trigger.get("commandText") or "").strip()
    ):
        errors.append("Slash command triggers require command text.")

    if (
        trigger_type == "mention"
        and not str(trigger.get("mentionTarget") or "").strip()
    ):
        errors.append("Mention triggers require a bot mention target.")

    if document["preset"] == "review" and scope not in {"merge_request", "both"}:
        errors.append("Review pipelines must target merge request scope.")

    if (
        document["preparation"].get("enableOpencodePreparation")
        and document["preset"] != "deep_test"
    ):
        warnings.append(
            "OpenCode preparation is enabled, but the selected preset does not currently include the preparation route."
        )

    if document["preparation"].get("enableRepoHook") and document["workspace"].get(
        "cleanupAfterRun"
    ):
        warnings.append(
            "Workspace cleanup is enabled, so hook-generated artifacts may only exist during the run."
        )

    duplicate_command = str(trigger.get("commandText") or "").strip()
    if duplicate_command:
        for pipeline_id, pipeline in _PIPELINES.items():
            if pipeline_id == existing_id:
                continue
            other_command = str(
                pipeline.get("trigger", {}).get("commandText") or ""
            ).strip()
            if other_command and other_command == duplicate_command:
                errors.append(
                    f"{duplicate_command} is already used by pipeline {pipeline_id}."
                )
                break

    return {
        "valid": not errors,
        "normalized": document,
        "errors": errors,
        "warnings": warnings,
    }


def _compile_preview(document: dict[str, Any]) -> dict[str, Any]:
    preset = str(document.get("preset") or document.get("execution", {}).get("mode"))
    stages = PIPELINE_PRESET_STAGES.get(preset, [])
    trigger = document.get("trigger", {})
    execution = document.get("execution", {})
    return {
        "name": document["id"],
        "preset": preset,
        "trigger": {
            "type": trigger.get("type"),
            "scope": trigger.get("scope"),
            "text": trigger.get("commandText") or trigger.get("mentionTarget") or "",
        },
        "agent": execution.get("agentName"),
        "model": execution.get("modelName"),
        "stages": stages,
    }


def _get_pipeline_or_404(pipeline_id: str) -> dict[str, Any]:
    document = _PIPELINES.get(pipeline_id)
    if not document:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return document


@router.get("/metadata")
def get_metadata() -> dict[str, Any]:
    return {
        "trigger_types": SUPPORTED_TRIGGER_TYPES,
        "scopes": SUPPORTED_SCOPES,
        "pipeline_presets": SUPPORTED_PRESETS,
        "agents": ["gitlab-review", "gitlab-prepare", "Build"],
        "models": [
            "minimax/MiniMax-M2.1",
            "openai/gpt-5.4",
            "anthropic/claude-sonnet-4.5",
        ],
        "workspace_modes": ["fresh_clone"],
        "checkout_strategies": ["source_branch", "explicit_ref"],
        "output_post_modes": ["new_note", "update_progress_note"],
    }


@router.get("/pipelines")
def list_pipelines() -> dict[str, Any]:
    summaries = [_pipeline_summary(pipeline) for pipeline in _PIPELINES.values()]
    summaries.sort(key=lambda item: item["name"].lower())
    return {"pipelines": summaries}


@router.post("/pipelines")
def create_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    validation = _validate_pipeline(payload)
    document = validation["normalized"]
    if document["id"] in _PIPELINES:
        validation["errors"].append(f"Pipeline {document['id']} already exists.")
        validation["valid"] = False
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail=validation)

    _PIPELINES[document["id"]] = document
    return document


@router.get("/pipelines/{pipeline_id}")
def get_pipeline(pipeline_id: str) -> dict[str, Any]:
    return deepcopy(_get_pipeline_or_404(pipeline_id))


@router.put("/pipelines/{pipeline_id}")
def replace_pipeline(pipeline_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _get_pipeline_or_404(pipeline_id)
    validation = _validate_pipeline(payload, existing_id=pipeline_id)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail=validation)

    document = validation["normalized"]
    if document["id"] != pipeline_id and document["id"] in _PIPELINES:
        raise HTTPException(
            status_code=422,
            detail={"errors": [f"Pipeline {document['id']} already exists."]},
        )

    _PIPELINES.pop(pipeline_id, None)
    _PIPELINES[document["id"]] = document
    return document


@router.patch("/pipelines/{pipeline_id}")
def patch_pipeline(pipeline_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    current = deepcopy(_get_pipeline_or_404(pipeline_id))
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            current[key].update(value)
        else:
            current[key] = value

    validation = _validate_pipeline(current, existing_id=pipeline_id)
    if not validation["valid"]:
        raise HTTPException(status_code=422, detail=validation)

    document = validation["normalized"]
    _PIPELINES.pop(pipeline_id, None)
    _PIPELINES[document["id"]] = document
    return document


@router.delete("/pipelines/{pipeline_id}")
def delete_pipeline(pipeline_id: str) -> dict[str, Any]:
    _get_pipeline_or_404(pipeline_id)
    _PIPELINES.pop(pipeline_id, None)
    return {"status": "deleted", "pipeline_id": pipeline_id}


@router.post("/pipelines/validate")
def validate_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    return _validate_pipeline(payload, existing_id=payload.get("id"))


@router.post("/pipelines/preview")
def preview_pipeline(payload: dict[str, Any]) -> dict[str, Any]:
    validation = _validate_pipeline(payload, existing_id=payload.get("id"))
    return {
        **validation,
        "compiled_pipeline": _compile_preview(validation["normalized"]),
    }
