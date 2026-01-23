# GitLab AI Code Reviewer

Webhook-driven pipeline system for AI-powered code review on GitLab Merge Requests and Issues.

## Current State

**Pipeline architecture is in place.** The system receives webhooks, detects commands (`/oc_review`, `/oc_ask`, `/oc_test`), and executes multi-stage pipelines. However, **OpenCode agent integration is not yet implemented** - the `AgentExecutorStage` currently returns placeholder results.

## Architecture

```
oc_hooks/
├── app.py                      # FastAPI webhook handler (async → sync bridge)
├── src/
│   ├── app_old.py              # Original app (for post_gitlab_note helper)
│   └── pipelines/
│       ├── base.py             # Pipeline, Stage, Context, Result classes
│       ├── registry.py         # Command detection and pipeline factory
│       ├── stages/
│       │   ├── hook_resolver.py    # Detect commands, post "started" note
│       │   ├── snapshot_resolver.py # Resolve SHA/branch from MR
│       │   ├── context_builder.py   # Clone repo to temp directory
│       │   ├── agent_executor.py    # TODO: Run OpenCode agent
│       │   └── note_updater.py      # Post results or errors
│       └── commands/
│           ├── base.py         # Command base class
│           ├── oc_review.py    # /oc_review pipeline
│           ├── oc_ask.py       # /oc_ask pipeline
│           └── oc_test.py      # /oc_test pipeline
└── tests/                      # Unit tests (13 passing)
```

## Commands

- `/oc_review` - Review code in the merge request
- `/oc_ask` - Answer questions about the code
- `/oc_test` - Run tests or analyze test coverage

## Running

```bash
uv run python app.py
```

Or with hot reload:

```bash
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8585
```

## Known Issues

### Recursive Webhook Loop (Hack Fix)

**Problem:** When the bot posts a note with results, GitLab sends another webhook event, triggering the pipeline again → infinite loop.

**Current Hack Fix:** The `HookResolverStage` filters out notes starting with "🤖 OpenCode".

**Real Fix (TODO):** When using a dedicated bot account, filter by `user_id` instead of message content. This requires:
1. A GitLab bot account with its own PAT
2. Checking `payload.get("user_id")` against the bot's user ID
3. Removing the "🤖 OpenCode" string check

### OpenCode Agent Integration

The `AgentExecutorStage` (`src/pipelines/stages/agent_executor.py`) currently returns placeholder results:

```python
result = AgentResult(
    content=f"Agent result for {self.agent_type}: {prompt[:100]}...",
    format="markdown",
)
```

This needs to be replaced with actual OpenCode agent invocation.

## Setup

1. Configure `.env`:
   - `GITLAB_URL` - GitLab instance URL
   - `GITLAB_PAT` - Personal Access Token
   - `HOST`/`PORT` - Server binding

2. Add webhook in GitLab project:
   - URL: `http://your-server:8585/webhook`
   - Trigger: Comments events

## Testing

```bash
uv run pytest tests/ -v
```
