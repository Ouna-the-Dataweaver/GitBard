import { useState, useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  type NodeProps,
} from "reactflow";
import { usePipelineEditor } from "../hooks/usePipelineEditor";
import { commaSeparated, buildEditableFlow } from "../lib/helpers";
import type { PipelineDocument } from "../types";
import "../styles/v4.css";

function PipelineNode({
  data,
  selected,
}: NodeProps<{
  label: string;
  section: string;
  stages: string[];
  summary: string;
}>) {
  return (
    <div className={`v4-node ${selected ? "v4-node-selected" : ""}`}>
      <Handle
        type="target"
        position={Position.Left}
        className="v4-handle v4-handle-left"
      />
      <div className="v4-node-header">
        <div className="v4-node-label">{data.label}</div>
        <div className="v4-node-summary">{data.summary}</div>
      </div>
      {data.stages.length > 0 && (
        <div className="v4-node-stages">
          {data.stages.map((s) => (
            <span key={s} className="v4-node-stage-tag">
              {s.replace("Stage", "")}
            </span>
          ))}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        className="v4-handle v4-handle-right"
      />
    </div>
  );
}

const nodeTypes = {
  pipelineNode: PipelineNode,
};

const sectionTitles: Record<string, string> = {
  basics: "Pipeline Basics",
  trigger: "Trigger Configuration",
  filters: "Filters + Context",
  workspace: "Workspace Setup",
  preparation: "Preparation",
  execution: "Execution",
  output: "Output + Posting",
};

export default function V4GraphCentric() {
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const {
    metadata,
    pipelines,
    selectedPipelineId,
    draft,
    preview,
    validation,
    loading,
    error,
    saving,
    saved,
    dirty,
    selectPipeline,
    updateDraft,
    saveDraft,
    createNewPipeline,
    duplicateDraft,
    deleteCurrentPipeline,
  } = usePipelineEditor();

  const flow = useMemo(
    () => buildEditableFlow(preview, draft),
    [preview, draft],
  );

  const onNodeClick = useCallback(
    (_event: unknown, node: { data?: { section?: string } }) => {
      if (node.data?.section) {
        setSelectedSection(node.data.section);
      }
    },
    [],
  );

  if (loading && !draft) {
    return (
      <div
        className="v4-app"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        Loading admin UI…
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div
        className="v4-app"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {error}
      </div>
    );
  }

  return (
    <div className="v4-app">
      <aside className="v4-sidebar">
        <div className="v4-sidebar-header">
          <h1>Pipeline Admin</h1>
          <p>Graph-centric editor</p>
        </div>
        <button className="v4-btn v4-btn-primary" type="button" onClick={() => void createNewPipeline()}>
          + New Pipeline
        </button>
        <div className="v4-pipeline-list">
          {pipelines.map((pipeline) => (
            <button
              key={pipeline.id}
              type="button"
              className={`v4-pipeline-item ${selectedPipelineId === pipeline.id ? "v4-selected" : ""}`}
              onClick={() => void selectPipeline(pipeline.id)}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                }}
              >
                <strong>{pipeline.name}</strong>
                <span
                  className={`v4-status ${pipeline.enabled ? "v4-on" : "v4-off"}`}
                >
                  {pipeline.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <p>{pipeline.description}</p>
              <div className="v4-pipeline-meta">
                <span>{pipeline.preset}</span>
                <span>{pipeline.triggerText}</span>
                <span>{pipeline.scope}</span>
              </div>
            </button>
          ))}
        </div>
      </aside>

      <main className="v4-main">
        {draft ? (
          <>
            <header className="v4-header">
              <div>
                <div className="v4-eyebrow">Pipeline Editor</div>
                <h2>{draft.name}</h2>
              </div>
              <div className="v4-header-actions">
                <span
                  className={`v4-status ${draft.enabled ? "v4-on" : "v4-off"}`}
                >
                  {draft.enabled ? "Enabled" : "Disabled"}
                </span>
                {dirty && <span className="v4-unsaved-dot" title="Unsaved changes" />}
                <button
                  className="v4-btn v4-btn-primary"
                  type="button"
                  disabled={saving || !dirty}
                  onClick={() => void saveDraft()}
                >
                  {saving ? "Saving…" : saved ? "Saved" : "Save"}
                </button>
                <button className="v4-btn" type="button" onClick={() => void duplicateDraft()}>
                  Duplicate
                </button>
                <button
                  className="v4-btn v4-btn-danger"
                  type="button"
                  disabled={saving}
                  onClick={() => { if (confirm("Delete this pipeline?")) void deleteCurrentPipeline(); }}
                >
                  Delete
                </button>
              </div>
            </header>

            <div className="v4-graph-wrap">
              <ReactFlow
                fitView
                nodes={flow.nodes}
                edges={flow.edges}
                nodeTypes={nodeTypes}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={true}
                onNodeClick={onNodeClick}
              >
                <MiniMap zoomable pannable />
                <Controls />
                <Background gap={18} size={1} />
              </ReactFlow>
            </div>

            <div className="v4-editor">
              {!selectedSection ? (
                <div className="v4-editor-placeholder">
                  <p>Select a node in the pipeline graph to edit its configuration.</p>
                  <div className="v4-feedback-inline">
                    <div className="v4-feedback-block">
                      <h3>Validation</h3>
                      <ul>
                        {(validation?.errors.length
                          ? validation.errors
                          : ["No validation errors."]
                        ).map((m) => (
                          <li key={m}>{m}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="v4-feedback-block">
                      <h3>Warnings</h3>
                      <ul>
                        {(preview?.warnings.length
                          ? preview.warnings
                          : ["No warnings for this draft."]
                        ).map((m) => (
                          <li key={m}>{m}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="v4-editor-content">
                  <div className="v4-editor-topbar">
                    <h3>{sectionTitles[selectedSection] ?? selectedSection}</h3>
                    <button
                      className="v4-btn-ghost"
                      type="button"
                      onClick={() => setSelectedSection(null)}
                    >
                      Close
                    </button>
                  </div>

                  {selectedSection === "basics" && (
                    <div className="v4-grid">
                      <label className="v4-field">
                        <span>Name</span>
                        <input
                          value={draft.name}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.name = e.target.value;
                              return c;
                            })
                          }
                        />
                      </label>
                      <label className="v4-field">
                        <span>Pipeline ID</span>
                        <input
                          value={draft.id}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.id = e.target.value;
                              return c;
                            })
                          }
                        />
                      </label>
                      <label
                        className="v4-field"
                        style={{ gridColumn: "1 / -1" }}
                      >
                        <span>Description</span>
                        <textarea
                          rows={3}
                          value={draft.description}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.description = e.target.value;
                              return c;
                            })
                          }
                        />
                      </label>
                      <label className="v4-field v4-check">
                        <input
                          type="checkbox"
                          checked={draft.enabled}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.enabled = e.target.checked;
                              return c;
                            })
                          }
                        />
                        <span>Enabled</span>
                      </label>
                    </div>
                  )}

                  {selectedSection === "trigger" && (
                    <div className="v4-grid">
                      <label className="v4-field">
                        <span>Trigger Type</span>
                        <select
                          value={draft.trigger.type}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.trigger.type = e.target.value as PipelineDocument["trigger"]["type"];
                              return c;
                            })
                          }
                        >
                          {metadata?.trigger_types.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field">
                        <span>Scope</span>
                        <select
                          value={draft.trigger.scope}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.trigger.scope = e.target.value as PipelineDocument["trigger"]["scope"];
                              return c;
                            })
                          }
                        >
                          {metadata?.scopes.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field">
                        <span>Command Text</span>
                        <input
                          value={draft.trigger.commandText}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.trigger.commandText = e.target.value;
                              return c;
                            })
                          }
                        />
                      </label>
                      <label className="v4-field">
                        <span>Mention Target</span>
                        <input
                          value={draft.trigger.mentionTarget}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.trigger.mentionTarget = e.target.value;
                              return c;
                            })
                          }
                        />
                      </label>
                    </div>
                  )}

                  {selectedSection === "filters" && (
                    <div className="v4-grid">
                      <label className="v4-field">
                        <span>Project Allowlist</span>
                        <input
                          value={draft.filters.projectAllowlist.join(", ")}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.filters.projectAllowlist = commaSeparated(
                                e.target.value,
                              );
                              return c;
                            })
                          }
                        />
                      </label>
                      <label className="v4-field">
                        <span>Branch Patterns</span>
                        <input
                          value={draft.filters.branchPatterns.join(", ")}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.filters.branchPatterns = commaSeparated(
                                e.target.value,
                              );
                              return c;
                            })
                          }
                        />
                      </label>
                    </div>
                  )}

                  {selectedSection === "workspace" && (
                    <div className="v4-grid">
                      <label className="v4-field">
                        <span>Workspace Mode</span>
                        <select
                          value={draft.workspace.mode}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.workspace.mode = e.target.value as PipelineDocument["workspace"]["mode"];
                              return c;
                            })
                          }
                        >
                          {metadata?.workspace_modes.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field">
                        <span>Checkout Strategy</span>
                        <select
                          value={draft.workspace.checkoutStrategy}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.workspace.checkoutStrategy = e.target.value as PipelineDocument["workspace"]["checkoutStrategy"];
                              return c;
                            })
                          }
                        >
                          {metadata?.checkout_strategies.map((s) => (
                            <option key={s} value={s}>
                              {s}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field v4-check">
                        <input
                          type="checkbox"
                          checked={draft.workspace.cleanupAfterRun}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.workspace.cleanupAfterRun = e.target.checked;
                              return c;
                            })
                          }
                        />
                        <span>Cleanup after run</span>
                      </label>
                    </div>
                  )}

                  {selectedSection === "preparation" && (
                    <div className="v4-grid">
                      <label className="v4-field v4-check">
                        <input
                          type="checkbox"
                          checked={draft.preparation.enableRepoHook}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.preparation.enableRepoHook = e.target.checked;
                              return c;
                            })
                          }
                        />
                        <span>Enable repo hook</span>
                      </label>
                      <label className="v4-field v4-check">
                        <input
                          type="checkbox"
                          checked={draft.preparation.enableOpencodePreparation}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.preparation.enableOpencodePreparation =
                                e.target.checked;
                              return c;
                            })
                          }
                        />
                        <span>Enable OpenCode preparation</span>
                      </label>
                      <label className="v4-field v4-check">
                        <input
                          type="checkbox"
                          checked={draft.preparation.allowDependencyInstall}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.preparation.allowDependencyInstall =
                                e.target.checked;
                              return c;
                            })
                          }
                        />
                        <span>Allow dependency install</span>
                      </label>
                    </div>
                  )}

                  {selectedSection === "execution" && (
                    <div className="v4-grid">
                      <label className="v4-field">
                        <span>Preset</span>
                        <select
                          value={draft.preset}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.preset = e.target.value as PipelineDocument["preset"];
                              c.execution.mode = c.preset;
                              return c;
                            })
                          }
                        >
                          {metadata?.pipeline_presets.map((p) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field">
                        <span>Agent Name</span>
                        <select
                          value={draft.execution.agentName}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.execution.agentName = e.target.value;
                              return c;
                            })
                          }
                        >
                          {metadata?.agents.map((a) => (
                            <option key={a} value={a}>
                              {a}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field">
                        <span>Model Name</span>
                        <select
                          value={draft.execution.modelName}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.execution.modelName = e.target.value;
                              return c;
                            })
                          }
                        >
                          {metadata?.models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label
                        className="v4-field"
                        style={{ gridColumn: "1 / -1" }}
                      >
                        <span>Question Template</span>
                        <textarea
                          rows={4}
                          value={draft.execution.questionTemplate}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.execution.questionTemplate = e.target.value;
                              return c;
                            })
                          }
                        />
                      </label>
                    </div>
                  )}

                  {selectedSection === "output" && (
                    <div className="v4-grid">
                      <label className="v4-field">
                        <span>Post Mode</span>
                        <select
                          value={draft.output.postMode}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.output.postMode = e.target.value as PipelineDocument["output"]["postMode"];
                              return c;
                            })
                          }
                        >
                          {metadata?.output_post_modes.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="v4-field v4-check">
                        <input
                          type="checkbox"
                          checked={draft.output.includeArtifactsInNote}
                          onChange={(e) =>
                            updateDraft((c) => {
                              c.output.includeArtifactsInNote = e.target.checked;
                              return c;
                            })
                          }
                        />
                        <span>Include artifacts in note</span>
                      </label>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
