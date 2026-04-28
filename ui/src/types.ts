export type TriggerType =
  | "slash_command"
  | "mention"
  | "issue_event"
  | "merge_request_event";

export type Scope = "issue" | "merge_request" | "both";

export type PipelinePreset = "review" | "ask" | "test" | "deep_test";

export interface PipelineSummary {
  id: string;
  name: string;
  enabled: boolean;
  description: string;
  triggerType: TriggerType;
  triggerText: string;
  scope: Scope;
  preset: PipelinePreset;
  updatedAt: string;
}

export interface PipelineDocument {
  id: string;
  name: string;
  enabled: boolean;
  description: string;
  preset: PipelinePreset;
  trigger: {
    type: TriggerType;
    scope: Scope;
    commandText: string;
    mentionTarget: string;
  };
  filters: {
    projectAllowlist: string[];
    branchPatterns: string[];
    labelFilters: string[];
    authorAllowlist: string[];
    authorDenylist: string[];
  };
  execution: {
    mode: PipelinePreset;
    agentName: string;
    modelName: string;
    questionTemplate: string;
    timeoutSeconds: number;
    maxConcurrentRuns: number;
  };
  workspace: {
    mode: "fresh_clone";
    cleanupAfterRun: boolean;
    checkoutStrategy: "source_branch" | "explicit_ref";
  };
  preparation: {
    enableRepoHook: boolean;
    enableOpencodePreparation: boolean;
    allowDependencyInstall: boolean;
  };
  output: {
    postMode: "new_note" | "update_progress_note";
    includeArtifactsInNote: boolean;
    keepEventsJsonl: boolean;
    keepRenderedReplyMarkdown: boolean;
  };
  stages?: string[];
  stepSettings?: Record<string, Record<string, unknown>>;
  contextHandling?: Record<
    string,
    {
      passToNext?: boolean;
      writeToWorkspace?: boolean;
      filename?: string;
    }
  >;
  updatedAt: string;
}

export type StepConfigField = {
  key: string;
  label: string;
  type: "text" | "boolean" | "select" | "multi_select" | "agent" | "model";
  options?: string[];
  default?: unknown;
};

export interface AvailableStep {
  id: string;
  stageId: string;
  name: string;
  description: string;
  provider: string;
  category: string;
  requiredAfter: string[];
  requiredBefore: string[];
  configSchema: StepConfigField[];
  contextSchema: {
    consumes?: string[];
    produces?: string[];
    default?: {
      passToNext?: boolean;
      writeToWorkspace?: boolean;
      filename?: string;
    };
  };
}

export interface MetadataResponse {
  trigger_types: TriggerType[];
  scopes: Scope[];
  pipeline_presets: PipelinePreset[];
  agents: string[];
  agent_options?: Array<{ name: string; description: string }>;
  models: string[];
  model_options?: Array<{ name: string; provider: string }>;
  workspace_modes: string[];
  checkout_strategies: string[];
  output_post_modes: Array<"new_note" | "update_progress_note">;
  available_stages: Array<{ id: string; name: string; description: string }>;
  available_steps: AvailableStep[];
}

export interface OpenCodeSettings {
  available_model_options: Array<{ name: string; provider: string }>;
  selected_models: string[];
  last_model_reload_at: string | null;
  last_model_reload_error: string | null;
}

export interface ValidationResponse {
  valid: boolean;
  normalized: PipelineDocument;
  errors: string[];
  warnings: string[];
}

export interface PreviewResponse extends ValidationResponse {
  compiled_pipeline: {
    name: string;
    preset: PipelinePreset;
    trigger: {
      type: TriggerType;
      scope: Scope;
      text: string;
    };
    agent: string;
    model: string;
    stages: string[];
    stepSettings: Record<string, Record<string, unknown>>;
    contextHandling: NonNullable<PipelineDocument["contextHandling"]>;
  };
}
