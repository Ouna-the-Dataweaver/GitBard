import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import ReactFlow, {
  Background,
  Handle,
  Position,
  type NodeProps,
  Panel,
  useReactFlow,
  useStore,
} from "reactflow";
import {
  fetchOpenCodeSettings,
  reloadOpenCodeModels,
  saveOpenCodeSettings,
} from "../api";
import { usePipelineEditor } from "../hooks/usePipelineEditor";
import { commaSeparated, buildEditableFlow } from "../lib/helpers";
import type { OpenCodeSettings, PipelineDocument } from "../types";
import "../styles/v4.css";

/* ------------------------------------------------------------------ */
/*  Icons                                                              */
/* ------------------------------------------------------------------ */
interface IconProps {
  size?: number;
  color?: string;
}

function IconPipeline({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="18" r="3" />
      <path d="M6 9v3a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3v3" />
    </svg>
  );
}

function IconPlug({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22v-5" />
      <path d="M15 8V2" />
      <path d="M9 8V2" />
      <path d="M15 8a3 3 0 0 1-3 3 3 3 0 0 1-3-3" />
      <path d="M12 17v-6" />
    </svg>
  );
}

function IconCamera({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
      <circle cx="12" cy="13" r="3" />
    </svg>
  );
}

function IconFolder({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconList({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="8" y1="6" x2="21" y2="6" />
      <line x1="8" y1="12" x2="21" y2="12" />
      <line x1="8" y1="18" x2="21" y2="18" />
      <line x1="3" y1="6" x2="3.01" y2="6" />
      <line x1="3" y1="12" x2="3.01" y2="12" />
      <line x1="3" y1="18" x2="3.01" y2="18" />
    </svg>
  );
}

function IconTerminal({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="4 17 10 11 4 5" />
      <line x1="12" y1="19" x2="20" y2="19" />
    </svg>
  );
}

function IconChat({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function IconChevronRight({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function IconCheckCircle({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function IconSave({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17 21 17 13 7 13 7 21" />
      <polyline points="7 3 7 8 15 8" />
    </svg>
  );
}

function IconCopy({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function IconTrash({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  );
}

function IconSearch({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function IconMinus({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconPlus({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function IconExpand({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 3H5a2 2 0 0 0-2 2v3" />
      <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
      <path d="M3 16v3a2 2 0 0 0 2 2h3" />
      <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function IconHand({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 11V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v0" />
      <path d="M14 10V4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v2" />
      <path d="M10 10.5V6a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v8" />
      <path d="M18 8a2 2 0 1 1 4 0v6a8 8 0 0 1-8 8h-2c-2.8 0-4.5-.86-5.99-2.34l-3.6-3.6a2 2 0 0 1 2.83-2.82L7 15" />
    </svg>
  );
}

function IconZoomIn({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="11" y1="8" x2="11" y2="14" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function IconZoomOut({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  );
}

function IconFitView({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 3h6v6" />
      <path d="M9 21H3v-6" />
      <path d="M21 3l-7 7" />
      <path d="M3 21l7-7" />
    </svg>
  );
}

function IconLock({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

function IconSettings({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.38a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.51a2 2 0 0 1 1-1.72l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function IconRefresh({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 0 1-15.5 6.2L3 16" />
      <path d="M3 21v-5h5" />
      <path d="M3 12A9 9 0 0 1 18.5 5.8L21 8" />
      <path d="M21 3v5h-5" />
    </svg>
  );
}

function IconFlask({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 2v7.31" />
      <path d="M14 2v7.31" />
      <path d="M8.5 2h7" />
      <path d="M14 9.3a6.5 6.5 0 1 1-4 0" />
      <path d="M5.52 16h12.96" />
    </svg>
  );
}

function IconLayers({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function IconAlertTriangle({ size = 20, color = "currentColor" }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Section metadata                                                   */
/* ------------------------------------------------------------------ */
const SECTION_META: Record<
  string,
  { color: string; Icon: React.FC<IconProps> }
> = {
  basics: { color: "#a78bfa", Icon: IconPipeline },
  trigger: { color: "#38bdf8", Icon: IconList },
  filters: { color: "#2dd4bf", Icon: IconCamera },
  workspace: { color: "#4ade80", Icon: IconFolder },
  preparation: { color: "#a3e635", Icon: IconPlug },
  execution: { color: "#34d399", Icon: IconTerminal },
  output: { color: "#22c55e", Icon: IconChat },
};

const PRESET_ICON: Record<string, React.FC<IconProps>> = {
  ask: IconPipeline,
  review: IconChat,
  test: IconFlask,
  deep_test: IconLayers,
};

/* ------------------------------------------------------------------ */
/*  Nodes                                                              */
/* ------------------------------------------------------------------ */
function PipelineNode({
  data,
  selected,
}: NodeProps<{
  label: string;
  section: string | null;
  stages: string[];
  summary: string;
  sourcePosition?: Position;
  targetPosition?: Position;
}>) {
  const meta = data.section ? SECTION_META[data.section] : SECTION_META.basics;
  const Icon = meta.Icon;
  return (
    <div
      className={`v4-node ${selected ? "v4-node-selected" : ""}`}
      style={{ ["--node-accent" as any]: meta.color }}
    >
      <Handle
        type="target"
        position={data.targetPosition ?? Position.Left}
        className="v4-handle"
        style={{ background: meta.color, borderColor: "#0b0f19" }}
      />
      <div className="v4-node-inner">
        <div
          className="v4-node-icon-wrap"
          style={{ background: `${meta.color}18`, color: meta.color }}
        >
          <Icon size={20} />
        </div>
        <div className="v4-node-body">
          <div className="v4-node-label" style={{ color: meta.color }}>
            {data.label}
          </div>
          <div className="v4-node-summary">{data.summary}</div>
        </div>
      </div>
      <Handle
        type="source"
        position={data.sourcePosition ?? Position.Right}
        className="v4-handle"
        style={{ background: meta.color, borderColor: "#0b0f19" }}
      />
    </div>
  );
}

function StageGroupNode({
  data,
}: NodeProps<{
  title: string;
  count: number;
  accent: string;
  active?: boolean;
}>) {
  return (
    <div
      className={`v4-stage-group ${data.active ? "v4-stage-group-active" : ""}`}
      style={{ ["--group-accent" as any]: data.accent }}
    >
      <div className="v4-stage-group-header">
        <span>{data.title}</span>
        <strong>{data.count}</strong>
      </div>
    </div>
  );
}

function InsertNode() {
  return (
    <div
      className="v4-insert-node"
      title="Add pipeline step"
      aria-label="Add pipeline step"
    >
      <span className="v4-insert-cross" aria-hidden="true" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step picker                                                        */
/* ------------------------------------------------------------------ */
function StepPickerModal({
  stages,
  onSelect,
  onClose,
}: {
  stages: Array<{ id: string; name: string; description: string }>;
  onSelect: (stageId: string) => void;
  onClose: () => void;
}) {
  return (
    <div className="v4-picker-overlay" onClick={onClose}>
      <div className="v4-picker" onClick={(e) => e.stopPropagation()}>
        <div className="v4-picker-header">
          <h3>Add Pipeline Step</h3>
          <button className="v4-btn-ghost" type="button" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="v4-picker-list">
          {stages.map((stage) => (
            <button
              key={stage.id}
              type="button"
              className="v4-picker-item"
              onClick={() => onSelect(stage.id)}
            >
              <div className="v4-picker-item-name">{stage.name}</div>
              <div className="v4-picker-item-desc">{stage.description}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  OpenCode picker                                                    */
/* ------------------------------------------------------------------ */
function OpenCodePicker({
  label,
  value,
  options,
  customLabel,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ name: string; detail?: string }>;
  customLabel: string;
  onChange: (value: string) => void;
}) {
  const [query, setQuery] = useState("");
  const normalizedQuery = query.trim().toLowerCase();
  const selectedKnown = options.some((option) => option.name === value);
  const filteredOptions = options.filter((option) => {
    if (!normalizedQuery) return true;
    return `${option.name} ${option.detail ?? ""}`
      .toLowerCase()
      .includes(normalizedQuery);
  });
  const canAddCustom = query.trim().length > 0 && query.trim() !== value;

  return (
    <div className="v4-field v4-opencode-picker">
      <span>{label}</span>
      <div className="v4-picker-current">
        <strong>{value || "Not set"}</strong>
        <small>{selectedKnown ? "Configured option" : "Custom entry"}</small>
      </div>
      <input
        value={query}
        placeholder={`Search or add ${label.toLowerCase()}`}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="v4-option-list">
        {filteredOptions.map((option) => (
          <button
            key={option.name}
            type="button"
            className={`v4-option-item ${option.name === value ? "v4-option-selected" : ""}`}
            onClick={() => {
              onChange(option.name);
              setQuery("");
            }}
          >
            <span>{option.name}</span>
            {option.detail ? <small>{option.detail}</small> : null}
          </button>
        ))}
        {canAddCustom && (
          <button
            type="button"
            className="v4-option-item v4-option-custom"
            onClick={() => {
              onChange(query.trim());
              setQuery("");
            }}
          >
            <span>{customLabel}</span>
            <small>{query.trim()}</small>
          </button>
        )}
        {!filteredOptions.length && !canAddCustom ? (
          <div className="v4-option-empty">No matches</div>
        ) : null}
      </div>
    </div>
  );
}

function OpenCodeSettingsModal({
  settings,
  busy,
  error,
  onClose,
  onReload,
  onSave,
}: {
  settings: OpenCodeSettings;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onReload: () => Promise<OpenCodeSettings>;
  onSave: (settings: OpenCodeSettings) => void;
}) {
  const [query, setQuery] = useState("");
  const [draftSettings, setDraftSettings] = useState(settings);
  const selected = new Set(draftSettings.selected_models);
  const normalizedQuery = query.trim().toLowerCase();
  const filteredModels = draftSettings.available_model_options.filter((option) => {
    if (!normalizedQuery) return true;
    return `${option.name} ${option.provider}`.toLowerCase().includes(normalizedQuery);
  });

  const toggleModel = (modelName: string) => {
    setDraftSettings((current) => {
      const nextSelected = new Set(current.selected_models);
      if (nextSelected.has(modelName)) {
        nextSelected.delete(modelName);
      } else {
        nextSelected.add(modelName);
      }
      return {
        ...current,
        selected_models: Array.from(nextSelected),
      };
    });
  };

  const replaceSettings = (nextSettings: OpenCodeSettings) => {
    setDraftSettings(nextSettings);
    setQuery("");
  };

  return (
    <div className="v4-settings-overlay" onClick={onClose}>
      <div className="v4-settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="v4-settings-header">
          <div>
            <div className="v4-eyebrow">OpenCode Settings</div>
            <h3>Visible Models</h3>
          </div>
          <button className="v4-btn-ghost" type="button" onClick={onClose}>
            &times;
          </button>
        </div>
        <div className="v4-settings-actions">
          <label className="v4-field v4-settings-search">
            <span>Search Models</span>
            <input
              value={query}
              placeholder="provider/model"
              onChange={(e) => setQuery(e.target.value)}
            />
          </label>
          <button
            className="v4-btn"
            type="button"
            disabled={busy}
            onClick={async () => {
              try {
                const nextSettings = await onReload();
                replaceSettings(nextSettings);
              } catch {
                // Error text is owned by the parent settings state.
              }
            }}
          >
            <IconRefresh size={14} />
            Reload
          </button>
        </div>
        {error || draftSettings.last_model_reload_error ? (
          <div className="v4-settings-error">
            {error ?? draftSettings.last_model_reload_error}
          </div>
        ) : null}
        <div className="v4-settings-count">
          {draftSettings.selected_models.length} of {draftSettings.available_model_options.length} models visible
        </div>
        <div className="v4-model-checklist">
          {filteredModels.map((option) => (
            <label key={option.name} className="v4-model-row">
              <input
                type="checkbox"
                checked={selected.has(option.name)}
                onChange={() => toggleModel(option.name)}
              />
              <span>
                <strong>{option.name}</strong>
                {option.provider ? <small>{option.provider}</small> : null}
              </span>
            </label>
          ))}
          {!filteredModels.length ? (
            <div className="v4-option-empty">No models match this search.</div>
          ) : null}
        </div>
        <div className="v4-settings-footer">
          <button className="v4-btn-ghost" type="button" onClick={onClose}>
            Cancel
          </button>
          <button
            className="v4-btn v4-btn-primary"
            type="button"
            disabled={busy || draftSettings.selected_models.length === 0}
            onClick={() => onSave(draftSettings)}
          >
            Save Models
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Zoom panel                                                         */
/* ------------------------------------------------------------------ */
function ZoomPanel() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  const zoom = useStore((s) => s.transform[2]);
  return (
    <Panel position="top-right" className="v4-zoom-panel">
      <button className="v4-zoom-btn" title="Search">
        <IconSearch size={14} />
      </button>
      <button className="v4-zoom-btn" onClick={() => zoomOut()} title="Zoom out">
        <IconMinus size={14} />
      </button>
      <span className="v4-zoom-level">{Math.round(zoom * 100)}%</span>
      <button className="v4-zoom-btn" onClick={() => zoomIn()} title="Zoom in">
        <IconPlus size={14} />
      </button>
      <button className="v4-zoom-btn" onClick={() => fitView()} title="Fit view">
        <IconExpand size={14} />
      </button>
    </Panel>
  );
}

/* ------------------------------------------------------------------ */
/*  Graph toolbar                                                      */
/* ------------------------------------------------------------------ */
function GraphToolbar() {
  const { zoomIn, zoomOut, fitView } = useReactFlow();
  return (
    <Panel position="top-left" className="v4-graph-toolbar">
      <button className="v4-tool-btn v4-tool-active" title="Pan">
        <IconHand size={16} />
      </button>
      <button
        className="v4-tool-btn"
        onClick={() => zoomIn()}
        title="Zoom in"
      >
        <IconZoomIn size={16} />
      </button>
      <button
        className="v4-tool-btn"
        onClick={() => zoomOut()}
        title="Zoom out"
      >
        <IconZoomOut size={16} />
      </button>
      <button
        className="v4-tool-btn"
        onClick={() => fitView()}
        title="Fit view"
      >
        <IconFitView size={16} />
      </button>
      <button className="v4-tool-btn" title="Lock">
        <IconLock size={16} />
      </button>
    </Panel>
  );
}

/* ------------------------------------------------------------------ */
/*  Node types & titles                                                */
/* ------------------------------------------------------------------ */
const nodeTypes = {
  stageGroup: StageGroupNode,
  pipelineNode: PipelineNode,
  insertNode: InsertNode,
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

function fmtDate(iso: string) {
  const d = new Date(iso);
  return (
    d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    }) +
    ", " +
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */
export default function V4GraphCentric() {
  const [selectedSection, setSelectedSection] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [insertAtIndex, setInsertAtIndex] = useState<number>(-1);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [opencodeSettings, setOpencodeSettings] =
    useState<OpenCodeSettings | null>(null);
  const [settingsBusy, setSettingsBusy] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(280);
  const isResizing = useRef(false);
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
    refreshMetadata,
  } = usePipelineEditor();

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      const newWidth = Math.min(Math.max(e.clientX, 200), 500);
      setSidebarWidth(newWidth);
    };
    const handleMouseUp = () => {
      isResizing.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const flow = useMemo(
    () => buildEditableFlow(preview, draft, selectedSection),
    [preview, draft, selectedSection],
  );
  const agentOptions = useMemo(
    () =>
      (metadata?.agent_options ?? metadata?.agents.map((name) => ({
        name,
        description: "",
      })) ?? []).map((option) => ({
        name: option.name,
        detail: option.description,
      })),
    [metadata],
  );
  const modelOptions = useMemo(
    () =>
      (metadata?.model_options ?? metadata?.models.map((name) => ({
        name,
        provider: "",
      })) ?? []).map((option) => ({
        name: option.name,
        detail: option.provider ? `Provider: ${option.provider}` : "",
      })),
    [metadata],
  );

  const onNodeClick = useCallback(
    (
      _event: unknown,
      node: {
        data?: { section?: string; isInsert?: boolean; insertAtIndex?: number };
      },
    ) => {
      if (node.data?.isInsert) {
        setInsertAtIndex(node.data.insertAtIndex ?? 0);
        setPickerOpen(true);
        return;
      }
      if (node.data?.section) {
        setSelectedSection(node.data.section);
      }
    },
    [],
  );

  const handleAddStage = useCallback(
    (stageId: string) => {
      if (!draft || !preview) return;
      const currentStages =
        draft.stages ?? preview.compiled_pipeline.stages;
      const newStages = [...currentStages];
      newStages.splice(insertAtIndex, 0, stageId);
      updateDraft((c) => {
        c.stages = newStages;
        return c;
      });
      setPickerOpen(false);
    },
    [draft, preview, insertAtIndex, updateDraft],
  );

  const handleRemoveStage = useCallback(
    (stageIndex: number) => {
      if (!draft || !preview) return;
      const currentStages =
        draft.stages ?? preview.compiled_pipeline.stages;
      if (currentStages.length <= 1) return;
      const newStages = [...currentStages];
      newStages.splice(stageIndex, 1);
      updateDraft((c) => {
        c.stages = newStages;
        return c;
      });
    },
    [draft, preview, updateDraft],
  );

  const openSettings = useCallback(async () => {
    setSettingsOpen(true);
    setSettingsBusy(true);
    setSettingsError(null);
    try {
      const settings = await fetchOpenCodeSettings();
      setOpencodeSettings(settings);
    } catch (settingsLoadError) {
      setSettingsError(
        settingsLoadError instanceof Error
          ? settingsLoadError.message
          : "Failed to load OpenCode settings.",
      );
    } finally {
      setSettingsBusy(false);
    }
  }, []);

  const handleReloadModels = useCallback(async () => {
    setSettingsBusy(true);
    setSettingsError(null);
    try {
      const settings = await reloadOpenCodeModels();
      setOpencodeSettings(settings);
      await refreshMetadata();
      return settings;
    } catch (reloadError) {
      const message =
        reloadError instanceof Error
          ? reloadError.message
          : "Failed to reload OpenCode models.";
      setSettingsError(message);
      throw new Error(message);
    } finally {
      setSettingsBusy(false);
    }
  }, [refreshMetadata]);

  const handleSaveSettings = useCallback(
    async (settings: OpenCodeSettings) => {
      setSettingsBusy(true);
      setSettingsError(null);
      try {
        const savedSettings = await saveOpenCodeSettings({
          available_model_options: settings.available_model_options,
          selected_models: settings.selected_models,
        });
        setOpencodeSettings(savedSettings);
        await refreshMetadata();
        setSettingsOpen(false);
      } catch (saveError) {
        setSettingsError(
          saveError instanceof Error
            ? saveError.message
            : "Failed to save OpenCode settings.",
        );
      } finally {
        setSettingsBusy(false);
      }
    },
    [refreshMetadata],
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
    <div className="v4-app" style={{ gridTemplateColumns: `${sidebarWidth}px 4px 1fr` }}>
      <aside className="v4-sidebar">
        <div className="v4-sidebar-header">
          <h1>Pipeline Admin</h1>
          <p>Graph-centric editor</p>
        </div>
        <button
          className="v4-btn v4-btn-primary"
          type="button"
          onClick={() => void createNewPipeline()}
        >
          <IconPlus size={14} />
          New Pipeline
        </button>
        <div className="v4-pipeline-list">
          {pipelines.map((pipeline) => {
            const PresetIcon = PRESET_ICON[pipeline.preset] || IconPipeline;
            return (
              <button
                key={pipeline.id}
                type="button"
                className={`v4-pipeline-item ${selectedPipelineId === pipeline.id ? "v4-selected" : ""}`}
                onClick={() => void selectPipeline(pipeline.id)}
              >
                <div className="v4-pipeline-card">
                  <div className="v4-pipeline-card-icon">
                    <PresetIcon size={18} color="#a78bfa" />
                  </div>
                  <div className="v4-pipeline-card-body">
                    <div className="v4-pipeline-card-top">
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
                  </div>
                  <div className="v4-pipeline-card-chevron">
                    <IconChevronRight size={16} color="#64748b" />
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      <div
        className="v4-resize-handle"
        onMouseDown={() => {
          isResizing.current = true;
          document.body.style.cursor = "col-resize";
          document.body.style.userSelect = "none";
        }}
        title="Resize sidebar"
      />

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
                  {draft.enabled ? (
                    <IconCheckCircle size={12} />
                  ) : null}
                  {draft.enabled ? "Enabled" : "Disabled"}
                </span>
                {dirty && (
                  <span
                    className="v4-unsaved-dot"
                    title="Unsaved changes"
                  />
                )}
                <button
                  className="v4-btn"
                  type="button"
                  onClick={() => void openSettings()}
                >
                  <IconSettings size={14} />
                  Settings
                </button>
                <button
                  className="v4-btn v4-btn-primary"
                  type="button"
                  disabled={saving || !dirty}
                  onClick={() => void saveDraft()}
                >
                  <IconSave size={14} />
                  {saving ? "Saving…" : saved ? "Saved" : "Save"}
                </button>
                <button
                  className="v4-btn"
                  type="button"
                  onClick={() => void duplicateDraft()}
                >
                  <IconCopy size={14} />
                  Duplicate
                </button>
                <button
                  className="v4-btn v4-btn-danger"
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    if (confirm("Delete this pipeline?"))
                      void deleteCurrentPipeline();
                  }}
                >
                  <IconTrash size={14} />
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
                <Background gap={18} size={1} />
                <ZoomPanel />
                <GraphToolbar />
              </ReactFlow>
              {pickerOpen && metadata && (
                <StepPickerModal
                  stages={metadata.available_stages}
                  onSelect={handleAddStage}
                  onClose={() => setPickerOpen(false)}
                />
              )}
              {settingsOpen && (
                <div className="v4-settings-layer">
                  {opencodeSettings ? (
                    <OpenCodeSettingsModal
                      settings={opencodeSettings}
                      busy={settingsBusy}
                      error={settingsError}
                      onClose={() => setSettingsOpen(false)}
                      onReload={handleReloadModels}
                      onSave={(settings) => void handleSaveSettings(settings)}
                    />
                  ) : (
                    <div className="v4-settings-overlay">
                      <div className="v4-settings-modal v4-settings-loading">
                        {settingsError ?? "Loading OpenCode settings..."}
                        <button
                          className="v4-btn-ghost"
                          type="button"
                          onClick={() => setSettingsOpen(false)}
                        >
                          Close
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="v4-editor">
              {!selectedSection ? (
                <div className="v4-editor-placeholder">
                  <div className="v4-pipeline-details">
                    <div className="v4-details-header">
                      <div
                        className="v4-details-icon"
                        style={{
                          background: "rgba(167, 139, 250, 0.12)",
                          color: "#a78bfa",
                        }}
                      >
                        <IconPipeline size={28} color="#a78bfa" />
                      </div>
                      <div className="v4-details-title">
                        <div className="v4-details-eyebrow">
                          Pipeline Details
                        </div>
                        <div className="v4-details-name">
                          {draft.name}
                          <span
                            className={`v4-status ${draft.enabled ? "v4-on" : "v4-off"}`}
                          >
                            {draft.enabled ? (
                              <IconCheckCircle size={12} />
                            ) : null}
                            {draft.enabled ? "Enabled" : "Disabled"}
                          </span>
                        </div>
                        <div className="v4-details-desc">
                          {draft.description || "No description provided."}
                        </div>
                      </div>
                    </div>
                    <div className="v4-details-meta">
                      <div className="v4-meta-row">
                        <span>Trigger</span>
                        <span>
                          {draft.trigger.commandText} / {draft.trigger.scope}
                        </span>
                      </div>
                      <div className="v4-meta-row">
                        <span>Preset</span>
                        <span>{draft.preset}</span>
                      </div>
                      <div className="v4-meta-row">
                        <span>Updated</span>
                        <span>{fmtDate(draft.updatedAt)}</span>
                      </div>
                      <div className="v4-meta-row">
                        <span>ID</span>
                        <span>{draft.id}</span>
                      </div>
                    </div>
                  </div>
                  <div className="v4-feedback-inline">
                    <div className="v4-feedback-block v4-feedback-valid">
                      <h3>
                        <IconCheckCircle size={14} color="#34d399" />
                        Validation
                      </h3>
                      <ul>
                        {(validation?.errors.length
                          ? validation.errors
                          : ["No validation errors."]
                        ).map((m) => (
                          <li key={m}>{m}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="v4-feedback-block v4-feedback-warn">
                      <h3>
                        <IconAlertTriangle size={14} color="#fbbf24" />
                        Warnings
                      </h3>
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
                    <h3>
                      {sectionTitles[selectedSection] ?? selectedSection}
                    </h3>
                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "center",
                      }}
                    >
                      {(() => {
                        const allStages =
                          draft.stages ??
                          preview?.compiled_pipeline.stages ??
                          [];
                        const stageNodesInSameSection = flow.nodes.filter(
                          (n) =>
                            n.data?.section === selectedSection &&
                            n.data?.stageIndex !== undefined,
                        );
                        if (
                          stageNodesInSameSection.length > 0 &&
                          allStages.length > 1
                        ) {
                          return (
                            <button
                              className="v4-btn v4-btn-danger"
                              type="button"
                              style={{
                                fontSize: "0.65rem",
                                padding: "4px 10px",
                              }}
                              onClick={() => {
                                const idx =
                                  stageNodesInSameSection[0].data.stageIndex;
                                void handleRemoveStage(idx);
                              }}
                            >
                              Remove Step
                            </button>
                          );
                        }
                        return null;
                      })()}
                      <button
                        className="v4-btn-ghost"
                        type="button"
                        onClick={() => setSelectedSection(null)}
                      >
                        Close
                      </button>
                    </div>
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
                              c.preparation.enableRepoHook =
                                e.target.checked;
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
                      <OpenCodePicker
                        label="Agent"
                        value={draft.execution.agentName}
                        options={agentOptions}
                        customLabel="Use custom agent"
                        onChange={(value) =>
                          updateDraft((c) => {
                            c.execution.agentName = value;
                            return c;
                          })
                        }
                      />
                      <OpenCodePicker
                        label="Model"
                        value={draft.execution.modelName}
                        options={modelOptions}
                        customLabel="Add custom model"
                        onChange={(value) =>
                          updateDraft((c) => {
                            c.execution.modelName = value;
                            return c;
                          })
                        }
                      />
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
                              c.output.includeArtifactsInNote =
                                e.target.checked;
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
