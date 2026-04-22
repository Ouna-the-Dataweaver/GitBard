import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import { usePipelineEditor } from "../hooks/usePipelineEditor";
import { commaSeparated } from "../lib/helpers";
import type { PipelineDocument } from "../types";
import "../styles/v2.css";

export default function V2GlassNeon() {
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
      <div className="v2-app" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        Loading admin UI…
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div className="v2-app" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        {error}
      </div>
    );
  }

  return (
    <div className="v2-app">
      <aside className="v2-sidebar">
        <div className="v2-sidebar-header">
          <h1>Pipeline Admin</h1>
          <p>Retro-futuristic glass HUD</p>
        </div>
        <button className="v2-btn" type="button" onClick={duplicateDraft}>
          Duplicate Into Draft
        </button>
        <div className="v2-pipeline-list">
          {pipelines.map((pipeline) => (
            <button
              key={pipeline.id}
              type="button"
              className={`v2-pipeline-item ${selectedPipelineId === pipeline.id ? "v2-selected" : ""}`}
              onClick={() => void selectPipeline(pipeline.id)}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <strong>{pipeline.name}</strong>
                <span className={`v2-status ${pipeline.enabled ? "v2-on" : "v2-off"}`}>
                  {pipeline.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <p>{pipeline.description}</p>
              <div className="v2-pipeline-meta">
                <span>{pipeline.preset}</span>
                <span>{pipeline.triggerText}</span>
                <span>{pipeline.scope}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="v2-main">
        {draft ? (
          <>
            <section className="v2-panel">
              <div className="v2-editor-header">
                <div>
                  <div className="v2-eyebrow">Editor</div>
                  <h2>{draft.name}</h2>
                </div>
                <span className={`v2-status ${draft.enabled ? "v2-on" : "v2-off"}`}>
                  {draft.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <hr className="v2-separator" />

              <div className="v2-grid">
                <section className="v2-section">
                  <h3 className="v2-section-title">Basics</h3>
                  <label>
                    <span>Name</span>
                    <input value={draft.name} onChange={(e) => updateDraft((c) => { c.name = e.target.value; return c; })} />
                  </label>
                  <label>
                    <span>Pipeline ID</span>
                    <input value={draft.id} onChange={(e) => updateDraft((c) => { c.id = e.target.value; return c; })} />
                  </label>
                  <label>
                    <span>Description</span>
                    <textarea rows={3} value={draft.description} onChange={(e) => updateDraft((c) => { c.description = e.target.value; return c; })} />
                  </label>
                  <label className="v2-check">
                    <input type="checkbox" checked={draft.enabled} onChange={(e) => updateDraft((c) => { c.enabled = e.target.checked; return c; })} />
                    <span>Enabled</span>
                  </label>
                </section>

                <section className="v2-section">
                  <h3 className="v2-section-title">Trigger</h3>
                  <label>
                    <span>Trigger Type</span>
                    <select value={draft.trigger.type} onChange={(e) => updateDraft((c) => { c.trigger.type = e.target.value as PipelineDocument["trigger"]["type"]; return c; })}>
                      {metadata?.trigger_types.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Scope</span>
                    <select value={draft.trigger.scope} onChange={(e) => updateDraft((c) => { c.trigger.scope = e.target.value as PipelineDocument["trigger"]["scope"]; return c; })}>
                      {metadata?.scopes.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Command Text</span>
                    <input value={draft.trigger.commandText} onChange={(e) => updateDraft((c) => { c.trigger.commandText = e.target.value; return c; })} />
                  </label>
                  <label>
                    <span>Mention Target</span>
                    <input value={draft.trigger.mentionTarget} onChange={(e) => updateDraft((c) => { c.trigger.mentionTarget = e.target.value; return c; })} />
                  </label>
                </section>

                <section className="v2-section">
                  <h3 className="v2-section-title">Execution</h3>
                  <label>
                    <span>Preset</span>
                    <select value={draft.preset} onChange={(e) => updateDraft((c) => { c.preset = e.target.value as PipelineDocument["preset"]; c.execution.mode = c.preset; return c; })}>
                      {metadata?.pipeline_presets.map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Agent Name</span>
                    <select value={draft.execution.agentName} onChange={(e) => updateDraft((c) => { c.execution.agentName = e.target.value; return c; })}>
                      {metadata?.agents.map((a) => <option key={a} value={a}>{a}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Model Name</span>
                    <select value={draft.execution.modelName} onChange={(e) => updateDraft((c) => { c.execution.modelName = e.target.value; return c; })}>
                      {metadata?.models.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Question Template</span>
                    <textarea rows={4} value={draft.execution.questionTemplate} onChange={(e) => updateDraft((c) => { c.execution.questionTemplate = e.target.value; return c; })} />
                  </label>
                </section>

                <section className="v2-section">
                  <h3 className="v2-section-title">Workspace + Preparation</h3>
                  <label>
                    <span>Workspace Mode</span>
                    <select value={draft.workspace.mode} onChange={(e) => updateDraft((c) => { c.workspace.mode = e.target.value as PipelineDocument["workspace"]["mode"]; return c; })}>
                      {metadata?.workspace_modes.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>Checkout Strategy</span>
                    <select value={draft.workspace.checkoutStrategy} onChange={(e) => updateDraft((c) => { c.workspace.checkoutStrategy = e.target.value as PipelineDocument["workspace"]["checkoutStrategy"]; return c; })}>
                      {metadata?.checkout_strategies.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                  <label className="v2-check">
                    <input type="checkbox" checked={draft.workspace.cleanupAfterRun} onChange={(e) => updateDraft((c) => { c.workspace.cleanupAfterRun = e.target.checked; return c; })} />
                    <span>Cleanup after run</span>
                  </label>
                  <label className="v2-check">
                    <input type="checkbox" checked={draft.preparation.enableRepoHook} onChange={(e) => updateDraft((c) => { c.preparation.enableRepoHook = e.target.checked; return c; })} />
                    <span>Enable repo hook</span>
                  </label>
                  <label className="v2-check">
                    <input type="checkbox" checked={draft.preparation.enableOpencodePreparation} onChange={(e) => updateDraft((c) => { c.preparation.enableOpencodePreparation = e.target.checked; return c; })} />
                    <span>Enable OpenCode preparation</span>
                  </label>
                </section>

                <section className="v2-section">
                  <h3 className="v2-section-title">Filters + Output</h3>
                  <label>
                    <span>Project Allowlist</span>
                    <input value={draft.filters.projectAllowlist.join(", ")} onChange={(e) => updateDraft((c) => { c.filters.projectAllowlist = commaSeparated(e.target.value); return c; })} />
                  </label>
                  <label>
                    <span>Branch Patterns</span>
                    <input value={draft.filters.branchPatterns.join(", ")} onChange={(e) => updateDraft((c) => { c.filters.branchPatterns = commaSeparated(e.target.value); return c; })} />
                  </label>
                  <label>
                    <span>Post Mode</span>
                    <select value={draft.output.postMode} onChange={(e) => updateDraft((c) => { c.output.postMode = e.target.value as PipelineDocument["output"]["postMode"]; return c; })}>
                      {metadata?.output_post_modes.map((m) => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </label>
                  <label className="v2-check">
                    <input type="checkbox" checked={draft.output.includeArtifactsInNote} onChange={(e) => updateDraft((c) => { c.output.includeArtifactsInNote = e.target.checked; return c; })} />
                    <span>Include artifacts in note</span>
                  </label>
                </section>
              </div>
            </section>

            <section className="v2-panel">
              <div className="v2-preview-header">
                <div>
                  <div className="v2-eyebrow">Preview</div>
                  <h2>Compiled Runtime Plan</h2>
                </div>
              </div>
              <hr className="v2-separator" />

              <div className="v2-stats">
                <div className="v2-glass-card">
                  <span className="v2-glass-label">Trigger</span>
                  <strong>{preview?.compiled_pipeline.trigger.type ?? "unknown"} / {preview?.compiled_pipeline.trigger.scope ?? "unknown"}</strong>
                  <p>{preview?.compiled_pipeline.trigger.text ?? "No trigger text"}</p>
                </div>
                <div className="v2-glass-card">
                  <span className="v2-glass-label">Agent</span>
                  <strong>{preview?.compiled_pipeline.agent ?? "unassigned"}</strong>
                  <p>{preview?.compiled_pipeline.model ?? "No model selected"}</p>
                </div>
                <div className="v2-glass-card">
                  <span className="v2-glass-label">Stages</span>
                  <strong>{preview?.compiled_pipeline.stages.length ?? 0}</strong>
                  <p>Runtime stage count</p>
                </div>
              </div>

              <div className="v2-flow">
                <ReactFlow fitView nodes={flow.nodes} edges={flow.edges} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}>
                  <MiniMap zoomable pannable />
                  <Controls />
                  <Background gap={18} size={1} />
                </ReactFlow>
              </div>

              <div className="v2-feedback">
                <div className="v2-feedback-card">
                  <h3>Validation</h3>
                  <ul>
                    {(validation?.errors.length ? validation.errors : ["No validation errors."]).map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                </div>
                <div className="v2-feedback-card">
                  <h3>Warnings</h3>
                  <ul>
                    {(preview?.warnings.length ? preview.warnings : ["No warnings for this draft."]).map((m) => (
                      <li key={m}>{m}</li>
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
