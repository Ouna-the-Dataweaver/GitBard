import type { Node, Edge } from "reactflow";
import { MarkerType } from "reactflow";
import type { PreviewResponse, PipelineDocument } from "../types";

export function cloneDocument<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function commaSeparated(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function buildFlow(preview: PreviewResponse | null): { nodes: Node[]; edges: Edge[] } {
  const stages = preview?.compiled_pipeline.stages ?? [];
  const nodes: Node[] = stages.map((stage, index) => ({
    id: stage,
    position: { x: 80 + index * 220, y: 90 },
    data: { label: stage },
    type: "default",
  }));
  const edges: Edge[] = stages.slice(1).map((stage, index) => ({
    id: `${stages[index]}-${stage}`,
    source: stages[index],
    target: stage,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
  }));
  return { nodes, edges };
}

export function buildEditableFlow(
  preview: PreviewResponse | null,
  draft: PipelineDocument | null,
): { nodes: Node[]; edges: Edge[] } {
  if (!preview || !draft) {
    return { nodes: [], edges: [] };
  }

  const compiledStages = preview.compiled_pipeline.stages;

  const sections: {
    key: string;
    label: string;
    stageFilter: (s: string) => boolean;
    summary: string;
  }[] = [
    {
      key: "basics",
      label: "Pipeline",
      stageFilter: () => false,
      summary: draft.name,
    },
    {
      key: "trigger",
      label: "Trigger",
      stageFilter: (s) => s === "IssueContextFetcherStage",
      summary: `${draft.trigger.type} / ${draft.trigger.scope}`,
    },
    {
      key: "filters",
      label: "Filters",
      stageFilter: (s) => s === "SnapshotResolverStage",
      summary: `${draft.filters.projectAllowlist.length} allowlisted`,
    },
    {
      key: "workspace",
      label: "Workspace",
      stageFilter: (s) => s === "WorkspaceAcquisitionStage",
      summary: draft.workspace.mode,
    },
    {
      key: "preparation",
      label: "Preparation",
      stageFilter: (s) =>
        ["HookResolverStage", "WorkspacePreparationStage"].includes(s),
      summary: draft.preparation.enableOpencodePreparation ? "Enabled" : "Disabled",
    },
    {
      key: "execution",
      label: "Execution",
      stageFilter: (s) => s === "OpencodeIntegrationStage",
      summary: draft.execution.agentName,
    },
    {
      key: "output",
      label: "Output",
      stageFilter: (s) => s === "NoteUpdaterStage",
      summary: draft.output.postMode,
    },
  ];

  const nodes: Node[] = sections.map((sec, index) => {
    const stages = compiledStages.filter(sec.stageFilter);
    return {
      id: sec.key,
      position: { x: 60 + index * 260, y: 120 },
      data: {
        label: sec.label,
        section: sec.key,
        stages,
        summary: sec.summary,
      },
      type: "pipelineNode",
    };
  });

  const edges: Edge[] = sections.slice(1).map((sec, index) => ({
    id: `${sections[index].key}-${sec.key}`,
    source: sections[index].key,
    target: sec.key,
    type: "smoothstep",
    markerEnd: { type: MarkerType.ArrowClosed },
  }));

  return { nodes, edges };
}
