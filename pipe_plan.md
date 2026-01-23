# Pipeline Architecture Plan for oc_hooks

## Overview
Flexible webhook-driven pipeline system with async webhook reception triggering synchronous multi-stage processing pipelines based on detected commands.

## Requirements
- **Initial stage**: Async webhook receiver
- **Pipeline execution**: Fully synchronous after initial async stage
- **State persistence**: Skipped
- **Timeouts**: Skipped
- **Logging**: Error logs and basic logging
- **Configuration**: Pure Python
- **Testing**: Unit tests
- **Monitoring**: Logging only

## Architecture

### Design Patterns
1. **Pipeline Pattern**: Sequential stage execution
2. **Strategy Pattern**: Different pipelines per command
3. **Factory Pattern**: Pipeline creation based on webhook content

### File Structure
```
oc_hooks/
├── app.py                      # Existing FastAPI app
├── models.py                   # Existing Pydantic models
├── pipelines/                  # NEW: Pipeline system
│   ├── __init__.py
│   ├── base.py                 # Pipeline, Stage, Context, Result base classes
│   ├── stages/                 # Stage implementations
│   │   ├── __init__.py
│   │   ├── hook_resolver.py    # Stage A: Detect commands
│   │   ├── snapshot_resolver.py  # Stage B: Get code state (SHA/branch)
│   │   ├── context_builder.py  # Stage C: Build local repo context
│   │   ├── agent_executor.py   # Stage D: Run AI agent
│   │   └── note_updater.py     # Update initial note with results
│   ├── commands/               # Command registry
│   │   ├── __init__.py
│   │   ├── base.py             # Command base class
│   │   ├── oc_review.py        # Review command pipeline
│   │   ├── oc_ask.py           # Ask command pipeline
│   │   └── oc_test.py          # Test command pipeline
│   └── registry.py             # Pipeline factory/registry
├── tests/                      # NEW: Unit tests
│   ├── __init__.py
│   ├── test_pipeline_base.py
│   ├── test_stages/
│   │   ├── __init__.py
│   │   ├── test_hook_resolver.py
│   │   ├── test_snapshot_resolver.py
│   │   └── test_context_builder.py
│   └── test_commands/
│       ├── __init__.py
│       └── test_oc_review.py
└── pipe_plan.md                # This plan document
```

## Core Components

### 1. Pipeline Context (`pipelines/base.py`)
```python
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class PipelineContext:
    """Shared context passed through all pipeline stages"""
    webhook_payload: Dict[str, Any]
    command: Optional[str] = None
    project_info: Optional[Dict[str, Any]] = None
    code_snapshot: Optional[Dict[str, Any]] = None  # SHA, branch info
    local_context_path: Optional[str] = None
    agent_result: Optional[AgentResult] = None
    gitlab_note_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2. Stage Result (`pipelines/base.py`)
```python
@dataclass
class StageResult:
    """Result returned by each stage"""
    context: PipelineContext
    should_stop: bool = False
    error: Optional[Exception] = None
    success: bool = True

@dataclass
class AgentResult:
    """Structured result from agent execution"""
    content: str
    format: str = "markdown"  # markdown, json, html, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 3. Stage Base (`pipelines/base.py`)
```python
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class Stage(ABC):
    """Base class for all pipeline stages"""

    def execute(self, context: PipelineContext) -> StageResult:
        """Execute stage - synchronous"""
        try:
            logger.info(f"Executing stage: {self.__class__.__name__}")
            result = self._execute(context)
            logger.info(f"Completed stage: {self.__class__.__name__}")
            return result
        except Exception as e:
            logger.error(f"Stage {self.__class__.__name__} failed: {e}", exc_info=True)
            return StageResult(context=context, should_stop=True, error=e, success=False)

    @abstractmethod
    def _execute(self, context: PipelineContext) -> StageResult:
        """Actual implementation of stage logic"""
        pass
```

### 4. Pipeline Class (`pipelines/base.py`)
```python
from typing import List

class Pipeline:
    """Pipeline executes stages sequentially"""

    def __init__(self, name: str, stages: List[Stage]):
        self.name = name
        self.stages = stages

    def execute(self, context: PipelineContext) -> StageResult:
        """Execute all stages until completion or stop"""
        logger.info(f"Starting pipeline: {self.name}")

        try:
            for stage in self.stages:
                result = stage.execute(context)
                context = result.context

                if result.should_stop:
                    if result.error:
                        context.metadata["pipeline_error"] = str(result.error)
                        logger.error(f"Pipeline {self.name} stopped with error: {result.error}")
                    else:
                        logger.info(f"Pipeline {self.name} stopped early")
                    return result

            logger.info(f"Pipeline {self.name} completed successfully")
            return StageResult(context=context, should_stop=False, success=True)
        finally:
            # Cleanup: remove temp directories if context builder was used
            for attr_name in ["local_context_path"]:
                path = getattr(context, attr_name, None)
                if path:
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
```

### 5. Command Base (`pipelines/commands/base.py`)
```python
from abc import ABC, abstractmethod
from pipelines.base import Pipeline

class Command(ABC):
    """Base class for all commands"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (e.g., 'oc_review')"""
        pass

    @property
    @abstractmethod
    def trigger_pattern(self) -> str:
        """Pattern to detect command in webhook (e.g., '/oc_review')"""
        pass

    @abstractmethod
    def get_pipeline(self) -> Pipeline:
        """Return the pipeline for this command"""
        pass
```

## Stage Implementations

### Stage A: Hook Resolver (`pipelines/stages/hook_resolver.py`)
```python
from pipelines.base import Stage, StageResult, PipelineContext

class HookResolverStage(Stage):
    """Stage A: Detect commands from webhook and create initial note"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload

        # Only process note events
        if payload.get("object_kind") != "note":
            return StageResult(context=context, should_stop=True)

        note = payload.get("object_attributes", {}).get("note", "")
        noteable_type = payload.get("object_attributes", {}).get("noteable_type")

        # Detect command
        from pipelines.registry import detect_command
        command = detect_command(note)

        if not command:
            logger.info(f"No command detected in note: {note}")
            return StageResult(context=context, should_stop=True)

        context.command = command.name
        context.metadata["noteable_type"] = noteable_type

        # Post "started working" note
        from app import post_gitlab_note
        project_id = payload.get("project", {}).get("id")
        noteable_iid = self._get_noteable_iid(payload)

        note_response = post_gitlab_note(
            project_id,
            noteable_type,
            noteable_iid,
            f"🤖 OpenCode started working on `{command.trigger_pattern}`..."
        )

        if note_response:
            context.gitlab_note_id = note_response.get("id")

        return StageResult(context=context, should_stop=False)

    def _get_noteable_iid(self, payload: dict) -> int:
        """Extract noteable_iid from payload"""
        noteable_type = payload.get("object_attributes", {}).get("noteable_type")
        if noteable_type == "MergeRequest":
            return payload.get("merge_request", {}).get("iid")
        elif noteable_type == "Issue":
            return payload.get("issue", {}).get("iid")
        return payload.get("object_attributes", {}).get("noteable_id")
```

### Stage B: Snapshot Resolver (`pipelines/stages/snapshot_resolver.py`)
```python
from pipelines.base import Stage, StageResult, PipelineContext

class SnapshotResolverStage(Stage):
    """Stage B: Resolve code snapshot (SHA/branch)"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        noteable_type = context.metadata.get("noteable_type")

        snapshot = {}

        if noteable_type == "MergeRequest":
            # MR has SHA directly
            mr = payload.get("merge_request", {})
            snapshot["sha"] = mr.get("diff_refs", {}).get("head_sha")
            snapshot["source_branch"] = mr.get("source_branch")
            snapshot["target_branch"] = mr.get("target_branch")
        elif noteable_type == "Issue":
            # Issue needs branch resolution from command or default
            # For now, default to main
            snapshot["sha"] = None  # Will resolve in next stage
            snapshot["branch"] = "main"  # Default, could be from command args

        context.code_snapshot = snapshot
        logger.info(f"Resolved code snapshot: {snapshot}")

        return StageResult(context=context, should_stop=False)
```

### Stage C: Context Builder (`pipelines/stages/context_builder.py`)
```python
from pipelines.base import Stage, StageResult, PipelineContext
import os
import tempfile
import shutil

class ContextBuilderStage(Stage):
    """Stage C: Build local directory with resolved repo state"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        project = payload.get("project", {})

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="opencode_")
        context.local_context_path = temp_dir

        # Clone repository
        git_http_url = project.get("git_http_url")
        if not git_http_url:
            raise ValueError("No git_http_url in project")

        # Clone with auth (from env)
        from subprocess import run
        gitlab_url = os.getenv("GITLAB_URL", "")
        gitlab_pat = os.getenv("GITLAB_PAT", "")

        # Build authenticated URL
        auth_url = git_http_url.replace("https://", f"https://gitlab:{gitlab_pat}@")

        run(["git", "clone", auth_url, temp_dir], check=True, capture_output=True)

        # Checkout appropriate state
        if context.code_snapshot.get("sha"):
            run(["git", "checkout", context.code_snapshot["sha"]],
                cwd=temp_dir, check=True, capture_output=True)
        elif context.code_snapshot.get("branch"):
            run(["git", "checkout", context.code_snapshot["branch"]],
                cwd=temp_dir, check=True, capture_output=True)

        logger.info(f"Built local context at: {temp_dir}")

        return StageResult(context=context, should_stop=False)

    def cleanup(self, context: PipelineContext):
        """Clean up temp directory"""
        if context.local_context_path:
            shutil.rmtree(context.local_context_path, ignore_errors=True)
```

### Stage D: Agent Executor (`pipelines/stages/agent_executor.py`)
```python
from pipelines.base import Stage, StageResult, PipelineContext, AgentResult

class AgentExecutorStage(Stage):
    """Stage D: Run OpenCode agent with appropriate prompt"""

    def __init__(self, agent_type: str):
        self.agent_type = agent_type

    def _execute(self, context: PipelineContext) -> StageResult:
        # Build prompt based on agent type
        if self.agent_type == "review":
            prompt = self._build_review_prompt(context)
        elif self.agent_type == "general":
            prompt = self._build_general_prompt(context)
        else:
            prompt = self._build_generic_prompt(context)

        # TODO: Integrate with actual OpenCode agent
        # For now, placeholder
        result = AgentResult(
            content=f"Agent result for {self.agent_type}: {prompt[:100]}...",
            format="markdown",
            metadata={"agent_type": self.agent_type}
        )
        context.agent_result = result

        logger.info(f"Agent {self.agent_type} executed")

        return StageResult(context=context, should_stop=False)

    def _build_review_prompt(self, context: PipelineContext) -> str:
        """Build prompt for code review"""
        return f"Review the code in {context.local_context_path}"

    def _build_general_prompt(self, context: PipelineContext) -> str:
        """Build prompt for general questions"""
        return f"Answer questions about the code in {context.local_context_path}"

    def _build_generic_prompt(self, context: PipelineContext) -> str:
        """Build generic prompt"""
        return "Analyze the code"
```

### Note Updater Stage (`pipelines/stages/note_updater.py`)
```python
from pipelines.base import Stage, StageResult, PipelineContext

class NoteUpdaterStage(Stage):
    """Update the initial note with agent results or error notification"""

    def _execute(self, context: PipelineContext) -> StageResult:
        payload = context.webhook_payload
        project_id = payload.get("project", {}).get("id")
        noteable_type = context.metadata.get("noteable_type")
        noteable_iid = self._get_noteable_iid(payload)

        # Check if previous stage reported an error
        if context.metadata.get("pipeline_error"):
            from app import post_gitlab_note
            error_msg = context.metadata.get("pipeline_error", "Unknown error")
            post_gitlab_note(
                project_id,
                noteable_type,
                noteable_iid,
                f"❌ **OpenCode Error**\n\nPipeline failed: {error_msg}"
            )
            logger.info("Updated note with error notification")
            return StageResult(context=context, should_stop=False)

        # Normal success case - use AgentResult content
        from app import post_gitlab_note
        result = context.agent_result
        content = result.content if result else "No results generated"

        post_gitlab_note(
            project_id,
            noteable_type,
            noteable_iid,
            f"🤖 **OpenCode Results**\n\n{content}"
        )

        logger.info("Updated note with agent results")

        return StageResult(context=context, should_stop=False)

    def _get_noteable_iid(self, payload: dict) -> int:
        noteable_type = payload.get("object_attributes", {}).get("noteable_type")
        if noteable_type == "MergeRequest":
            return payload.get("merge_request", {}).get("iid")
        elif noteable_type == "Issue":
            return payload.get("issue", {}).get("iid")
        return payload.get("object_attributes", {}).get("noteable_id")
```

## Command Implementations

### Review Command (`pipelines/commands/oc_review.py`)
```python
from pipelines.base import Pipeline
from pipelines.commands.base import Command
from pipelines.stages.hook_resolver import HookResolverStage
from pipelines.stages.snapshot_resolver import SnapshotResolverStage
from pipelines.stages.context_builder import ContextBuilderStage
from pipelines.stages.agent_executor import AgentExecutorStage
from pipelines.stages.note_updater import NoteUpdaterStage

class ReviewCommand(Command):
    @property
    def name(self) -> str:
        return "oc_review"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_review"

    def get_pipeline(self) -> Pipeline:
        return Pipeline(
            name="oc_review",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                ContextBuilderStage(),
                AgentExecutorStage(agent_type="review"),
                NoteUpdaterStage()
            ]
        )
```

### Ask Command (`pipelines/commands/oc_ask.py`)
```python
from pipelines.base import Pipeline
from pipelines.commands.base import Command
from pipelines.stages.hook_resolver import HookResolverStage
from pipelines.stages.snapshot_resolver import SnapshotResolverStage
from pipelines.stages.context_builder import ContextBuilderStage
from pipelines.stages.agent_executor import AgentExecutorStage
from pipelines.stages.note_updater import NoteUpdaterStage

class AskCommand(Command):
    @property
    def name(self) -> str:
        return "oc_ask"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_ask"

    def get_pipeline(self) -> Pipeline:
        return Pipeline(
            name="oc_ask",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                ContextBuilderStage(),
                AgentExecutorStage(agent_type="general"),
                NoteUpdaterStage()
            ]
        )
```

### Test Command (`pipelines/commands/oc_test.py`)
```python
from pipelines.base import Pipeline
from pipelines.commands.base import Command
from pipelines.stages.hook_resolver import HookResolverStage
from pipelines.stages.snapshot_resolver import SnapshotResolverStage
from pipelines.stages.context_builder import ContextBuilderStage
from pipelines.stages.agent_executor import AgentExecutorStage
from pipelines.stages.note_updater import NoteUpdaterStage

class TestCommand(Command):
    @property
    def name(self) -> str:
        return "oc_test"

    @property
    def trigger_pattern(self) -> str:
        return "/oc_test"

    def get_pipeline(self) -> Pipeline:
        return Pipeline(
            name="oc_test",
            stages=[
                HookResolverStage(),
                SnapshotResolverStage(),
                ContextBuilderStage(),
                AgentExecutorStage(agent_type="test"),
                NoteUpdaterStage()
            ]
        )
```

## Pipeline Registry (`pipelines/registry.py`)
```python
from typing import Optional, List
from pipelines.commands.base import Command
from pipelines.commands.oc_review import ReviewCommand
from pipelines.commands.oc_ask import AskCommand
from pipelines.commands.oc_test import TestCommand
from pipelines.base import Pipeline

# Register all commands
COMMANDS: List[Command] = [
    ReviewCommand(),
    AskCommand(),
    TestCommand()
]

def detect_command(text: str) -> Optional[Command]:
    """Detect command from text"""
    for command in COMMANDS:
        if command.trigger_pattern in text:
            return command
    return None

def get_pipeline_for_command(command_name: str) -> Optional[Pipeline]:
    """Get pipeline by command name"""
    for command in COMMANDS:
        if command.name == command_name:
            return command.get_pipeline()
    return None
```

## FastAPI Integration

### Updated Webhook Handler (`app.py`)
```python
from pipelines.base import PipelineContext
from pipelines.registry import detect_command

@app.post("/webhook")
async def gitlab_webhook(request: Request):
    """Receive GitLab webhook events - async, then triggers sync pipeline"""
    try:
        payload = await request.json()

        # Async part: Quick validation and command detection
        event_type = payload.get("object_kind")
        if event_type != "note":
            return JSONResponse({"status": "ignored"})

        note = payload.get("object_attributes", {}).get("note", "")
        command = detect_command(note)

        if not command:
            return JSONResponse({"status": "ignored"})

        # Create context
        context = PipelineContext(webhook_payload=payload)

        # Get pipeline for command
        pipeline = command.get_pipeline()

        # Run sync pipeline (in thread pool to not block event loop)
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, pipeline.execute, context)

        if result.success:
            return JSONResponse({
                "status": "completed",
                "command": command.name
            })
        else:
            return JSONResponse({
                "status": "error",
                "error": str(result.error)
            }, status_code=500)

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
```

## Unit Tests

### Test Pipeline Base (`tests/test_pipeline_base.py`)
```python
import pytest
from pipelines.base import Pipeline, Stage, StageResult, PipelineContext

class MockStage(Stage):
    def _execute(self, context: PipelineContext) -> StageResult:
        context.metadata["executed"] = True
        return StageResult(context=context, should_stop=False)

def test_pipeline_execution():
    context = PipelineContext(webhook_payload={})
    stages = [MockStage(), MockStage()]
    pipeline = Pipeline(name="test", stages=stages)

    result = pipeline.execute(context)

    assert result.success
    assert context.metadata["executed"]

def test_pipeline_stop_on_error():
    class ErrorStage(Stage):
        def _execute(self, context: PipelineContext) -> StageResult:
            raise ValueError("Test error")

    context = PipelineContext(webhook_payload={})
    stages = [MockStage(), ErrorStage(), MockStage()]
    pipeline = Pipeline(name="test", stages=stages)

    result = pipeline.execute(context)

    assert not result.success
    assert result.error is not None

def test_pipeline_should_stop():
    class StopStage(Stage):
        def _execute(self, context: PipelineContext) -> StageResult:
            return StageResult(context=context, should_stop=True)

    context = PipelineContext(webhook_payload={})
    stages = [MockStage(), StopStage(), MockStage()]
    pipeline = Pipeline(name="test", stages=stages)

    result = pipeline.execute(context)

    assert result.success
    assert context.metadata.get("final_executed") is None
```

### Test Hook Resolver (`tests/test_stages/test_hook_resolver.py`)
```python
import pytest
from pipelines.stages.hook_resolver import HookResolverStage
from pipelines.base import PipelineContext

def test_hook_resolver_detects_command():
    payload = {
        "object_kind": "note",
        "object_attributes": {
            "note": "Please /oc_review this",
            "noteable_type": "MergeRequest"
        },
        "project": {"id": 1},
        "merge_request": {"iid": 42}
    }
    context = PipelineContext(webhook_payload=payload)
    stage = HookResolverStage()

    result = stage.execute(context)

    assert not result.should_stop
    assert context.command == "oc_review"

def test_hook_resolver_ignores_non_note():
    payload = {
        "object_kind": "merge_request",
        "object_attributes": {"noteable_type": "MergeRequest"}
    }
    context = PipelineContext(webhook_payload=payload)
    stage = HookResolverStage()

    result = stage.execute(context)

    assert result.should_stop

def test_hook_resolver_ignores_no_command():
    payload = {
        "object_kind": "note",
        "object_attributes": {
            "note": "This is just a comment",
            "noteable_type": "MergeRequest"
        },
        "project": {"id": 1}
    }
    context = PipelineContext(webhook_payload=payload)
    stage = HookResolverStage()

    result = stage.execute(context)

    assert result.should_stop
```

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Create `pipelines/` directory structure
- [ ] Implement `pipelines/base.py` (Pipeline, Stage, Context, Result)
- [ ] Unit tests for base classes

### Phase 2: Command Registry
- [ ] Implement `pipelines/commands/base.py`
- [ ] Implement `pipelines/commands/oc_review.py`
- [ ] Implement `pipelines/commands/oc_ask.py`
- [ ] Implement `pipelines/commands/oc_test.py`
- [ ] Implement `pipelines/registry.py`

### Phase 3: Basic Stages
- [ ] Implement `HookResolverStage` with note posting
- [ ] Implement `SnapshotResolverStage`
- [ ] Unit tests for basic stages

### Phase 4: Context Building
- [ ] Implement `ContextBuilderStage` with git clone
- [ ] Add cleanup logic
- [ ] Unit tests (with mock git operations)

### Phase 5: Agent Integration
- [ ] Implement `AgentExecutorStage` (placeholder for now)
- [ ] Implement `NoteUpdaterStage`
- [ ] Unit tests

### Phase 6: FastAPI Integration
- [ ] Update `app.py` webhook handler
- [ ] Test webhook → pipeline flow
- [ ] Error handling improvements

### Phase 7: Testing & Refinement
- [ ] Integration tests for full pipelines
- [ ] Error logging improvements
- [ ] Documentation updates

## Dependencies
No new external dependencies required. Uses:
- Existing: `fastapi`, `uvicorn`, `requests`, `python-dotenv`, `pydantic`
- Standard library: `dataclasses`, `abc`, `asyncio`, `tempfile`, `shutil`, `subprocess`, `logging`

## Notes
- Async → Sync transition happens in webhook handler using `run_in_executor`
- Git operations use `subprocess` for simplicity
- Temp directories cleaned up after pipeline completion
- Error logging at stage level with full stack traces
- Pure Python configuration - no YAML/TOML
