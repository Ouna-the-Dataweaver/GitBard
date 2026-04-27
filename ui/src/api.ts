import type {
  MetadataResponse,
  OpenCodeSettings,
  PipelineDocument,
  PipelineSummary,
  PreviewResponse,
  ValidationResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchMetadata(): Promise<MetadataResponse> {
  return request<MetadataResponse>("/api/admin/metadata");
}

export function fetchOpenCodeSettings(): Promise<OpenCodeSettings> {
  return request<OpenCodeSettings>("/api/admin/settings/opencode");
}

export function saveOpenCodeSettings(
  settings: Pick<OpenCodeSettings, "available_model_options" | "selected_models">,
): Promise<OpenCodeSettings> {
  return request<OpenCodeSettings>("/api/admin/settings/opencode", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export function reloadOpenCodeModels(): Promise<OpenCodeSettings> {
  return request<OpenCodeSettings>("/api/admin/settings/opencode/reload-models", {
    method: "POST",
  });
}

export async function fetchPipelines(): Promise<PipelineSummary[]> {
  const payload = await request<{ pipelines: PipelineSummary[] }>("/api/admin/pipelines");
  return payload.pipelines;
}

export function fetchPipeline(pipelineId: string): Promise<PipelineDocument> {
  return request<PipelineDocument>(`/api/admin/pipelines/${pipelineId}`);
}

export function previewPipeline(pipeline: PipelineDocument): Promise<PreviewResponse> {
  return request<PreviewResponse>("/api/admin/pipelines/preview", {
    method: "POST",
    body: JSON.stringify(pipeline),
  });
}

export function validatePipeline(
  pipeline: PipelineDocument,
): Promise<ValidationResponse> {
  return request<ValidationResponse>("/api/admin/pipelines/validate", {
    method: "POST",
    body: JSON.stringify(pipeline),
  });
}

export function savePipeline(
  pipelineId: string,
  pipeline: PipelineDocument,
): Promise<PipelineDocument> {
  return request<PipelineDocument>(`/api/admin/pipelines/${pipelineId}`, {
    method: "PUT",
    body: JSON.stringify(pipeline),
  });
}

export function createPipeline(
  pipeline: PipelineDocument,
): Promise<PipelineDocument> {
  return request<PipelineDocument>("/api/admin/pipelines", {
    method: "POST",
    body: JSON.stringify(pipeline),
  });
}

export function deletePipeline(pipelineId: string): Promise<{ status: string; pipeline_id: string }> {
  return request<{ status: string; pipeline_id: string }>(`/api/admin/pipelines/${pipelineId}`, {
    method: "DELETE",
  });
}
