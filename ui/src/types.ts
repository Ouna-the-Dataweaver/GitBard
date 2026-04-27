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
  updatedAt: string;
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
  };
}
