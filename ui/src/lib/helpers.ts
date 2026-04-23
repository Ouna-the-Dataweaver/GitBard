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

export const STAGE_CATALOG: Record<
  string,
  { name: string; description: string; section: string | null }
> = {
  HookResolverStage: {
    name: "Hook Resolver",
    description: "Detect trigger commands",
    section: "preparation",
  },
  SnapshotResolverStage: {
    name: "Snapshot Resolver",
    description: "Resolve code snapshot",
    section: "filters",
  },
  WorkspaceAcquisitionStage: {
    name: "Workspace",
    description: "Clone workspace",
    section: "workspace",
  },
  IssueContextFetcherStage: {
    name: "Context Fetcher",
    description: "Fetch issue context",
    section: "trigger",
  },
  WorkspacePreparationStage: {
    name: "Preparation",
    description: "Prepare workspace",
    section: "preparation",
  },
  OpencodeIntegrationStage: {
    name: "OpenCode",
    description: "Run AI agent",
    section: "execution",
  },
  NoteUpdaterStage: {
    name: "Note Updater",
    description: "Post results",
    section: "output",
  },
};

export function buildFlow(
  preview: PreviewResponse | null,
): { nodes: Node[]; edges: Edge[] } {
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

  const stages = draft.stages ?? preview.compiled_pipeline.stages;

  const NODE_Y = 120;
  const INSERT_Y = 143;
  const NODE_W = 220;
  const INSERT_SIZE = 26;
  const GAP = 30;

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  let x = 60;

  nodes.push({
    id: "basics",
    position: { x, y: NODE_Y },
    data: {
      label: "Pipeline",
      section: "basics",
      stages: [],
      summary: draft.name,
    },
    type: "pipelineNode",
  });

  let prevId = "basics";
  x += NODE_W + GAP;

  for (let i = 0; i <= stages.length; i++) {
    const insertId = `insert-${i}`;
    nodes.push({
      id: insertId,
      position: { x, y: INSERT_Y },
      data: { isInsert: true, insertAtIndex: i },
      type: "insertNode",
    });
    x += INSERT_SIZE + GAP;

    if (i < stages.length) {
      const stage = stages[i];
      const info = STAGE_CATALOG[stage];
      const stageId = `stage-${i}`;

      nodes.push({
        id: stageId,
        position: { x, y: NODE_Y },
        data: {
          label: info?.name ?? stage.replace("Stage", ""),
          section: info?.section ?? null,
          stages: [],
          summary: info?.description ?? "",
          stageIndex: i,
        },
        type: "pipelineNode",
      });

      edges.push({
        id: `${prevId}-${stageId}`,
        source: prevId,
        target: stageId,
        type: "smoothstep",
        markerEnd: { type: MarkerType.ArrowClosed },
      });

      prevId = stageId;
      x += NODE_W + GAP;
    }
  }

  return { nodes, edges };
}
