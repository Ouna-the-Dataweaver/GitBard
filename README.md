# GitLab AI Code Reviewer

Webhook-driven pipeline system for AI-powered code review on GitLab Merge Requests and Issues.

## Current State

**Pipeline architecture is in place.** The system receives note webhooks, detects slash commands and bot mentions, and replies back into GitLab. Command execution is partially implemented:
- `/oc_review` now uses the real `opencode` CLI path with a dedicated review agent prompt from [`opencode.json`](/mnt/asr_hot/agafonov/repos_2/GitBard/opencode.json).
- `/oc_ask` uses the real `opencode` CLI path with the default agent.
- `/oc_test` uses the same real `opencode` CLI path for ad hoc testing.
- `@nid-bugbard` mention pings now trigger a simple confirmation reply so you can verify delivery end to end.

## Architecture

```
oc_hooks/
├── app.py                      # FastAPI webhook handler (async → sync bridge)
├── src/
│   ├── gitlab_api.py           # Shared GitLab note helpers
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

## Triggers

- `@nid-bugbard` - Replies with a simple "ping received" message to prove webhook delivery works.
- `/oc_review` - Runs the `opencode` CLI with the `gitlab-review` agent defined in `opencode.json`.
- `/oc_ask` - Runs the `opencode` CLI and posts its response back to the thread.
- `/oc_test` - Runs the `opencode` CLI and posts its response back to the thread.

## Running

```bash
uv run python app.py
```

Or with hot reload:

```bash
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8585
```

## Known Issues

### Recursive Webhook Loop

Bot-authored notes are ignored by comparing the webhook `user.username` with `GITLAB_USER`. The older message-prefix hack is still kept in the pipeline stage as a secondary guard.

### OpenCode Agent Integration

`OpencodeIntegrationStage` points `OPENCODE_CONFIG` at this repo’s [`opencode.json`](/mnt/asr_hot/agafonov/repos_2/GitBard/opencode.json) before launching `opencode run` inside the checked out target repository. That lets the webhook app keep its own reusable review agent and prompt while still running against the cloned MR codebase.

## Setup

1. Configure `.env`:
   - `GITLAB_URL` - GitLab instance URL
   - `GITLAB_PAT` - Personal Access Token
   - `GITLAB_USER` - GitLab username that will be mentioned, for example `nid-bugbard`
   - `OPENCODE_MODEL` - OpenCode model id, defaults to `minimax/MiniMax-M2.1`
   - `OPENCODE_AGENT` - OpenCode agent name for general commands, defaults to `Build`
   - `HOST`/`PORT` - Server binding

2. Add webhook in GitLab project:
   - URL: `http://your-server:8585/webhook`
   - Trigger: Comments events

## Testing

```bash
uv run pytest tests/ -v
```

For an ad hoc local smoke test against a running server, use
`scripts/manual_webhook_smoke.py`.
