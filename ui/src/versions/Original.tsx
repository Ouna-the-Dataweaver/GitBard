import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import { usePipelineEditor } from "../hooks/usePipelineEditor";
import { commaSeparated } from "../lib/helpers";
import type { PipelineDocument } from "../types";
import "../styles/original.css";

export default function Original() {
  const {
    metadata,
    pipelines,
    selectedPipelineId,
    draft,
    preview,
    validation,
    loading,
    error,
    flow,
    selectPipeline,
    updateDraft,
    duplicateDraft,
  } = usePipelineEditor();

  if (loading && !draft) {
    return <div className="v0-app v0-loading-state">Loading admin UI…</div>;
  }

  if (error && !draft) {
    return <div className="v0-app v0-loading-state">{error}</div>;
  }

  return (
    <div className="v0-app">
      <aside className="v0-sidebar">
        <div className="v0-sidebar-header">
          <p className="v0-eyebrow">GitBard</p>
          <h1>Pipeline Admin</h1>
          <p className="v0-muted">
            Original cards-in-cards design for comparison.
          </p>
        </div>

        <button
          className="v0-primary-button"
          type="button"
          onClick={duplicateDraft}
        >
          Duplicate Into Draft
        </button>

        <div className="v0-pipeline-list">
          {pipelines.map((pipeline) => (
            <button
              key={pipeline.id}
              type="button"
              className={`v0-pipeline-card ${
                selectedPipelineId === pipeline.id ? "v0-selected" : ""
              }`}
              onClick={() => void selectPipeline(pipeline.id)}
            >
              <div className="v0-pipeline-card-row">
                <strong>{pipeline.name}</strong>
                <span className={`v0-status-pill ${pipeline.enabled ? "v0-on" : "v0-off"}`}>
                  {pipeline.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <p>{pipeline.description}</p>
              <div className="v0-pipeline-meta">
                <span>{pipeline.preset}</span>
                <span>{pipeline.triggerText}</span>
                <span>{pipeline.scope}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="v0-main-panel">
        {draft ? (
          <>
            <section className="v0-panel v0-form-panel">
              <div className="v0-panel-header">
                <div>
                  <p className="v0-eyebrow">Editor</p>
                  <h2>{draft.name}</h2>
                </div>
                <div className="v0-header-actions">
                  <span className={`v0-status-pill ${draft.enabled ? "v0-on" : "v0-off"}`}>
                    {draft.enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>

              <div className="v0-section-grid">
                <section className="v0-form-section">
                  <h3>Basics</h3>
                  <label>
                    <span>Name</span>
                    <input
                      value={draft.name}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.name = event.target.value;
                          return current;
                        })
                      }
                    />
                  </label>
                  <label>
                    <span>Pipeline ID</span>
                    <input
                      value={draft.id}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.id = event.target.value;
                          return current;
                        })
                      }
                    />
                  </label>
                  <label>
                    <span>Description</span>
                    <textarea
                      rows={3}
                      value={draft.description}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.description = event.target.value;
                          return current;
                        })
                      }
                    />
                  </label>
                  <label className="v0-inline-toggle">
                    <input
                      type="checkbox"
                      checked={draft.enabled}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.enabled = event.target.checked;
                          return current;
                        })
                      }
                    />
                    <span>Enabled</span>
                  </label>
                </section>

                <section className="v0-form-section">
                  <h3>Trigger</h3>
                  <label>
                    <span>Trigger Type</span>
                    <select
                      value={draft.trigger.type}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.trigger.type = event.target.value as PipelineDocument["trigger"]["type"];
                          return current;
                        })
                      }
                    >
                      {metadata?.trigger_types.map((triggerType) => (
                        <option key={triggerType} value={triggerType}>
                          {triggerType}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Scope</span>
                    <select
                      value={draft.trigger.scope}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.trigger.scope = event.target.value as PipelineDocument["trigger"]["scope"];
                          return current;
                        })
                      }
                    >
                      {metadata?.scopes.map((scope) => (
                        <option key={scope} value={scope}>
                          {scope}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Command Text</span>
                    <input
                      value={draft.trigger.commandText}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.trigger.commandText = event.target.value;
                          return current;
                        })
                      }
                    />
                  </label>
                  <label>
                    <span>Mention Target</span>
                    <input
                      value={draft.trigger.mentionTarget}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.trigger.mentionTarget = event.target.value;
                          return current;
                        })
                      }
                    />
                  </label>
                </section>

                <section className="v0-form-section">
                  <h3>Execution</h3>
                  <label>
                    <span>Preset</span>
                    <select
                      value={draft.preset}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.preset = event.target.value as PipelineDocument["preset"];
                          current.execution.mode = current.preset;
                          return current;
                        })
                      }
                    >
                      {metadata?.pipeline_presets.map((preset) => (
                        <option key={preset} value={preset}>
                          {preset}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Agent Name</span>
                    <select
                      value={draft.execution.agentName}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.execution.agentName = event.target.value;
                          return current;
                        })
                      }
                    >
                      {metadata?.agents.map((agent) => (
                        <option key={agent} value={agent}>
                          {agent}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Model Name</span>
                    <select
                      value={draft.execution.modelName}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.execution.modelName = event.target.value;
                          return current;
                        })
                      }
                    >
                      {metadata?.models.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Question Template</span>
                    <textarea
                      rows={4}
                      value={draft.execution.questionTemplate}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.execution.questionTemplate = event.target.value;
                          return current;
                        })
                      }
                    />
                  </label>
                </section>

                <section className="v0-form-section">
                  <h3>Workspace + Preparation</h3>
                  <label>
                    <span>Workspace Mode</span>
                    <select
                      value={draft.workspace.mode}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.workspace.mode = event.target.value as PipelineDocument["workspace"]["mode"];
                          return current;
                        })
                      }
                    >
                      {metadata?.workspace_modes.map((mode) => (
                        <option key={mode} value={mode}>
                          {mode}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>Checkout Strategy</span>
                    <select
                      value={draft.workspace.checkoutStrategy}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.workspace.checkoutStrategy =
                            event.target.value as PipelineDocument["workspace"]["checkoutStrategy"];
                          return current;
                        })
                      }
                    >
                      {metadata?.checkout_strategies.map((strategy) => (
                        <option key={strategy} value={strategy}>
                          {strategy}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="v0-inline-toggle">
                    <input
                      type="checkbox"
                      checked={draft.workspace.cleanupAfterRun}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.workspace.cleanupAfterRun = event.target.checked;
                          return current;
                        })
                      }
                    />
                    <span>Cleanup after run</span>
                  </label>
                  <label className="v0-inline-toggle">
                    <input
                      type="checkbox"
                      checked={draft.preparation.enableRepoHook}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.preparation.enableRepoHook = event.target.checked;
                          return current;
                        })
                      }
                    />
                    <span>Enable repo hook</span>
                  </label>
                  <label className="v0-inline-toggle">
                    <input
                      type="checkbox"
                      checked={draft.preparation.enableOpencodePreparation}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.preparation.enableOpencodePreparation =
                            event.target.checked;
                          return current;
                        })
                      }
                    />
                    <span>Enable OpenCode preparation</span>
                  </label>
                </section>

                <section className="v0-form-section">
                  <h3>Filters + Output</h3>
                  <label>
                    <span>Project Allowlist</span>
                    <input
                      value={draft.filters.projectAllowlist.join(", ")}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.filters.projectAllowlist = commaSeparated(
                            event.target.value,
                          );
                          return current;
                        })
                      }
                    />
                  </label>
                  <label>
                    <span>Branch Patterns</span>
                    <input
                      value={draft.filters.branchPatterns.join(", ")}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.filters.branchPatterns = commaSeparated(
                            event.target.value,
                          );
                          return current;
                        })
                      }
                    />
                  </label>
                  <label>
                    <span>Post Mode</span>
                    <select
                      value={draft.output.postMode}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.output.postMode =
                            event.target.value as PipelineDocument["output"]["postMode"];
                          return current;
                        })
                      }
                    >
                      {metadata?.output_post_modes.map((mode) => (
                        <option key={mode} value={mode}>
                          {mode}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="v0-inline-toggle">
                    <input
                      type="checkbox"
                      checked={draft.output.includeArtifactsInNote}
                      onChange={(event) =>
                        updateDraft((current) => {
                          current.output.includeArtifactsInNote =
                            event.target.checked;
                          return current;
                        })
                      }
                    />
                    <span>Include artifacts in note</span>
                  </label>
                </section>
              </div>
            </section>

            <section className="v0-panel v0-preview-panel">
              <div className="v0-panel-header">
                <div>
                  <p className="v0-eyebrow">Preview</p>
                  <h2>Compiled Runtime Plan</h2>
                </div>
              </div>

              <div className="v0-preview-summary">
                <div className="v0-summary-card">
                  <span className="v0-summary-label">Trigger</span>
                  <strong>
                    {preview?.compiled_pipeline.trigger.type ?? "unknown"} /{" "}
                    {preview?.compiled_pipeline.trigger.scope ?? "unknown"}
                  </strong>
                  <p>{preview?.compiled_pipeline.trigger.text ?? "No trigger text"}</p>
                </div>
                <div className="v0-summary-card">
                  <span className="v0-summary-label">Agent</span>
                  <strong>{preview?.compiled_pipeline.agent ?? "unassigned"}</strong>
                  <p>{preview?.compiled_pipeline.model ?? "No model selected"}</p>
                </div>
                <div className="v0-summary-card">
                  <span className="v0-summary-label">Stages</span>
                  <strong>{preview?.compiled_pipeline.stages.length ?? 0}</strong>
                  <p>Node layout placeholder for an eventual n8n-like builder.</p>
                </div>
              </div>

              <div className="v0-flow-panel">
                <ReactFlow
                  fitView
                  nodes={flow.nodes}
                  edges={flow.edges}
                  nodesDraggable={false}
                  nodesConnectable={false}
                  elementsSelectable={false}
                >
                  <MiniMap zoomable pannable />
                  <Controls />
                  <Background gap={18} size={1} />
                </ReactFlow>
              </div>

              <div className="v0-feedback-grid">
                <div className="v0-feedback-card">
                  <h3>Validation</h3>
                  <ul>
                    {(validation?.errors.length
                      ? validation.errors
                      : ["No validation errors."]).map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
                <div className="v0-feedback-card">
                  <h3>Warnings</h3>
                  <ul>
                    {(preview?.warnings.length
                      ? preview.warnings
                      : ["No warnings for this draft."]).map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
