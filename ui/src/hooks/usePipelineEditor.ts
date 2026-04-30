import { useEffect, useMemo, useRef, useState } from "react";
import {
  createPipeline,
  deletePipeline,
  fetchMetadata,
  fetchPipeline,
  fetchPipelines,
  previewPipeline,
  savePipeline,
  validatePipeline,
} from "../api";
import type {
  MetadataResponse,
  PipelineDocument,
  PipelineSummary,
  PreviewResponse,
  ValidationResponse,
} from "../types";
import { buildFlow, cloneDocument } from "../lib/helpers";

export function usePipelineEditor() {
  const [metadata, setMetadata] = useState<MetadataResponse | null>(null);
  const [pipelines, setPipelines] = useState<PipelineSummary[]>([]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [draft, setDraft] = useState<PipelineDocument | null>(null);
  const [original, setOriginal] = useState<PipelineDocument | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [validation, setValidation] = useState<ValidationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dirty = useMemo(() => {
    if (!draft) return false;
    if (!original) return true;
    return JSON.stringify(draft) !== JSON.stringify(original);
  }, [draft, original]);

  useEffect(() => {
    async function load() {
      try {
        const [metadataResponse, pipelineSummaries] = await Promise.all([
          fetchMetadata(),
          fetchPipelines(),
        ]);
        setMetadata(metadataResponse);
        setPipelines(pipelineSummaries);

        const firstPipelineId = pipelineSummaries[0]?.id ?? null;
        if (!firstPipelineId) {
          setLoading(false);
          return;
        }

        setSelectedPipelineId(firstPipelineId);
        const pipeline = await fetchPipeline(firstPipelineId);
        setDraft(pipeline);
        setOriginal(cloneDocument(pipeline));
        const [previewResponse, validationResponse] = await Promise.all([
          previewPipeline(pipeline),
          validatePipeline(pipeline),
        ]);
        setPreview(previewResponse);
        setValidation(validationResponse);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load admin UI.");
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, []);

  const flow = useMemo(() => buildFlow(preview), [preview]);

  async function refreshPipelines() {
    const pipelineSummaries = await fetchPipelines();
    setPipelines(pipelineSummaries);
  }

  async function refreshMetadata() {
    const metadataResponse = await fetchMetadata();
    setMetadata(metadataResponse);
    return metadataResponse;
  }

  async function selectPipeline(pipelineId: string) {
    setSelectedPipelineId(pipelineId);
    setLoading(true);
    setError(null);
    try {
      const pipeline = await fetchPipeline(pipelineId);
      setDraft(pipeline);
      setOriginal(cloneDocument(pipeline));
      const [previewResponse, validationResponse] = await Promise.all([
        previewPipeline(pipeline),
        validatePipeline(pipeline),
      ]);
      setPreview(previewResponse);
      setValidation(validationResponse);
      setSaved(false);
    } catch (selectionError) {
      setError(
        selectionError instanceof Error
          ? selectionError.message
          : "Failed to load pipeline.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function refreshDerived(nextDraft: PipelineDocument) {
    const [previewResponse, validationResponse] = await Promise.all([
      previewPipeline(nextDraft),
      validatePipeline(nextDraft),
    ]);
    setPreview(previewResponse);
    setValidation(validationResponse);
  }

  function updateDraft(
    updater: (currentDraft: PipelineDocument) => PipelineDocument,
  ) {
    if (!draft) {
      return;
    }
    const nextDraft = updater(cloneDocument(draft));
    setDraft(nextDraft);
    setSaved(false);
    void refreshDerived(nextDraft).catch((refreshError) => {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Failed to refresh preview.",
      );
    });
  }

  async function saveDraft() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const savedDoc = original
        ? await savePipeline(original.id, draft)
        : await createPipeline(draft);
      setDraft(savedDoc);
      setOriginal(cloneDocument(savedDoc));
      setSaved(true);
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      savedTimerRef.current = setTimeout(() => setSaved(false), 2000);
      await refreshPipelines();
      setSelectedPipelineId(savedDoc.id);
    } catch (saveError) {
      setError(
        saveError instanceof Error ? saveError.message : "Failed to save pipeline.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function createNewPipeline() {
    setLoading(true);
    setError(null);
    try {
      const now = Date.now();
      const template: PipelineDocument = {
        id: `new-pipeline-${now}`,
        name: "New Pipeline",
        enabled: false,
        description: "",
        preset: "review",
        trigger: {
          type: "slash_command",
          scope: "merge_request",
          commandText: `/oc_custom_${now}`,
          mentionTarget: "@nid-bugbard",
        },
        filters: {
          projectAllowlist: [],
          branchPatterns: [],
          labelFilters: [],
          authorAllowlist: [],
          authorDenylist: [],
        },
        execution: {
          mode: "review",
          agentName: metadata?.agents[0] ?? "gitlab-review",
          modelName: metadata?.models[0] ?? "minimax/MiniMax-M2.7",
          questionTemplate: "{{note_body_without_trigger}}",
          timeoutSeconds: 1800,
          maxConcurrentRuns: 1,
        },
        workspace: {
          mode: "fresh_clone",
          cleanupAfterRun: true,
          checkoutStrategy: "source_branch",
        },
        preparation: {
          enableRepoHook: false,
          enableOpencodePreparation: false,
          allowDependencyInstall: false,
        },
        output: {
          postMode: "new_note",
          includeArtifactsInNote: true,
          keepEventsJsonl: true,
          keepRenderedReplyMarkdown: true,
        },
        stages: [],
        stepSettings: {},
        contextHandling: {},
        updatedAt: new Date().toISOString(),
      };
      setSelectedPipelineId(null);
      setDraft(template);
      setOriginal(null);
      const [previewResponse, validationResponse] = await Promise.all([
        previewPipeline(template),
        validatePipeline(template),
      ]);
      setPreview(previewResponse);
      setValidation(validationResponse);
      setSaved(false);
    } catch (createError) {
      setError(
        createError instanceof Error ? createError.message : "Failed to create pipeline.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function duplicateDraft() {
    if (!draft) return;
    setLoading(true);
    setError(null);
    try {
      const duplicated = cloneDocument(draft);
      duplicated.id = `${draft.id}-copy`;
      duplicated.name = `${draft.name} Copy`;
      duplicated.trigger.commandText = `${draft.trigger.commandText}_copy`;
      duplicated.updatedAt = new Date().toISOString();
      const created = await createPipeline(duplicated);
      await refreshPipelines();
      setSelectedPipelineId(created.id);
      setDraft(created);
      setOriginal(cloneDocument(created));
      const [previewResponse, validationResponse] = await Promise.all([
        previewPipeline(created),
        validatePipeline(created),
      ]);
      setPreview(previewResponse);
      setValidation(validationResponse);
      setSaved(false);
    } catch (duplicationError) {
      setError(
        duplicationError instanceof Error
          ? duplicationError.message
          : "Failed to duplicate pipeline.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function deleteCurrentPipeline() {
    if (!draft) return;
    if (!original) {
      setDraft(null);
      setPreview(null);
      setValidation(null);
      setSelectedPipelineId(null);
      const pipelineSummaries = await fetchPipelines();
      setPipelines(pipelineSummaries);
      const firstPipelineId = pipelineSummaries[0]?.id ?? null;
      if (firstPipelineId) {
        await selectPipeline(firstPipelineId);
      }
      return;
    }

    const pipelineId = original.id;
    setLoading(true);
    setError(null);
    try {
      await deletePipeline(pipelineId);
      setDraft(null);
      setOriginal(null);
      setPreview(null);
      setValidation(null);
      setSelectedPipelineId(null);
      await refreshPipelines();
      const pipelineSummaries = await fetchPipelines();
      setPipelines(pipelineSummaries);
      const firstPipelineId = pipelineSummaries[0]?.id ?? null;
      if (firstPipelineId) {
        await selectPipeline(firstPipelineId);
      } else {
        setLoading(false);
      }
    } catch (deletionError) {
      setError(
        deletionError instanceof Error ? deletionError.message : "Failed to delete pipeline.",
      );
      setLoading(false);
    }
  }

  return {
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
    flow,
    selectPipeline,
    updateDraft,
    saveDraft,
    createNewPipeline,
    duplicateDraft,
    deleteCurrentPipeline,
    refreshMetadata,
  };
}
