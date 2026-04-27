import type { Node, Edge } from "reactflow";
import { MarkerType, Position } from "reactflow";
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
  {
    name: string;
    description: string;
    section: string | null;
    visualGroup: "repoPrep" | "agentRun" | "publishing" | "custom";
  }
> = {
  HookResolverStage: {
    name: "Hook Resolver",
    description: "Detect trigger commands",
    section: "preparation",
    visualGroup: "repoPrep",
  },
  SnapshotResolverStage: {
    name: "Snapshot Resolver",
    description: "Resolve code snapshot",
    section: "filters",
    visualGroup: "repoPrep",
  },
  WorkspaceAcquisitionStage: {
    name: "Workspace",
    description: "Clone workspace",
    section: "workspace",
    visualGroup: "repoPrep",
  },
  IssueContextFetcherStage: {
    name: "Context Fetcher",
    description: "Fetch issue context",
    section: "trigger",
    visualGroup: "agentRun",
  },
  WorkspacePreparationStage: {
    name: "Preparation",
    description: "Prepare workspace",
    section: "preparation",
    visualGroup: "repoPrep",
  },
  OpencodeIntegrationStage: {
    name: "OpenCode",
    description: "Run AI agent",
    section: "execution",
    visualGroup: "agentRun",
  },
  NoteUpdaterStage: {
    name: "Note Updater",
    description: "Post results",
    section: "output",
    visualGroup: "publishing",
  },
};

const VISUAL_GROUPS = [
  { id: "repoPrep", title: "Repo Prep", accent: "#a3e635" },
  { id: "agentRun", title: "Agent Run", accent: "#38bdf8" },
  { id: "publishing", title: "Publishing", accent: "#22c55e" },
  { id: "custom", title: "Custom", accent: "#a78bfa" },
] as const;

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
  selectedSection?: string | null,
): { nodes: Node[]; edges: Edge[] } {
  if (!preview || !draft) {
    return { nodes: [], edges: [] };
  }

  const stages = draft.stages ?? preview.compiled_pipeline.stages;

  const NODE_W = 240;
  const NODE_H = 66;
  const INSERT_SIZE = 28;
  const GROUP_X = 96;
  const GROUP_Y = 56;
  const GROUP_PAD_X = 28;
  const GROUP_PAD_TOP = 58;
  const GROUP_PAD_BOTTOM = 30;
  const GROUP_GAP_X = 64;
  const GROUP_W = NODE_W + GROUP_PAD_X * 2;
  const ROW_GAP = 26;

  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const stageLayouts: Array<{
    id: string;
    stage: string;
    index: number;
    x: number;
    y: number;
    label: string;
    section: string | null;
    summary: string;
    visualGroup: string;
    sourcePosition?: Position;
    targetPosition?: Position;
  }> = [];

  const groupedStages = new Map<
    string,
    Array<{
      stage: string;
      index: number;
      info: (typeof STAGE_CATALOG)[string] | undefined;
    }>
  >();

  stages.forEach((stage, index) => {
    const info = STAGE_CATALOG[stage];
    const groupId = info?.visualGroup ?? "custom";
    const group = groupedStages.get(groupId) ?? [];
    group.push({ stage, index, info });
    groupedStages.set(groupId, group);
  });

  let groupX = GROUP_X;
  for (const group of VISUAL_GROUPS) {
    const groupStages = groupedStages.get(group.id) ?? [];
    if (groupStages.length === 0) continue;

    const groupHeight =
      GROUP_PAD_TOP +
      groupStages.length * NODE_H +
      Math.max(0, groupStages.length - 1) * ROW_GAP +
      GROUP_PAD_BOTTOM;

    nodes.push({
      id: `visual-group-${group.id}`,
      position: { x: groupX, y: GROUP_Y },
      data: {
        title: group.title,
        count: groupStages.length,
        accent: group.accent,
        active: groupStages.some(
          ({ info }) => info?.section && info.section === selectedSection,
        ),
      },
      type: "stageGroup",
      draggable: false,
      selectable: false,
      connectable: false,
      zIndex: 0,
      style: { width: GROUP_W, height: groupHeight },
    });

    groupStages.forEach(({ stage, index, info }, localIndex) => {
      stageLayouts[index] = {
        id: `stage-${index}`,
        stage,
        index,
        x: groupX + GROUP_PAD_X,
        y: GROUP_Y + GROUP_PAD_TOP + localIndex * (NODE_H + ROW_GAP),
        label: info?.name ?? stage.replace("Stage", ""),
        section: info?.section ?? null,
        summary: info?.description ?? "",
        visualGroup: group.id,
      };
    });

    groupX += GROUP_W + GROUP_GAP_X;
  }

  for (let i = 0; i < stageLayouts.length - 1; i++) {
    const source = stageLayouts[i];
    const target = stageLayouts[i + 1];
    if (!source || !target) continue;

    const dx = target.x - source.x;
    const dy = target.y - source.y;
    if (source.visualGroup === target.visualGroup) {
      source.sourcePosition = Position.Bottom;
      target.targetPosition = Position.Top;
    } else if (Math.abs(dx) >= Math.abs(dy)) {
      source.sourcePosition = dx >= 0 ? Position.Right : Position.Left;
      target.targetPosition = dx >= 0 ? Position.Left : Position.Right;
    } else {
      source.sourcePosition = dy >= 0 ? Position.Bottom : Position.Top;
      target.targetPosition = dy >= 0 ? Position.Top : Position.Bottom;
    }

    edges.push({
      id: `${source.id}-${target.id}`,
      source: source.id,
      target: target.id,
      type: "smoothstep",
      markerEnd: { type: MarkerType.ArrowClosed },
    });
  }

  for (let i = 0; i <= stages.length; i++) {
    const previous = stageLayouts[i - 1];
    const next = stageLayouts[i];
    let insertX = GROUP_X - INSERT_SIZE - 20;
    let insertY = GROUP_Y + GROUP_PAD_TOP + NODE_H / 2 - INSERT_SIZE / 2;

    if (previous && next) {
      if (previous.visualGroup === next.visualGroup) {
        insertX = previous.x + NODE_W / 2 - INSERT_SIZE / 2;
        insertY = (previous.y + NODE_H + next.y) / 2 - INSERT_SIZE / 2;
      } else {
        insertX =
          (previous.x + NODE_W + next.x) / 2 - INSERT_SIZE / 2;
        insertY =
          (previous.y + NODE_H / 2 + next.y + NODE_H / 2) / 2 -
          INSERT_SIZE / 2;
      }
    } else if (previous) {
      insertX = previous.x + NODE_W + 22;
      insertY = previous.y + NODE_H / 2 - INSERT_SIZE / 2;
    } else if (next) {
      insertX = next.x - INSERT_SIZE - 22;
      insertY = next.y + NODE_H / 2 - INSERT_SIZE / 2;
    }

    const insertId = `insert-${i}`;
    nodes.push({
      id: insertId,
      position: { x: insertX, y: insertY },
      data: { isInsert: true, insertAtIndex: i },
      type: "insertNode",
      zIndex: 3,
    });
  }

  for (const layout of stageLayouts) {
    if (!layout) continue;
    nodes.push({
      id: layout.id,
      position: { x: layout.x, y: layout.y },
      data: {
        label: layout.label,
        section: layout.section,
        stages: [],
        summary: layout.summary,
        stageIndex: layout.index,
        visualGroup: layout.visualGroup,
        sourcePosition: layout.sourcePosition ?? Position.Right,
        targetPosition: layout.targetPosition ?? Position.Left,
      },
      type: "pipelineNode",
      zIndex: 2,
    });
  }

  return { nodes, edges };
}
