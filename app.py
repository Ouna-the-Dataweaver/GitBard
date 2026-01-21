from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging
import os
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

        if event_type == "merge_request":
            mr = payload.get("object_attributes", {})
            action = mr.get("action", "unknown")
            mr_iid = mr.get("iid", "unknown")
            logger.info(f"Merge Request event: {action} - MR !{mr_iid}")
        elif event_type == "note":
            note = payload.get("object_attributes", {})
            note_type = note.get("noteable_type", "unknown")
            logger.info(f"Note event on {note_type}")

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
