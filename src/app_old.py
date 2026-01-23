from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
import logging
import os
import requests
from dotenv import load_dotenv

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
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8585"))


def post_gitlab_note(project_id, noteable_type, noteable_iid, body):
    """Post a note (comment) to a GitLab issue or MR"""
    if not GITLAB_PAT:
        logger.warning("GITLAB_PAT not configured, cannot post note")
        return None

    gitlab_url = GITLAB_URL.rstrip("/")
    if "/api/" in gitlab_url:
        gitlab_url = gitlab_url.split("/api/")[0]
    elif "/-" in gitlab_url:
        gitlab_url = gitlab_url.split("/-")[0]

    if noteable_type == "MergeRequest":
        url = f"{gitlab_url}/api/v4/projects/{project_id}/merge_requests/{noteable_iid}/notes"
    elif noteable_type == "Issue":
        url = f"{gitlab_url}/api/v4/projects/{project_id}/issues/{noteable_iid}/notes"
    else:
        logger.warning(f"Unsupported noteable_type: {noteable_type}")
        return None

    headers = {"PRIVATE-TOKEN": GITLAB_PAT}
    data = {"body": body}

    logger.debug(f"Posting note to {url}")
    resp = None
    try:
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        logger.info(f"Posted note to {noteable_type} #{noteable_iid}: {body}")
        return resp.json()
    except Exception as e:
        logger.error(f"Failed to post note: {e}")
        if resp is not None:
            logger.error(f"GitLab response: {resp.text}")
        return None


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
    }


@app.post("/webhook")
async def gitlab_webhook(request: Request):
    """Receive GitLab webhook events"""
    try:
        payload = await request.json()

        event_type = payload.get("object_kind")
        project = payload.get("project", {})
        project_name = project.get("name", "unknown")

        logger.info(f"Received webhook: {event_type} from project '{project_name}'")
        logger.debug(f"Full payload: {payload}")

        if event_type == "merge_request":
            mr = payload.get("object_attributes", {})
            action = mr.get("action", "unknown")
            mr_iid = mr.get("iid", "unknown")
            logger.info(f"Merge Request event: {action} - MR !{mr_iid}")
        elif event_type == "note":
            note = payload.get("object_attributes", {})
            note_type = note.get("noteable_type", "unknown")
            note_content = note.get("note", "")
            logger.info(f"Note event on {note_type}")
            logger.info(f"Note payload keys: {list(note.keys())}")

            if "/oc_test" in note_content:
                logger.info("Detected /oc_test command in note")
                project_id = project.get("id")
                noteable_iid = None
                if note_type == "MergeRequest":
                    noteable_iid = payload.get("merge_request", {}).get("iid")
                elif note_type == "Issue":
                    noteable_iid = payload.get("issue", {}).get("iid")
                if noteable_iid is None:
                    noteable_iid = note.get("noteable_id")

                logger.info(
                    "Project ID: %s, noteable_iid: %s", project_id, noteable_iid
                )
                post_gitlab_note(
                    project_id, note_type, noteable_iid, "test hook triggered"
                )

        return JSONResponse(
            {"status": "received", "event_type": event_type, "project": project_name}
        )

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
