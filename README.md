# GitLab AI Code Reviewer

Simple webhook service for AI-powered code review on GitLab Merge Requests.

## Features

- Receives GitLab webhook events (MR and comments)
- Built with FastAPI
- Async support for high performance
- Type-safe with Pydantic models
- Health check endpoint

## Prerequisites

- [uv](https://github.com/astral-sh/uv) - Python package manager
- Python 3.11+ (uv will handle this)
- GitLab Personal Access Token with `api` scope

## Setup

1. **Clone and navigate to the project:**
   ```bash
   cd /mnt/asr_hot/agafonov/repos_2/oc_hooks
   ```

2. **Create virtual environment with uv:**
   ```bash
   uv venv
   source .uv/bin/activate  # On Linux/Mac
   # or
   .uv\Scripts\activate     # On Windows
   ```

3. **Install dependencies:**
   ```bash
   uv pip install fastapi uvicorn[standard] pydantic python-dotenv httpx
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your GitLab credentials
   ```
   
   Required variables:
   - `GITLAB_URL` - Your GitLab instance URL
   - `GITLAB_PAT` - Personal Access Token
   - `PORT` - Server port (default: 8585)

## Running

### Development
```bash
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8585
```

### Production
```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8585 --workers 4
```

## Testing

1. **Start the server** (in one terminal)
2. **Run the test script** (in another terminal):
   ```bash
   python test_webhook.py
   ```

3. **Test health endpoint:**
   ```bash
   curl http://localhost:8585/health
   ```

4. **Test webhook manually:**
   ```bash
   curl -X POST http://localhost:8585/webhook \
     -H "Content-Type: application/json" \
     -d '{"object_kind":"merge_request","project":{"name":"test"}}'
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8585/docs
- ReDoc: http://localhost:8585/redoc

## GitLab Webhook Configuration

1. Go to your GitLab project: **Settings → Webhooks**
2. Add a new webhook:
   - **URL**: `http://your-server:8585/webhook`
   - **Secret Token**: (optional) add a secret for verification
   - **Trigger events**:
     - ✅ Merge request events
     - ✅ Comments events
3. Click "Add webhook"

## Project Structure

```
oc_hooks/
├── app.py              # Main FastAPI application
├── models.py           # Pydantic models for webhooks
├── test_webhook.py     # Test script
├── .env                # Environment variables (not in git)
├── .env.example        # Environment template
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── requirements.txt    # Python dependencies (auto-generated)
```

## Development Plan

- [x] Basic webhook receiver
- [x] Health check endpoint
- [ ] GitLab API client (fetch MR diffs, post comments)
- [ ] AI integration (call AI model for code review)
- [ ] Manual trigger via `/ai-review` comment
- [ ] Auto-review on MR open
- [ ] Error handling and logging improvements

## License

MIT
