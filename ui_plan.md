# Pipeline UI Plan

## Goal

Add a GUI for configuring how GitLab issues or merge requests trigger OpenCode-driven pipelines, without forcing users to edit Python classes or raw config files.

The UI should let users:

- create and edit pipeline definitions
- choose triggers such as slash commands, mentions, issue events, or merge request events
- configure workspace and preparation behavior
- choose which OpenCode agent/model to run
- preview the effective config before saving
- test a pipeline definition against sample GitLab webhook payloads

The UI should not initially expose arbitrary internal stage composition. The current backend is stage-based, but that is an implementation detail. Users should edit a higher-level declarative config that the backend compiles into the existing Python pipeline objects.

## Recommended Product Shape

Start with a constrained "pipeline editor", not a generic visual workflow builder.

That means:

- users edit named pipelines
- each pipeline has a trigger block
- each pipeline has a behavior block
- the backend maps that config to known stage sequences

This avoids turning the first version into a no-code engine. Your current codebase is not there yet, and you do not need it.

## What Should Be Configurable

Expose these fields in the UI:

### Identity

- pipeline name
- enabled or disabled
- description

### Trigger

- trigger type: `slash_command`, `mention`, `issue_event`, `merge_request_event`
- scope: `issue`, `merge_request`, or `both`
- command text, for example `/oc_review`
- bot mention target, for example `@nid-bugbard`
- optional filters:
  - project allowlist
  - branch patterns
  - label filters
  - author allowlist or denylist

### Execution

- agent name
- model name
- question template
- working mode: review, ask, test, deep test
- timeout seconds
- max concurrent runs

### Workspace

- workspace mode: `fresh_clone` initially
- cleanup after run
- checkout source branch vs explicit ref

### Preparation

- enable repo hook
- enable OpenCode preparation pass
- allow dependency install during prep

### Output

- note posting mode: new note vs update progress note
- include artifacts in note
- keep events JSONL
- keep rendered reply markdown

## What Should Not Be Configurable Yet

Keep these internal for v1:

- arbitrary stage ordering
- arbitrary shell stages
- custom Python expressions
- free-form graph editing
- credentials and secrets management beyond selecting named secret references

If you expose all of that immediately, you will just move the suffering from YAML or Python into a worse GUI.

## Backend Refactor Needed First

Right now command definitions are code:

- [`src/pipelines/registry.py`](/mnt/asr_hot/agafonov/repos_2/GitBard/src/pipelines/registry.py)
- [`src/pipelines/commands/oc_review.py`](/mnt/asr_hot/agafonov/repos_2/GitBard/src/pipelines/commands/oc_review.py)
- [`src/pipelines/commands/oc_deeptest.py`](/mnt/asr_hot/agafonov/repos_2/GitBard/src/pipelines/commands/oc_deeptest.py)

To support a UI, add a declarative config layer:

1. UI edits pipeline definitions in JSON stored on disk or in SQLite.
2. Backend validates those definitions.
3. Backend compiles a definition into a concrete `Pipeline`.
4. Runtime execution still uses the existing stage classes.

That gives you a stable editing model without rewriting the execution engine.

## Suggested Config Model

Use a versioned config object.

```json
{
  "version": 1,
  "pipelines": [
    {
      "id": "oc_review",
      "name": "Review Merge Requests",
      "enabled": true,
      "description": "Run review agent on merge request notes.",
      "trigger": {
        "type": "slash_command",
        "pattern": "/oc_review",
        "scope": ["merge_request"]
      },
      "filters": {
        "projects": [],
        "target_branches": [],
        "labels_any": [],
        "authors_excluded": []
      },
      "workspace": {
        "mode": "fresh_clone",
        "cleanup_required": true
      },
      "preparation": {
        "repo_hook": false,
        "opencode_prepare": false
      },
      "agent": {
        "name": "gitlab-review",
        "model": "minimax/MiniMax-M2.1",
        "question_template": "{{note_body_without_trigger}}"
      },
      "output": {
        "post_mode": "new_note",
        "persist_events": true,
        "persist_reply": true
      },
      "limits": {
        "timeout_seconds": 1800,
        "max_concurrency": 1
      }
    }
  ]
}
```

## Compilation Rules

The backend should compile config into stage sequences using a small set of presets.

Example mapping:

- `review`
  - `HookResolverStage`
  - `SnapshotResolverStage`
  - `WorkspaceAcquisitionStage`
  - `IssueContextFetcherStage`
  - `OpencodeIntegrationStage`
  - `NoteUpdaterStage`

- `deep_test`
  - `HookResolverStage`
  - `SnapshotResolverStage`
  - `WorkspaceAcquisitionStage`
  - `IssueContextFetcherStage`
  - `WorkspacePreparationStage`
  - `OpencodeIntegrationStage`
  - `NoteUpdaterStage`

Instead of letting users drag stages around, let them toggle options that select one of these backend-approved shapes.

## Suggested API

Add a small admin API under `/api/admin`.

### Pipeline CRUD

`GET /api/admin/pipelines`

- returns summary list for the table view

`POST /api/admin/pipelines`

- creates a pipeline

`GET /api/admin/pipelines/{pipeline_id}`

- returns full editable pipeline document

`PUT /api/admin/pipelines/{pipeline_id}`

- updates the full pipeline document

`PATCH /api/admin/pipelines/{pipeline_id}`

- partial updates for quick toggles

`DELETE /api/admin/pipelines/{pipeline_id}`

- deletes or archives pipeline definition

### Validation and Preview

`POST /api/admin/pipelines/validate`

- request body: pipeline draft
- response: normalized config plus validation errors and warnings

`POST /api/admin/pipelines/preview`

- request body: pipeline draft
- response: compiled runtime plan

Example response:

```json
{
  "valid": true,
  "compiled_pipeline": {
    "name": "oc_review",
    "stages": [
      "HookResolverStage",
      "SnapshotResolverStage",
      "WorkspaceAcquisitionStage",
      "IssueContextFetcherStage",
      "OpencodeIntegrationStage",
      "NoteUpdaterStage"
    ]
  },
  "warnings": [
    "This pipeline only applies to merge requests."
  ]
}
```

### Test Harness

`POST /api/admin/pipelines/test-match`

- request body:
  - pipeline draft
  - sample webhook payload
- response:
  - whether it matches
  - extracted trigger data
  - rejected reason if it does not match

`POST /api/admin/pipelines/test-run`

- optional later endpoint
- runs against a sample payload in dry-run mode without posting to GitLab

### Metadata for Forms

`GET /api/admin/metadata`

- supported trigger types
- supported scopes
- supported pipeline presets
- available OpenCode agents from `opencode.json`
- model defaults

Example response:

```json
{
  "trigger_types": ["slash_command", "mention", "issue_event", "merge_request_event"],
  "scopes": ["issue", "merge_request"],
  "pipeline_presets": ["review", "ask", "test", "deep_test"],
  "agents": ["gitlab-prepare", "gitlab-review"]
}
```

## UI Structure

The UI can be very small.

### 1. Pipeline List

Columns:

- name
- trigger
- scope
- preset
- enabled
- last edited

Actions:

- create
- duplicate
- disable
- test
- edit

### 2. Pipeline Editor

Tabs or sections:

- Basics
- Trigger
- Execution
- Workspace
- Preparation
- Output
- Validation Preview

The right side should always show a generated summary:

- effective trigger rule
- effective stage plan
- risk or warning messages

### 3. Test Drawer

Allow the user to paste:

- a GitLab note payload
- an issue payload
- a merge request payload

Then show:

- matched pipeline or no match
- extracted command text
- final prompt preview
- runtime stages that would execute

## UX Guidance

The main design principle should be "safe by default, inspectable when needed".

Good patterns:

- sensible defaults
- inline validation
- preview before save
- duplication from existing pipeline
- advanced settings hidden by default

Bad patterns:

- giant JSON textarea as the main editor
- exposing backend class names as the primary user language
- drag-and-drop workflow graphs for v1

## Storage Choice

For this app, either of these is reasonable:

### Option A: JSON file on disk

Good if:

- single-instance deployment
- config changes are rare
- you want easy backup and git tracking

Recommended file:

- `config/pipelines.json`

### Option B: SQLite

Good if:

- multiple admins edit config
- you want change history later
- you want draft vs published versions

My default recommendation here is JSON first, SQLite later if the product grows.

## Validation Rules

Backend validation should enforce:

- unique pipeline id
- unique slash command pattern
- mention triggers require bot username compatibility
- merge request review pipelines require merge request scope
- `opencode_prepare` implies preparation preset support
- agent names must exist in `opencode.json`

Return both errors and warnings.

Example:

- error: "`/oc_review` is already used by pipeline `review-default`"
- warning: "Preparation is enabled but workspace cleanup is also enabled, artifacts may not persist"

## Implementation Plan

### Phase 1

- add versioned pipeline config schema
- load pipelines from config instead of hardcoded registry list
- compile config into existing pipeline objects
- add validation service

### Phase 2

- add admin API
- add metadata endpoint
- add preview and test-match endpoints

### Phase 3

- build the UI
- support clone, enable or disable, edit, validate, preview

### Phase 4

- add audit log
- add draft vs published
- add dry-run execution

## Framework Recommendation

You do not need Next.js.

Next.js would be justified if you needed:

- public SEO pages
- complex client-side routing across many screens
- server actions tightly coupled to the frontend
- a broader product surface than one admin console

For this app, you are building an internal configuration UI around a FastAPI backend. That is a small admin surface.

### Best Fit

I would choose one of these:

1. FastAPI server-rendered pages plus a little `htmx` or `Alpine.js`
2. plain TypeScript with Vite and a few small components
3. a light component model such as `Lit` if you want reusable widgets without React

### What I Would Not Choose

- Next.js for v1
- a full SPA if the UI is mostly forms and previews
- React unless the editor becomes deeply interactive

## How Heavy React or Next.js Is

### Plain TypeScript

Pros:

- smallest mental model
- minimal bundle
- very direct control
- good for forms, tables, and a small settings app

Cons:

- you build your own state management patterns
- complex editor interactions get messy faster
- long-term consistency depends on discipline

### React

Pros:

- easier to structure larger interactive forms
- huge ecosystem
- easier component reuse

Cons:

- more tooling
- more build complexity
- more framework ceremony than this app obviously needs today

### Next.js

Pros:

- strong full-stack conventions
- good if frontend is the product

Cons:

- heaviest option here
- brings routing, rendering modes, and deployment concerns you do not need
- poor trade if this is just an internal admin tool

## Bottom Line

For this specific app, I would start with:

- FastAPI backend
- JSON-backed pipeline config
- small admin API
- UI built either as server-rendered HTML with `htmx`, or a very small Vite plus TypeScript frontend

I would only move to React if the editor evolves into something like:

- multi-step visual builders
- reusable complex forms across many entities
- live graph editing
- deep optimistic client-side state

That threshold is real, but you are not there yet.
