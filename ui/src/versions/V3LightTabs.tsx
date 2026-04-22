import { useState } from "react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import { usePipelineEditor } from "../hooks/usePipelineEditor";
import { commaSeparated } from "../lib/helpers";
import type { PipelineDocument } from "../types";
import "../styles/v3.css";

const tabs = [
  { key: "basics", label: "Basics" },
  { key: "trigger", label: "Trigger" },
  { key: "execution", label: "Execution" },
  { key: "workspace", label: "Workspace" },
  { key: "filters", label: "Filters + Output" },
] as const;

type TabKey = (typeof tabs)[number]["key"];

export default function V3LightTabs() {
  const [tab, setTab] = useState<TabKey>("basics");
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
    return (
      <div className="v3-app" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        Loading admin UI…
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div className="v3-app" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        {error}
      </div>
    );
  }

  return (
    <div className="v3-app">
      <aside className="v3-sidebar">
        <div className="v3-sidebar-header">
          <h1>Pipeline Admin</h1>
          <p>Swiss editorial layout</p>
        </div>
        <button className="v3-btn" type="button" onClick={duplicateDraft}>
          Duplicate Into Draft
        </button>
        <div className="v3-pipeline-list">
          {pipelines.map((pipeline) => (
            <button
              key={pipeline.id}
              type="button"
              className={`v3-pipeline-item ${selectedPipelineId === pipeline.id ? "v3-selected" : ""}`}
              onClick={() => void selectPipeline(pipeline.id)}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <strong>{pipeline.name}</strong>
                <span className={`v3-status ${pipeline.enabled ? "v3-on" : "v3-off"}`}>
                  {pipeline.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <p>{pipeline.description}</p>
              <div className="v3-pipeline-meta">
                <span>{pipeline.preset}</span>
                <span>{pipeline.triggerText}</span>
                <span>{pipeline.scope}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="v3-main">
        {draft ? (
          <>
            <div className="v3-editor">
              <div className="v3-tabs">
                {tabs.map((t) => (
                  <button
                    key={t.key}
                    className={`v3-tab ${tab === t.key ? "v3-active" : ""}`}
                    onClick={() => setTab(t.key)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              <div className="v3-tab-content">
                {tab === "basics" && (
                  <>
                    <h2 className="v3-tab-title">Basics</h2>
                    <div className="v3-grid">
                      <label className="v3-field">
                        <span>Name</span>
                        <input value={draft.name} onChange={(e) => updateDraft((c) => { c.name = e.target.value; return c; })} />
                      </label>
                      <label className="v3-field">
                        <span>Pipeline ID</span>
                        <input value={draft.id} onChange={(e) => updateDraft((c) => { c.id = e.target.value; return c; })} />
                      </label>
                      <label className="v3-field" style={{ gridColumn: "1 / -1" }}>
                        <span>Description</span>
                        <textarea rows={3} value={draft.description} onChange={(e) => updateDraft((c) => { c.description = e.target.value; return c; })} />
                      </label>
                      <label className="v3-field v3-check">
                        <input type="checkbox" checked={draft.enabled} onChange={(e) => updateDraft((c) => { c.enabled = e.target.checked; return c; })} />
                        <span>Enabled</span>
                      </label>
                    </div>
                  </>
                )}

                {tab === "trigger" && (
                  <>
                    <h2 className="v3-tab-title">Trigger</h2>
                    <div className="v3-grid">
                      <label className="v3-field">
                        <span>Trigger Type</span>
                        <select value={draft.trigger.type} onChange={(e) => updateDraft((c) => { c.trigger.type = e.target.value as PipelineDocument["trigger"]["type"]; return c; })}>
                          {metadata?.trigger_types.map((t) => <option key={t} value={t}>{t}</option>)}
                        </select>
                      </label>
                      <label className="v3-field">
                        <span>Scope</span>
                        <select value={draft.trigger.scope} onChange={(e) => updateDraft((c) => { c.trigger.scope = e.target.value as PipelineDocument["trigger"]["scope"]; return c; })}>
                          {metadata?.scopes.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </label>
                      <label className="v3-field">
                        <span>Command Text</span>
                        <input value={draft.trigger.commandText} onChange={(e) => updateDraft((c) => { c.trigger.commandText = e.target.value; return c; })} />
                      </label>
                      <label className="v3-field">
                        <span>Mention Target</span>
                        <input value={draft.trigger.mentionTarget} onChange={(e) => updateDraft((c) => { c.trigger.mentionTarget = e.target.value; return c; })} />
                      </label>
                    </div>
                  </>
                )}

                {tab === "execution" && (
                  <>
                    <h2 className="v3-tab-title">Execution</h2>
                    <div className="v3-grid">
                      <label className="v3-field">
                        <span>Preset</span>
                        <select value={draft.preset} onChange={(e) => updateDraft((c) => { c.preset = e.target.value as PipelineDocument["preset"]; c.execution.mode = c.preset; return c; })}>
                          {metadata?.pipeline_presets.map((p) => <option key={p} value={p}>{p}</option>)}
                        </select>
                      </label>
                      <label className="v3-field">
                        <span>Agent Name</span>
                        <select value={draft.execution.agentName} onChange={(e) => updateDraft((c) => { c.execution.agentName = e.target.value; return c; })}>
                          {metadata?.agents.map((a) => <option key={a} value={a}>{a}</option>)}
                        </select>
                      </label>
                      <label className="v3-field">
                        <span>Model Name</span>
                        <select value={draft.execution.modelName} onChange={(e) => updateDraft((c) => { c.execution.modelName = e.target.value; return c; })}>
                          {metadata?.models.map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </label>
                      <label className="v3-field" style={{ gridColumn: "1 / -1" }}>
                        <span>Question Template</span>
                        <textarea rows={4} value={draft.execution.questionTemplate} onChange={(e) => updateDraft((c) => { c.execution.questionTemplate = e.target.value; return c; })} />
                      </label>
                    </div>
                  </>
                )}

                {tab === "workspace" && (
                  <>
                    <h2 className="v3-tab-title">Workspace + Preparation</h2>
                    <div className="v3-grid">
                      <label className="v3-field">
                        <span>Workspace Mode</span>
                        <select value={draft.workspace.mode} onChange={(e) => updateDraft((c) => { c.workspace.mode = e.target.value as PipelineDocument["workspace"]["mode"]; return c; })}>
                          {metadata?.workspace_modes.map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </label>
                      <label className="v3-field">
                        <span>Checkout Strategy</span>
                        <select value={draft.workspace.checkoutStrategy} onChange={(e) => updateDraft((c) => { c.workspace.checkoutStrategy = e.target.value as PipelineDocument["workspace"]["checkoutStrategy"]; return c; })}>
                          {metadata?.checkout_strategies.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </label>
                      <label className="v3-field v3-check">
                        <input type="checkbox" checked={draft.workspace.cleanupAfterRun} onChange={(e) => updateDraft((c) => { c.workspace.cleanupAfterRun = e.target.checked; return c; })} />
                        <span>Cleanup after run</span>
                      </label>
                      <label className="v3-field v3-check">
                        <input type="checkbox" checked={draft.preparation.enableRepoHook} onChange={(e) => updateDraft((c) => { c.preparation.enableRepoHook = e.target.checked; return c; })} />
                        <span>Enable repo hook</span>
                      </label>
                      <label className="v3-field v3-check">
                        <input type="checkbox" checked={draft.preparation.enableOpencodePreparation} onChange={(e) => updateDraft((c) => { c.preparation.enableOpencodePreparation = e.target.checked; return c; })} />
                        <span>Enable OpenCode preparation</span>
                      </label>
                    </div>
                  </>
                )}

                {tab === "filters" && (
                  <>
                    <h2 className="v3-tab-title">Filters + Output</h2>
                    <div className="v3-grid">
                      <label className="v3-field">
                        <span>Project Allowlist</span>
                        <input value={draft.filters.projectAllowlist.join(", ")} onChange={(e) => updateDraft((c) => { c.filters.projectAllowlist = commaSeparated(e.target.value); return c; })} />
                      </label>
                      <label className="v3-field">
                        <span>Branch Patterns</span>
                        <input value={draft.filters.branchPatterns.join(", ")} onChange={(e) => updateDraft((c) => { c.filters.branchPatterns = commaSeparated(e.target.value); return c; })} />
                      </label>
                      <label className="v3-field">
                        <span>Post Mode</span>
                        <select value={draft.output.postMode} onChange={(e) => updateDraft((c) => { c.output.postMode = e.target.value as PipelineDocument["output"]["postMode"]; return c; })}>
                          {metadata?.output_post_modes.map((m) => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </label>
                      <label className="v3-field v3-check">
                        <input type="checkbox" checked={draft.output.includeArtifactsInNote} onChange={(e) => updateDraft((c) => { c.output.includeArtifactsInNote = e.target.checked; return c; })} />
                        <span>Include artifacts in note</span>
                      </label>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div className="v3-preview">
              <div className="v3-preview-card">
                <div className="v3-preview-header">
                  <div>
                    <div className="v3-eyebrow">Preview</div>
                    <h2>Compiled Runtime Plan</h2>
                  </div>
                </div>

                <div className="v3-stats">
                  <div className="v3-stat">
                    <span className="v3-stat-label">Trigger</span>
                    <strong>{preview?.compiled_pipeline.trigger.type ?? "unknown"}</strong>
                    <p>{preview?.compiled_pipeline.trigger.scope ?? "unknown"}</p>
                  </div>
                  <div className="v3-stat">
                    <span className="v3-stat-label">Agent</span>
                    <strong>{preview?.compiled_pipeline.agent ?? "unassigned"}</strong>
                    <p>{preview?.compiled_pipeline.model ?? "No model"}</p>
                  </div>
                  <div className="v3-stat">
                    <span className="v3-stat-label">Stages</span>
                    <strong>{preview?.compiled_pipeline.stages.length ?? 0}</strong>
                    <p>Total stages</p>
                  </div>
                </div>

                <div className="v3-flow">
                  <ReactFlow fitView nodes={flow.nodes} edges={flow.edges} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}>
                    <MiniMap zoomable pannable />
                    <Controls />
                    <Background gap={18} size={1} />
                  </ReactFlow>
                </div>

                <div className="v3-feedback">
                  <div className="v3-alert v3-alert-error">
                    <h3>Validation</h3>
                    <ul>
                      {(validation?.errors.length ? validation.errors : ["No validation errors."]).map((m) => (
                        <li key={m}>{m}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="v3-alert v3-alert-warn">
                    <h3>Warnings</h3>
                    <ul>
                      {(preview?.warnings.length ? preview.warnings : ["No warnings for this draft."]).map((m) => (
                        <li key={m}>{m}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
