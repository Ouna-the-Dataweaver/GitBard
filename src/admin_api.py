from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException

from src.opencode_command import opencode_command_args
from src.pipelines.builder import (
    PipelineBuildConfig,
    STAGE_BLOCKS,
    available_stage_ids,
    available_stage_metadata,
    available_step_metadata,
    normalize_preset,
    resolve_stage_ids,
    supported_presets,
)
from src.pipelines.registry import COMMANDS

router = APIRouter(prefix="/api/admin", tags=["admin"])

SUPPORTED_TRIGGER_TYPES = [
    "slash_command",
    "mention",
    "issue_event",
    "merge_request_event",
]
SUPPORTED_SCOPES = ["issue", "merge_request", "both"]
SUPPORTED_PRESETS = list(supported_presets())
_AVAILABLE_STAGE_IDS = set(available_stage_ids())
_REPO_ROOT = Path(__file__).resolve().parents[1]
_OPENCODE_CONFIG_PATH = _REPO_ROOT / "opencode.json"
_ADMIN_SETTINGS_PATH = _REPO_ROOT / ".gitbard_admin_settings.json"
_DEFAULT_MODELS = [
    "minimax/MiniMax-M2.1",
    "openai/gpt-5.4",
    "anthropic/claude-sonnet-4.5",
]
_MODEL_ID_PATTERN = re.compile(r"\b[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.:-]+\b")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return base or "pipeline"


def _default_pipeline_document() -> dict[str, Any]:
    default_stages = list(resolve_stage_ids(PipelineBuildConfig(name="new-pipeline", preset="review")))
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
        "stages": default_stages,
        "stepSettings": _default_step_settings(default_stages),
        "contextHandling": _default_context_handling(default_stages),
        "updatedAt": _utcnow(),
    }


def _default_step_settings(stage_ids: list[str]) -> dict[str, dict[str, Any]]:
    settings: dict[str, dict[str, Any]] = {}
    for stage_id in stage_ids:
        block = STAGE_BLOCKS.get(stage_id)
        if not block:
            continue
        values: dict[str, Any] = {}
        for field in block.config_schema:
            if "default" in field:
                values[str(field["key"])] = field["default"]
        if values:
            settings[stage_id] = values
    return settings


def _default_context_handling(stage_ids: list[str]) -> dict[str, dict[str, Any]]:
    policies: dict[str, dict[str, Any]] = {}
    for stage_id in stage_ids:
        block = STAGE_BLOCKS.get(stage_id)
        if not block:
            continue
        default = block.context_schema.get("default", {})
        if isinstance(default, dict):
            policies[stage_id] = deepcopy(default)
    return policies


def _read_opencode_config() -> dict[str, Any]:
    try:
        return json.loads(_OPENCODE_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _opencode_agent_options() -> list[dict[str, str]]:
    config = _read_opencode_config()
    configured_agents = config.get("agent", {})
    options: list[dict[str, str]] = [
        {
            "name": name,
            "description": str(details.get("description") or ""),
        }
        for name, details in sorted(configured_agents.items())
        if isinstance(details, dict)
    ]
    if not any(option["name"] == "Build" for option in options):
        options.append(
            {
                "name": "Build",
                "description": "OpenCode default build agent.",
            }
        )
    return options


def _opencode_model_options() -> list[dict[str, str]]:
    settings = _read_admin_settings()
    return _selected_model_options(settings)


def _model_option(model: str) -> dict[str, str]:
    return {"name": model, "provider": model.split("/", 1)[0] if "/" in model else ""}


def _default_model_options() -> list[dict[str, str]]:
    return [_model_option(model) for model in _DEFAULT_MODELS]


def _dedupe_model_options(options: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for option in options:
        name = str(option.get("name") or "").strip()
        if not name:
            continue
        deduped[name] = {
            "name": name,
            "provider": str(
                option.get("provider")
                or (name.split("/", 1)[0] if "/" in name else "")
            ),
        }
    return sorted(deduped.values(), key=lambda option: option["name"].lower())


def _read_admin_settings() -> dict[str, Any]:
    try:
        raw_settings = json.loads(_ADMIN_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw_settings = {}
    available = _dedupe_model_options(
        raw_settings.get("available_model_options") or _default_model_options()
    )
    selected = [
        str(model).strip()
        for model in raw_settings.get("selected_models", [])
        if str(model).strip()
    ]
    if not selected:
        selected = [option["name"] for option in available]
    return {
        "available_model_options": available,
        "selected_models": selected,
        "last_model_reload_at": raw_settings.get("last_model_reload_at"),
        "last_model_reload_error": raw_settings.get("last_model_reload_error"),
    }


def _write_admin_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "available_model_options": _dedupe_model_options(
            settings.get("available_model_options") or _default_model_options()
        ),
        "selected_models": [
            str(model).strip()
            for model in settings.get("selected_models", [])
            if str(model).strip()
        ],
        "last_model_reload_at": settings.get("last_model_reload_at"),
        "last_model_reload_error": settings.get("last_model_reload_error"),
    }
    _ADMIN_SETTINGS_PATH.write_text(
        json.dumps(normalized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _read_admin_settings()


def _selected_model_options(settings: dict[str, Any]) -> list[dict[str, str]]:
    selected_names = set(settings.get("selected_models") or [])
    options = [
        option
        for option in settings["available_model_options"]
        if option["name"] in selected_names
    ]
    return options or settings["available_model_options"]


def _parse_opencode_models_output(output: str) -> list[dict[str, str]]:
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        parsed = None

    names: list[str] = []
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                value = item.get("id") or item.get("name") or item.get("model")
                if value:
                    names.append(str(value))
    elif isinstance(parsed, dict):
        for value in parsed.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        names.append(item)
                    elif isinstance(item, dict):
                        model = item.get("id") or item.get("name") or item.get("model")
                        if model:
                            names.append(str(model))

    if not names:
        names = _MODEL_ID_PATTERN.findall(output)

    return _dedupe_model_options([_model_option(name) for name in names])


def _reload_opencode_models() -> dict[str, Any]:
    settings = _read_admin_settings()
    result_settings = deepcopy(settings)
    try:
        result = subprocess.run(
            opencode_command_args("models"),
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result_settings["last_model_reload_at"] = _utcnow()
        result_settings["last_model_reload_error"] = str(exc)
        return _write_admin_settings(result_settings)

    result_settings["last_model_reload_at"] = _utcnow()
    if result.returncode != 0:
        result_settings["last_model_reload_error"] = (
            result.stderr.strip() or result.stdout.strip() or "opencode models failed"
        )
        return _write_admin_settings(result_settings)

    discovered = _parse_opencode_models_output(result.stdout)
    if not discovered:
        result_settings["last_model_reload_error"] = "opencode models returned no model IDs"
        return _write_admin_settings(result_settings)

    previous_selected = set(settings.get("selected_models") or [])
    selected = [
        option["name"]
        for option in discovered
        if option["name"] in previous_selected
    ]
    result_settings.update(
        {
            "available_model_options": discovered,
            "selected_models": selected or [option["name"] for option in discovered],
            "last_model_reload_error": None,
        }
    )
    return _write_admin_settings(result_settings)


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
    payload_has_stages = "stages" in payload
    document = deepcopy(_default_pipeline_document())
    for key, value in payload.items():
        if isinstance(value, dict) and isinstance(document.get(key), dict):
            document[key].update(value)
        else:
            document[key] = value

    document["id"] = _slugify(
        str(document.get("id") or document.get("name") or "pipeline")
    )
    document["preset"] = normalize_preset(
        str(document.get("preset") or document["execution"]["mode"])
    )
    document["execution"]["mode"] = normalize_preset(
        str(document["execution"].get("mode") or document["preset"])
    )
    stage_ids = document.get("stages") if payload_has_stages else None
    if stage_ids is None:
        try:
            stage_ids = list(
                resolve_stage_ids(
                    PipelineBuildConfig(name=document["id"], preset=document["preset"])
                )
            )
        except ValueError:
            stage_ids = []
        document["stages"] = stage_ids
    if isinstance(stage_ids, list):
        payload_step_settings = (
            payload.get("stepSettings") if isinstance(payload.get("stepSettings"), dict) else {}
        )
        payload_context_handling = (
            payload.get("contextHandling")
            if isinstance(payload.get("contextHandling"), dict)
            else {}
        )
        document["stepSettings"] = {
            **_default_step_settings(stage_ids),
            **payload_step_settings,
        }
        document["contextHandling"] = {
            **_default_context_handling(stage_ids),
            **payload_context_handling,
        }
    document["updatedAt"] = _utcnow()
    return document


def _validate_stage_contract(stage_ids: list[str]) -> list[str]:
    errors: list[str] = []
    positions = {stage_id: index for index, stage_id in enumerate(stage_ids)}
    for stage_id in stage_ids:
        block = STAGE_BLOCKS.get(stage_id)
        if not block:
            continue
        index = positions[stage_id]
        for required in block.required_after:
            required_index = positions.get(required)
            if required_index is None:
                errors.append(f"{stage_id} requires {required} before it.")
            elif required_index > index:
                errors.append(f"{stage_id} must run after {required}.")
        for required in block.required_before:
            required_index = positions.get(required)
            if required_index is not None and required_index < index:
                errors.append(f"{stage_id} must run before {required}.")
    return errors


def _validate_step_settings(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    stage_ids = document.get("stages") or []
    step_settings = document.get("stepSettings") or {}
    context_handling = document.get("contextHandling") or {}

    if not isinstance(step_settings, dict):
        return ["stepSettings must be an object keyed by stage ID."]
    if not isinstance(context_handling, dict):
        return ["contextHandling must be an object keyed by stage ID."]

    known_stage_ids = set(stage_ids)
    for stage_id in step_settings:
        if stage_id not in known_stage_ids:
            errors.append(f"stepSettings contains non-pipeline step: {stage_id}")
    for stage_id, policy in context_handling.items():
        if stage_id not in known_stage_ids:
            errors.append(f"contextHandling contains non-pipeline step: {stage_id}")
            continue
        if not isinstance(policy, dict):
            errors.append(f"contextHandling for {stage_id} must be an object.")
            continue
        for key in ("passToNext", "writeToWorkspace"):
            if key in policy and not isinstance(policy[key], bool):
                errors.append(f"contextHandling.{stage_id}.{key} must be a boolean.")

    return errors


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

    custom_stages = document.get("stages")
    if custom_stages is not None:
        if not isinstance(custom_stages, list):
            errors.append("stages must be a list of stage IDs.")
        elif len(custom_stages) == 0:
            errors.append("stages cannot be empty.")
        else:
            unknown = [s for s in custom_stages if s not in _AVAILABLE_STAGE_IDS]
            if unknown:
                errors.append(f"Unknown stage(s): {', '.join(unknown)}")
            duplicate_ids = {s for s in custom_stages if custom_stages.count(s) > 1}
            if duplicate_ids:
                errors.append(f"Duplicate stage(s): {', '.join(sorted(duplicate_ids))}")
            if not unknown and not duplicate_ids:
                errors.extend(_validate_stage_contract(custom_stages))

    errors.extend(_validate_step_settings(document))

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
        and "WorkspacePreparationStage" not in (document.get("stages") or [])
    ):
        warnings.append(
            "OpenCode preparation is enabled, but the pipeline does not include the preparation step."
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
    custom_stages = document.get("stages")
    stage_ids = tuple(custom_stages) if isinstance(custom_stages, list) else None
    step_settings = document.get("stepSettings") or {}
    execution = document.get("execution", {})
    step_settings = {
        **step_settings,
        "OpencodeIntegrationStage": {
            "agentName": execution.get("agentName"),
            "modelName": execution.get("modelName"),
            **(step_settings.get("OpencodeIntegrationStage") or {}),
        },
    }
    try:
        stages = list(
            resolve_stage_ids(
                PipelineBuildConfig(
                    name=document["id"],
                    preset=preset,
                    stage_ids=stage_ids,
                    step_configs=step_settings,
                    context_policies=document.get("contextHandling") or {},
                )
            )
        )
    except ValueError:
        stages = []
    trigger = document.get("trigger", {})
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
        "stepSettings": {
            stage_id: step_settings.get(stage_id, {}) for stage_id in stages
        },
        "contextHandling": {
            stage_id: (document.get("contextHandling") or {}).get(stage_id, {})
            for stage_id in stages
        },
    }


def _get_pipeline_or_404(pipeline_id: str) -> dict[str, Any]:
    document = _PIPELINES.get(pipeline_id)
    if not document:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return document


@router.get("/metadata")
def get_metadata() -> dict[str, Any]:
    agent_options = _opencode_agent_options()
    model_options = _opencode_model_options()
    return {
        "trigger_types": SUPPORTED_TRIGGER_TYPES,
        "scopes": SUPPORTED_SCOPES,
        "pipeline_presets": SUPPORTED_PRESETS,
        "agents": [option["name"] for option in agent_options],
        "agent_options": agent_options,
        "models": [option["name"] for option in model_options],
        "model_options": model_options,
        "workspace_modes": ["fresh_clone"],
        "checkout_strategies": ["source_branch", "explicit_ref"],
        "output_post_modes": ["new_note", "update_progress_note"],
        "available_stages": available_stage_metadata(),
        "available_steps": available_step_metadata(),
    }


@router.get("/settings/opencode")
def get_opencode_settings() -> dict[str, Any]:
    return _read_admin_settings()


@router.put("/settings/opencode")
def update_opencode_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = _read_admin_settings()
    available = _dedupe_model_options(
        payload.get("available_model_options") or current["available_model_options"]
    )
    available_names = {option["name"] for option in available}
    selected = [
        str(model).strip()
        for model in payload.get("selected_models", current["selected_models"])
        if str(model).strip()
    ]
    selected = [model for model in selected if model in available_names]
    if not selected:
        raise HTTPException(
            status_code=422,
            detail={"errors": ["At least one visible model must be selected."]},
        )
    return _write_admin_settings(
        {
            **current,
            "available_model_options": available,
            "selected_models": selected,
            "last_model_reload_error": current.get("last_model_reload_error"),
        }
    )


@router.post("/settings/opencode/reload-models")
def reload_opencode_models() -> dict[str, Any]:
    return _reload_opencode_models()


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
