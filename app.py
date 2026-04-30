import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.gitlab_api import (
    extract_noteable_iid,
    is_self_authored_note,
    post_gitlab_note,
)
from src.admin_api import router as admin_router
from src.pipelines.commands.oc_review import ReviewCommand
from src.pipelines.registry import contains_user_mention, detect_command

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitLab AI Code Reviewer",
    description="Webhook service for AI-powered code review on GitLab MRs",
    version="0.1.0",
)

GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.example.com")
GITLAB_PAT = os.getenv("GITLAB_PAT", "")
GITLAB_USER = os.getenv("GITLAB_USER", "").strip().lstrip("@")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8585"))
BASE_DIR = Path(__file__).resolve().parent
UI_DIST_DIR = BASE_DIR / "ui" / "dist"
UI_ASSETS_DIR = UI_DIST_DIR / "assets"

app.include_router(admin_router)

if UI_ASSETS_DIR.exists():
    app.mount("/admin/assets", StaticFiles(directory=str(UI_ASSETS_DIR)), name="admin-assets")


def _preview_text(value: str, *, limit: int = 160) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _webhook_log_fields(request: Request, payload: dict) -> dict[str, object]:
    attrs = payload.get("object_attributes", {})
    project = payload.get("project", {})
    user = payload.get("user", {})
    return {
        "path": request.url.path,
        "gitlab_event": request.headers.get("x-gitlab-event", ""),
        "has_gitlab_token": bool(request.headers.get("x-gitlab-token")),
        "object_kind": payload.get("object_kind"),
        "noteable_type": attrs.get("noteable_type"),
        "project_id": project.get("id"),
        "project_path": project.get("path_with_namespace") or project.get("web_url"),
        "user": user.get("username") or user.get("name"),
        "note_id": attrs.get("id"),
        "note_preview": _preview_text(str(attrs.get("note") or "")),
    }


def build_mention_reply(bot_username: str) -> str:
    mention = f"@{bot_username}" if bot_username else "the bot"
    return (
        f"Ping received. Mention delivery works and I saw {mention}.\n\n"
        "Context-aware answers are not wired yet, but the webhook can already reply to mentions."
    )


async def _run_detected_command(
    payload: dict,
    command_name: str,
    command,
    trigger_text: str | None = None,
    display_trigger: str | None = None,
) -> JSONResponse:
    from src.pipelines.base import PipelineContext
    import asyncio

    context = PipelineContext(webhook_payload=payload)
    if trigger_text:
        context.command = command_name
        context.metadata["noteable_type"] = payload.get("object_attributes", {}).get(
            "noteable_type"
        )
        context.metadata["note_body"] = payload.get("object_attributes", {}).get(
            "note", ""
        )
        context.metadata["trigger_pattern"] = trigger_text
        if display_trigger:
            context.metadata["display_trigger"] = display_trigger

    pipeline = command.get_pipeline()
    logger.info(
        "Dispatching pipeline command=%s trigger=%s display_trigger=%s pipeline=%s",
        command_name,
        trigger_text or getattr(command, "trigger_pattern", ""),
        display_trigger or "",
        pipeline.name,
    )
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, pipeline.execute, context)

    if result.success:
        logger.info(
            "Pipeline completed command=%s pipeline=%s", command_name, pipeline.name
        )
        return JSONResponse({"status": "completed", "command": command_name})

    logger.error(
        "Pipeline failed command=%s pipeline=%s error=%s",
        command_name,
        pipeline.name,
        result.error,
    )
    return JSONResponse({"status": "error", "error": str(result.error)}, status_code=500)


def _post_mention_reply(payload: dict) -> JSONResponse:
    project_id = payload.get("project", {}).get("id")
    noteable_type = payload.get("object_attributes", {}).get("noteable_type")
    noteable_iid = extract_noteable_iid(payload)
    note_response = post_gitlab_note(
        project_id,
        noteable_type,
        noteable_iid,
        build_mention_reply(GITLAB_USER),
        project=payload.get("project"),
    )
    if note_response:
        return JSONResponse({"status": "completed", "trigger": "mention"})

    return JSONResponse(
        {"status": "error", "message": "Failed to post mention reply"},
        status_code=502,
    )


async def _run_mention_review(payload: dict) -> JSONResponse:
    mention = f"@{GITLAB_USER}" if GITLAB_USER else "@bot"
    review_command = ReviewCommand()
    return await _run_detected_command(
        payload,
        review_command.name,
        review_command,
        trigger_text=mention,
        display_trigger=review_command.trigger_pattern,
    )


def _admin_fallback_html() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>GitBard Admin UI</title>
    <style>
      body {
        font-family: sans-serif;
        margin: 0;
        padding: 32px;
        background: #111827;
        color: #f9fafb;
      }
      .panel {
        max-width: 720px;
        margin: 0 auto;
        padding: 24px;
        border-radius: 16px;
        background: #1f2937;
        border: 1px solid #374151;
      }
      code {
        background: #111827;
        padding: 2px 6px;
        border-radius: 6px;
      }
      a { color: #93c5fd; }
    </style>
  </head>
  <body>
    <div class="panel">
      <h1>Admin UI build not found</h1>
      <p>The TypeScript frontend has been scaffolded under <code>ui/</code>, but the production bundle is not built yet.</p>
      <p>Run <code>cd ui && npm install && npm run build</code> to serve the built UI from FastAPI, or <code>npm run dev</code> for frontend development.</p>
      <p>The placeholder admin API is already available at <a href="/api/admin/metadata">/api/admin/metadata</a>.</p>
    </div>
  </body>
</html>
""".strip()


@app.get("/admin")
@app.get("/admin/{full_path:path}")
async def admin_ui(full_path: str = ""):
    index_path = UI_DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(_admin_fallback_html())


@app.get("/")
async def root():
    """Redirect root to webhook endpoint"""
    return RedirectResponse(url="/webhook")


@app.post("/")
async def root_post(request: Request):
    """Handle POST requests to root - redirect to webhook"""
    return await gitlab_webhook(request)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "gitlab-ai-reviewer",
        "gitlab_url": GITLAB_URL,
        "gitlab_user": GITLAB_USER,
    }


@app.post("/webhook")
async def gitlab_webhook(request: Request):
    """Receive GitLab webhook events - async, then triggers sync pipeline"""
    try:
        logger.info(
            "GitLab webhook request arrived path=%s gitlab_event=%s has_gitlab_token=%s content_type=%s",
            request.url.path,
            request.headers.get("x-gitlab-event", ""),
            bool(request.headers.get("x-gitlab-token")),
            request.headers.get("content-type", ""),
        )
        payload = await request.json()
        log_fields = _webhook_log_fields(request, payload)
        logger.info("GitLab webhook received: %s", log_fields)

        event_type = payload.get("object_kind")
        if event_type != "note":
            logger.info(
                "Ignoring webhook: unsupported object_kind=%s gitlab_event=%s project_id=%s",
                event_type,
                log_fields["gitlab_event"],
                log_fields["project_id"],
            )
            return JSONResponse({"status": "ignored"})

        note = payload.get("object_attributes", {}).get("note", "")
        if is_self_authored_note(payload, GITLAB_USER):
            logger.info(
                "Ignoring webhook note: self-authored user=%s project_id=%s noteable_type=%s note_preview=%r",
                GITLAB_USER,
                log_fields["project_id"],
                log_fields["noteable_type"],
                log_fields["note_preview"],
            )
            return JSONResponse({"status": "ignored", "reason": "self_note"})

        command = detect_command(note)
        if command:
            logger.info(
                "Detected slash command command=%s trigger=%s project_id=%s noteable_type=%s note_preview=%r",
                command.name,
                command.trigger_pattern,
                log_fields["project_id"],
                log_fields["noteable_type"],
                log_fields["note_preview"],
            )
            return await _run_detected_command(payload, command.name, command)

        if contains_user_mention(note, GITLAB_USER):
            noteable_type = payload.get("object_attributes", {}).get("noteable_type")
            logger.info(
                "Detected bot mention user=@%s project_id=%s noteable_type=%s note_preview=%r",
                GITLAB_USER,
                log_fields["project_id"],
                noteable_type,
                log_fields["note_preview"],
            )
            if noteable_type == "MergeRequest":
                return await _run_mention_review(payload)
            return _post_mention_reply(payload)

        logger.info(
            "Ignoring webhook note: no supported trigger project_id=%s noteable_type=%s configured_user=@%s note_preview=%r",
            log_fields["project_id"],
            log_fields["noteable_type"],
            GITLAB_USER,
            log_fields["note_preview"],
        )
        return JSONResponse({"status": "ignored"})

    except Exception as exc:
        logger.exception("Error processing webhook")
        return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
