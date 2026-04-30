# GitBard

Webhook-driven pipeline system for running OpenCode agents from GitLab issue and merge request comments.

## What It Does

GitBard receives GitLab note webhooks, detects supported slash commands or bot mentions, checks out the target repository state, runs an OpenCode-backed pipeline, and posts the result back to GitLab.

Supported triggers:

- `@nid-bugbard` on a merge request - runs the review pipeline.
- `@nid-bugbard` on non-MR notes - replies with a lightweight delivery check.
- `/oc_review` - runs the `gitlab-review` agent from `opencode.json`.
- `/oc_ask` - runs OpenCode and posts the answer back to the thread.
- `/oc_test` - runs OpenCode for ad hoc testing.
- `/oc_deeptest` - runs repository preparation before the main OpenCode pass.

## Layout

```text
.
├── app.py                         # FastAPI webhook service
├── src/
│   ├── admin_api.py               # Admin UI API and local admin settings
│   ├── gitlab_api.py              # GitLab note helpers
│   └── pipelines/
│       ├── base.py                # Pipeline primitives
│       ├── builder.py             # Declarative pipeline builder
│       ├── registry.py            # Command detection
│       ├── commands/              # Command definitions
│       └── stages/                # Pipeline stage implementations
├── prompts/                       # OpenCode agent prompts
├── scripts/                       # Manual smoke-test helpers
├── tests/                         # Python test suite
└── ui/                            # Vite admin frontend
```

## Configuration

Copy the example environment and fill in the local values:

```bash
cp .env.example .env
```

Required settings:

- `GITLAB_URL` - GitLab instance URL.
- `GITLAB_PAT` - token used to read GitLab data and post notes.
- `GITLAB_USER` - bot username without `@`.

Optional settings:

- `OPENCODE_MODEL` - default model for OpenCode stages.
- `OPENCODE_AGENT` - default OpenCode agent for general commands.
- `HOST` and `PORT` - FastAPI bind address.

The admin UI writes local OpenCode model picker state to `.gitbard_admin_settings.json`. That file is ignored because it is machine-local runtime state. Use `.gitbard_admin_settings.example.json` as the committed example shape.

`opencode.json` is committed intentionally. It defines the repo-local OpenCode agents and command wiring used by the pipelines.

## Running

Start the backend:

```bash
uv run python app.py
```

Or run with hot reload:

```bash
uv run uvicorn app:app --reload --host 0.0.0.0 --port 8585
```

Build the admin frontend when you want FastAPI to serve `/admin` from `ui/dist`:

```bash
cd ui
npm install
npm run build
```

For frontend development, run the Vite dev server from `ui/`.

## GitLab Webhook

Add a project webhook in GitLab:

- URL: `http://your-server:8585/webhook`
- Trigger: comments events

Bot-authored notes are ignored by comparing the webhook `user.username` with `GITLAB_USER`. A message-prefix guard is also kept in the note updater as a secondary loop protection.

## OpenCode Runtime

`OpencodeIntegrationStage` sets `OPENCODE_CONFIG` to this repo's `opencode.json` before launching `opencode run` inside the checked-out target repository. Set `OPENCODE_COMMAND` to use a wrapper or alternate binary, for example `OPENCODE_COMMAND=opencode-safe`.

Preparation-enabled pipelines run the optional repo-root `.gitbard.sh` hook first, then a `gitlab-prepare` OpenCode pass. Generated runtime artifacts such as `opencode_prep_report.md`, `opencode_prep_events.jsonl`, `opencode_reply.md`, and `opencode_events.jsonl` are ignored.

## Testing

Run the Python tests:

```bash
uv run pytest tests/ -v
```

For an ad hoc local smoke test against a running server:

```bash
uv run python scripts/manual_webhook_smoke.py
```
