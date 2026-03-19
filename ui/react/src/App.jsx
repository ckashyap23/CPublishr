import React, { useEffect, useMemo, useRef, useState } from "react";
import ArtifactGeneratorPanel from "./components/ArtifactGeneratorPanel";
import EditorialWorkspace from "./components/EditorialWorkspace";
import PublishPanel from "./components/PublishPanel";
import SetupContentForm from "./components/SetupContentForm";
import VoiceProfilesSettings from "./components/VoiceProfilesSettings";
import {
  API_BASE_DEFAULT,
  AUDIENCE_FAMILIARITY_OPTIONS,
  AUDIENCE_OPTIONS,
  CORE_IDEA_SUGGESTION,
  DESIRED_ACTION_OPTIONS,
  DETAIL_LEVEL_OPTIONS,
  FORMAT_ADVANCED_DEFAULTS,
  PRIMARY_GOAL_OPTIONS,
  STANCE_OPTIONS,
  TONE_OPTIONS,
  TOPIC_TITLE_SUGGESTION,
  USER_CONTENT_SUGGESTION,
} from "./lib/appConstants";
import {
  apiRequest,
  artifactFormatMeta,
  artifactHasTags,
  autoResizeTextarea,
  clampInt,
  defaultPublishPartForArtifact,
  encodePathSegment,
  getVersionLabel,
  humorLabelToSlider,
  humorSliderToLabel,
  makeDefaultFormatAdvancedSettings,
  makeDefaultImageStyleSettings,
  makeDefaultToneNuance,
  makeDefaultVideoStyleSettings,
  makePublishSourceRow,
  normalizeVoiceProfilePreview,
  orderArtifactFormats,
  pickLatestImageStyleSeed,
  toneBaseFromProjectTone,
  uniqueStrings,
} from "./lib/appUtils";
import publishrLogo from "./publishr_logo.png";

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState(API_BASE_DEFAULT);
  const [authToken, setAuthToken] = useState(() => window.localStorage.getItem("cpublishr_token") || "");
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ user_id: "", email: "", password: "" });
  const [currentUser, setCurrentUser] = useState(null);
  const [page, setPage] = useState("setup");
  const [busy, setBusy] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [nodeAudit, setNodeAudit] = useState([]);
  const [canContinueToEditorial, setCanContinueToEditorial] = useState(false);
  const [hasExistingContent, setHasExistingContent] = useState(false);
  const [isCheckingProjectData, setIsCheckingProjectData] = useState(false);
  const [showGenerateSetupForm, setShowGenerateSetupForm] = useState(true);

  const [form, setForm] = useState({
    project_id: "proj_local_1",
    topic_title: "",
    core_idea: "",
    user_content: "",
    target_audience_segment: "general",
    target_audience_notes: "",
    audience_familiarity: "somewhat_familiar",
    detail_level: "quick_take",
    tone_preference: "conversational",
    stance: "balanced",
    primary_goal: "community",
    desired_action: "comment",
    voice_profile_id: "",
    distribution_targets: ["x", "instagram"],
  });

  const [versions, setVersions] = useState([]);
  const [selectedVersionNumber, setSelectedVersionNumber] = useState(null);
  const [keywordsInput, setKeywordsInput] = useState("");
  const [workingContent, setWorkingContent] = useState("");
  const [feedbackText, setFeedbackText] = useState("Improve clarity and tighten repetitive sections.");
  const [feedbackPreviewContent, setFeedbackPreviewContent] = useState("");
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [editorMode, setEditorMode] = useState("none"); // none | inline | iterate
  const [selectedArtifactFormats, setSelectedArtifactFormats] = useState([]);
  const [artifactFormatsByKind, setArtifactFormatsByKind] = useState({});
  const [artifactOutput, setArtifactOutput] = useState(null);
  const [selectedArtifactTab, setSelectedArtifactTab] = useState(0);
  const [storedArtifacts, setStoredArtifacts] = useState([]);
  const [selectedStoredFormat, setSelectedStoredFormat] = useState("");
  const [selectedStoredArtifactTab, setSelectedStoredArtifactTab] = useState(0);
  const [isArtifactGenerating, setIsArtifactGenerating] = useState(false);
  const [isStoredArtifactsLoading, setIsStoredArtifactsLoading] = useState(false);
  const [hasStoredArtifactsForProject, setHasStoredArtifactsForProject] = useState(false);
  const [isCheckingStoredArtifacts, setIsCheckingStoredArtifacts] = useState(false);
  const [storedArtifactFormatsForProject, setStoredArtifactFormatsForProject] = useState([]);
  const [artifactsViewMode, setArtifactsViewMode] = useState("");
  const [artifactGenerateStep, setArtifactGenerateStep] = useState("formats");
  const [artifactStyleSource, setArtifactStyleSource] = useState("manual");
  const [artifactStyleVoiceProfileId, setArtifactStyleVoiceProfileId] = useState("");
  const [artifactStyleVoiceProfileDetail, setArtifactStyleVoiceProfileDetail] = useState(null);
  const [isArtifactStyleVoiceProfileLoading, setIsArtifactStyleVoiceProfileLoading] = useState(false);
  const [artifactManualCoreVoice, setArtifactManualCoreVoice] = useState("");
  const [artifactToneNuance, setArtifactToneNuance] = useState(() => makeDefaultToneNuance("conversational"));
  const [artifactFrameworkMode, setArtifactFrameworkMode] = useState("light");
  const [artifactFormatAdvanced, setArtifactFormatAdvanced] = useState(() => makeDefaultFormatAdvancedSettings());
  const [artifactAdvancedOpen, setArtifactAdvancedOpen] = useState({});
  const [artifactImageStyle, setArtifactImageStyle] = useState(() => makeDefaultImageStyleSettings());
  const [artifactImageAvoidInput, setArtifactImageAvoidInput] = useState("");
  const [artifactVideoStyle, setArtifactVideoStyle] = useState(() => makeDefaultVideoStyleSettings());
  const [artifactVideoAvoidInput, setArtifactVideoAvoidInput] = useState("");
  const [artifactSuggestions, setArtifactSuggestions] = useState(null); // null = not loaded, {} = loaded (may be empty)
  const [artifactSuggestionsLoading, setArtifactSuggestionsLoading] = useState(false);
  const [artifactStyleKindPanel, setArtifactStyleKindPanel] = useState("text");
  const [publishPlatforms, setPublishPlatforms] = useState([]);
  const [isPublishPlatformsLoading, setIsPublishPlatformsLoading] = useState(false);
  const [publishSelectedPlatform, setPublishSelectedPlatform] = useState("");
  const [publishFieldSchema, setPublishFieldSchema] = useState([]);
  const [isPublishFieldSchemaLoading, setIsPublishFieldSchemaLoading] = useState(false);
  const [publishArtifacts, setPublishArtifacts] = useState([]);
  const [isPublishArtifactsLoading, setIsPublishArtifactsLoading] = useState(false);
  const [publishFieldMappings, setPublishFieldMappings] = useState({});
  const [publishSaveMessage, setPublishSaveMessage] = useState("");
  const [showPublishSaveDialog, setShowPublishSaveDialog] = useState(false);
  const [publishSaveUserName, setPublishSaveUserName] = useState("");
  const [publishSaveDestinationMode, setPublishSaveDestinationMode] = useState(() => {
    const raw = window.localStorage.getItem("cpublishr_publish_destination_mode") || "download";
    return ["url", "local", "download"].includes(raw) ? raw : "download";
  }); // url | local | download
  const [publishSaveOutputPath, setPublishSaveOutputPath] = useState(
    () => window.localStorage.getItem("cpublishr_publish_output_path") || ""
  );
  const [publishBrowseCurrentPath, setPublishBrowseCurrentPath] = useState("");
  const [publishBrowseParentPath, setPublishBrowseParentPath] = useState("");
  const [publishBrowseDirectories, setPublishBrowseDirectories] = useState([]);
  const [isPublishBrowsingPaths, setIsPublishBrowsingPaths] = useState(false);
  const [isPublishPickingLocalPath, setIsPublishPickingLocalPath] = useState(false);
  const [artifactEditMode, setArtifactEditMode] = useState("none"); // none | inline | iterate
  const [isArtifactEditing, setIsArtifactEditing] = useState(false);
  const [artifactInlineText, setArtifactInlineText] = useState("");
  const [artifactIterateInstruction, setArtifactIterateInstruction] = useState("");
  const [artifactIterateStyleSource, setArtifactIterateStyleSource] = useState("manual");
  const [artifactIterateVoiceProfileId, setArtifactIterateVoiceProfileId] = useState("");
  const [artifactIterateManualCoreVoice, setArtifactIterateManualCoreVoice] = useState("");
  const [artifactIterateToneNuance, setArtifactIterateToneNuance] = useState(() => makeDefaultToneNuance("conversational"));
  const [artifactIterateFrameworkMode, setArtifactIterateFrameworkMode] = useState("light");
  const [artifactIterateFormatAdvanced, setArtifactIterateFormatAdvanced] = useState(() => makeDefaultFormatAdvancedSettings());
  const [artifactIterateImageStyle, setArtifactIterateImageStyle] = useState(() => ({
    medium: "illustration",
    texture: "clean",
    lighting: "soft_daylight",
    palette_mode: "muted",
    mood: "premium",
    focus_negative_space: "subject_centered",
    output_fidelity: "standard",
    brand_colors: {
      primary: "#0F172A",
      secondary: "#1D4ED8",
      accent: "#22C55E",
      background: "#F8FAFC",
    },
  }));
  const [artifactIterateVideoStyle, setArtifactIterateVideoStyle] = useState(() => ({
    mood: "energetic",
    lighting: "soft_daylight",
    palette_mode: "muted",
    output_fidelity: "standard",
    camera_motion: "",
    energy_level: "medium",
    brand_colors: {
      primary: "#0F172A",
      secondary: "#1D4ED8",
      accent: "#22C55E",
      background: "#F8FAFC",
    },
  }));
  const [editingArtifactTitleId, setEditingArtifactTitleId] = useState("");
  const [editingArtifactTitleValue, setEditingArtifactTitleValue] = useState("");
  const [isSavingArtifactTitle, setIsSavingArtifactTitle] = useState(false);

  const [vpCollections, setVpCollections] = useState([]);
  const [vpProfilesIndex, setVpProfilesIndex] = useState([]);
  const [vpSelectedCollectionId, setVpSelectedCollectionId] = useState("");
  const [vpCollectionDetail, setVpCollectionDetail] = useState(null);
  const [vpSelectedProfileId, setVpSelectedProfileId] = useState("");
  const [vpProfileDetail, setVpProfileDetail] = useState(null);
  const [vpProfileComposerMode, setVpProfileComposerMode] = useState("hidden");
  const [vpCheckedProfileIds, setVpCheckedProfileIds] = useState([]);
  const [vpSelectedVersionId, setVpSelectedVersionId] = useState("");
  const [vpVersionDetail, setVpVersionDetail] = useState(null);
  const [showVpCreateCollectionForm, setShowVpCreateCollectionForm] = useState(false);
  const [vpCreateForm, setVpCreateForm] = useState({ collection_name: "", platforms: ["linkedin"] });
  const [vpDatasetForm, setVpDatasetForm] = useState({ dataset_name: "", source_profile: "", blob_prefix: "", sample_scope_note: "" });
  const [vpDatasetSourceMode, setVpDatasetSourceMode] = useState(() => {
    const raw = window.localStorage.getItem("cpublishr_vp_dataset_source_mode") || "azure";
    return raw === "local" ? "local" : "azure";
  });
  const [isVpPickingLocalDatasetPath, setIsVpPickingLocalDatasetPath] = useState(false);
  const [vpDatasetLocalFiles, setVpDatasetLocalFiles] = useState([]);
  const [vpProfileForm, setVpProfileForm] = useState({ voice_profile_name: "", intended_use: "" });
  const [vpGenerateForm, setVpGenerateForm] = useState({
    intended_use: "",
    dataset_ids: [],
  });
  const [vpStatusInput, setVpStatusInput] = useState("approved");
  const [isVpGenerating, setIsVpGenerating] = useState(false);
  const [userProjects, setUserProjects] = useState([]);
  const [isProjectsLoading, setIsProjectsLoading] = useState(false);
  const [hasManuallyEditedProjectId, setHasManuallyEditedProjectId] = useState(false);
  const [isCreatingNewProject, setIsCreatingNewProject] = useState(false);
  const contentCheckSeqRef = useRef(0);
  const storedArtifactsCheckSeqRef = useRef(0);
  const artifactStyleSeedFetchRef = useRef("");
  const artifactInlineTextareaRef = useRef(null);
  const artifactIterateInstructionTextareaRef = useRef(null);
  const artifactIterateVoiceStyleTextareaRef = useRef(null);
  const editorialInlineTextareaRef = useRef(null);
  const editorialFeedbackTextareaRef = useRef(null);
  const userContentTextareaRef = useRef(null);
  const isAuthenticated = !!authToken;
  const currentProjectSummary = useMemo(() => {
    const current = String(form.project_id || "").trim();
    if (!current) return null;
    return userProjects.find((p) => String(p?.project_id || "").trim() === current) || null;
  }, [userProjects, form.project_id]);
  const isExistingProjectFlow = isAuthenticated && !!currentProjectSummary && !isCreatingNewProject;
  const finalizedVersionBanner = useMemo(() => {
    const finalVersionNumber = Number(currentProjectSummary?.final_version_number);
    const list = Array.isArray(versions) ? versions : [];
    const fromProject = Number.isFinite(finalVersionNumber)
      ? list.find((v) => Number(v?.version_number) === finalVersionNumber) || null
      : null;
    const fallbackFinal = fromProject || [...list]
      .filter((v) => String(v?.version_stage || "").trim().toLowerCase() === "final")
      .sort((a, b) => Number(b?.version_number || 0) - Number(a?.version_number || 0))[0] || null;
    if (!fallbackFinal) return "";
    return `Finalized content: ${getVersionLabel(fallbackFinal)} (v${fallbackFinal.version_number})`;
  }, [versions, currentProjectSummary]);
  const selectedVoiceProfiles = useMemo(() => {
    const ids = new Set(Array.isArray(vpCheckedProfileIds) ? vpCheckedProfileIds : []);
    return (Array.isArray(vpCollectionDetail?.voice_profiles) ? vpCollectionDetail.voice_profiles : []).filter((p) =>
      ids.has(p.voice_profile_id)
    );
  }, [vpCheckedProfileIds, vpCollectionDetail]);
  const hasSelectedActiveVoiceProfiles = useMemo(
    () => selectedVoiceProfiles.some((p) => p?.is_enabled !== false),
    [selectedVoiceProfiles]
  );
  const hasSelectedInactiveVoiceProfiles = useMemo(
    () => selectedVoiceProfiles.some((p) => p?.is_enabled === false),
    [selectedVoiceProfiles]
  );
  const vpSelectedProfileSummary = useMemo(() => {
    const profiles = Array.isArray(vpCollectionDetail?.voice_profiles) ? vpCollectionDetail.voice_profiles : [];
    return profiles.find((p) => p.voice_profile_id === vpSelectedProfileId) || null;
  }, [vpCollectionDetail, vpSelectedProfileId]);
  const topBannerMessage = useMemo(() => {
    if (page === "settings") {
      return "";
    }
    if ((page === "artifacts" || page === "publish") && finalizedVersionBanner) {
      return finalizedVersionBanner;
    }
    return message;
  }, [page, finalizedVersionBanner, message]);

  const selectedVersion = useMemo(
    () => versions.find((v) => v.version_number === selectedVersionNumber) || null,
    [versions, selectedVersionNumber]
  );
  const nodeProgress = useMemo(() => {
    if (!isGenerating) return 0;
    const total = 3;
    const done = nodeAudit.filter((x) => x.status === "completed").length;
    return Math.min(100, Math.round((done / total) * 100));
  }, [isGenerating, nodeAudit]);
  const generatedArtifacts = useMemo(() => {
    if (!artifactOutput || !Array.isArray(artifactOutput.artifacts)) return [];
    return artifactOutput.artifacts;
  }, [artifactOutput]);
  const selectedGeneratedArtifact = generatedArtifacts[selectedArtifactTab] || null;
  const latestProjectImageStyleSeed = useMemo(
    () => pickLatestImageStyleSeed([...(Array.isArray(storedArtifacts) ? storedArtifacts : []), ...(Array.isArray(generatedArtifacts) ? generatedArtifacts : [])]),
    [storedArtifacts, generatedArtifacts]
  );
  const storedFormats = useMemo(() => {
    const byKind = artifactFormatsByKind && typeof artifactFormatsByKind === "object" ? artifactFormatsByKind : {};
    const preferredKindOrder = ["text", "image", "gif", "video", "audio"];
    const seen = new Set();
    const out = [];

    for (const kind of preferredKindOrder) {
      const formats = Array.isArray(byKind[kind]) ? byKind[kind] : [];
      for (const fmt of formats) {
        const normalized = String(fmt || "").trim();
        if (!normalized || seen.has(normalized)) continue;
        seen.add(normalized);
        out.push(normalized);
      }
    }

    for (const [kind, formats] of Object.entries(byKind)) {
      if (preferredKindOrder.includes(kind)) continue;
      for (const fmt of Array.isArray(formats) ? formats : []) {
        const normalized = String(fmt || "").trim();
        if (!normalized || seen.has(normalized)) continue;
        seen.add(normalized);
        out.push(normalized);
      }
    }

    return out;
  }, [artifactFormatsByKind]);
  const artifactFormatKindMap = useMemo(() => {
    const out = {};
    for (const [kind, formats] of Object.entries(artifactFormatsByKind || {})) {
      for (const fmt of Array.isArray(formats) ? formats : []) {
        const key = String(fmt || "").trim();
        if (!key) continue;
        out[key] = String(kind || "").trim();
      }
    }
    return out;
  }, [artifactFormatsByKind]);
  const artifactSelectedKinds = useMemo(() => {
    const seen = new Set();
    const out = [];
    for (const fmt of selectedArtifactFormats) {
      const kind = String(artifactFormatKindMap?.[fmt] || "").trim();
      if (!kind || seen.has(kind)) continue;
      seen.add(kind);
      out.push(kind);
    }
    return out;
  }, [selectedArtifactFormats, artifactFormatKindMap]);
  const filteredStoredArtifacts = useMemo(() => {
    if (!selectedStoredFormat) return [];
    return storedArtifacts.filter((a) => a?.format === selectedStoredFormat);
  }, [storedArtifacts, selectedStoredFormat]);
  const storedArtifactCountsByFormat = useMemo(() => {
    const counts = {};
    for (const artifact of Array.isArray(storedArtifacts) ? storedArtifacts : []) {
      const fmt = String(artifact?.format || "").trim();
      if (!fmt) continue;
      counts[fmt] = (counts[fmt] || 0) + 1;
    }
    return counts;
  }, [storedArtifacts]);
  const selectedStoredArtifact = filteredStoredArtifacts[selectedStoredArtifactTab] || null;
  const isArtifactEditActive = artifactEditMode !== "none";
  const approvedActiveVoiceProfileOptions = useMemo(() => {
    return vpProfilesIndex
      .filter((p) => p?.active_version && String(p.active_version.generation_status || "").toLowerCase() === "approved")
      .map((p) => {
        const active = p.active_version || {};
        const versionNo = active.version_no ?? "-";
        const name = String(p.voice_profile_name || p.voice_profile_id || "").trim();
        return {
          value: p.voice_profile_id,
          label: `${name} (active v${versionNo})`,
        };
      });
  }, [vpProfilesIndex]);
  const projectHasSavedVoiceProfileOption = useMemo(() => {
    const currentVoiceProfileId = String(form.voice_profile_id || "").trim();
    if (!currentVoiceProfileId) return false;
    return approvedActiveVoiceProfileOptions.some((opt) => opt.value === currentVoiceProfileId);
  }, [approvedActiveVoiceProfileOptions, form.voice_profile_id]);
  const projectToneBase = useMemo(() => toneBaseFromProjectTone(form.tone_preference), [form.tone_preference]);
  const artifactSelectedFormatCards = useMemo(
    () => selectedArtifactFormats.map((fmt) => artifactFormatMeta(fmt)),
    [selectedArtifactFormats]
  );
  const artifactSelectedAdvancedFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => Object.prototype.hasOwnProperty.call(FORMAT_ADVANCED_DEFAULTS, x.key)),
    [artifactSelectedFormatCards]
  );
  const artifactSelectedVoiceProfilePreview = useMemo(
    () => normalizeVoiceProfilePreview(artifactStyleVoiceProfileDetail),
    [artifactStyleVoiceProfileDetail]
  );
  const artifactSelectedTextFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => artifactFormatKindMap?.[x.key] === "text"),
    [artifactSelectedFormatCards, artifactFormatKindMap]
  );
  const artifactSelectedImageFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => artifactFormatKindMap?.[x.key] === "image"),
    [artifactSelectedFormatCards, artifactFormatKindMap]
  );
  const artifactSelectedVideoFormatCards = useMemo(
    () => artifactSelectedFormatCards.filter((x) => {
      const kind = artifactFormatKindMap?.[x.key];
      return kind === "video" || kind === "gif";
    }),
    [artifactSelectedFormatCards, artifactFormatKindMap]
  );
  const publishArtifactsById = useMemo(() => {
    const out = {};
    for (const a of Array.isArray(publishArtifacts) ? publishArtifacts : []) {
      const id = String(a?.artifact_id || "").trim();
      if (!id) continue;
      out[id] = a;
    }
    return out;
  }, [publishArtifacts]);
  const areRequiredPublishFieldsMapped = useMemo(() => {
    const schemaRows = Array.isArray(publishFieldSchema) ? publishFieldSchema : [];
    const requiredRows = schemaRows.filter((field) => !!field?.required);
    if (!requiredRows.length) return true;
    for (const field of requiredRows) {
      const fieldKey = String(field?.field_key || "").trim();
      if (!fieldKey) return false;
      const rows = Array.isArray(publishFieldMappings?.[fieldKey]) ? publishFieldMappings[fieldKey] : [];
      let hasValid = false;
      for (const row of rows) {
        const artifactId = String(row?.artifact_id || "").trim();
        const artifact = publishArtifactsById[artifactId] || null;
        const primaryPart = String(row?.primary_part || "").trim() || defaultPublishPartForArtifact(artifact);
        if (artifactId && primaryPart) {
          hasValid = true;
          break;
        }
      }
      if (!hasValid) return false;
    }
    return true;
  }, [publishFieldSchema, publishFieldMappings, publishArtifactsById]);
  const platformTargets = useMemo(
    () => uniqueStrings((publishPlatforms || []).map((p) => String(p || "").trim()).filter(Boolean)),
    [publishPlatforms]
  );
  const canGenerateContent = useMemo(() => {
    const topicTitle = String(form.topic_title || "").trim();
    const coreIdea = String(form.core_idea || "").trim();
    const targetAudience = String(form.target_audience_segment || "").trim();
    const tonePreference = String(form.tone_preference || "").trim();
    return !!(topicTitle && coreIdea && targetAudience && tonePreference);
  }, [form]);
  const canGenerateArtifactsNow = useMemo(() => {
    if (!selectedArtifactFormats.length) return false;
    const hasTextSelection = selectedArtifactFormats.some((fmt) => artifactFormatKindMap?.[fmt] === "text");
    const hasImageSelection = artifactSelectedKinds.includes("image");
    const hasVideoSelection = artifactSelectedKinds.includes("video") || artifactSelectedKinds.includes("gif");

    if (hasTextSelection) {
      if (artifactStyleSource === "manual" && !(artifactManualCoreVoice || "").trim()) return false;
      if (artifactStyleSource === "voice_profile" && !(artifactStyleVoiceProfileId || "").trim()) return false;
    }
    if (hasImageSelection) {
      if (!(artifactImageStyle?.theme || "").trim()) return false;
      if (!(artifactImageStyle?.subject_prompt || "").trim()) return false;
    }
    if (hasVideoSelection) {
      if (!(artifactVideoStyle?.theme || "").trim()) return false;
      if (!(artifactVideoStyle?.subject_prompt || "").trim()) return false;
    }
    return true;
  }, [
    selectedArtifactFormats,
    artifactFormatKindMap,
    artifactSelectedKinds,
    artifactStyleSource,
    artifactManualCoreVoice,
    artifactStyleVoiceProfileId,
    artifactImageStyle,
    artifactVideoStyle,
  ]);

async function refreshVersions(projectId, preferredVersion) {
    const data = await request("GET", `/api/v1/versions/${encodePathSegment(projectId)}`);
    const list = data?.versions || [];
    setVersions(list);
    if (preferredVersion && list.some((v) => v.version_number === preferredVersion)) {
      setSelectedVersionNumber(preferredVersion);
      return list;
    }
    const finalVersionFromProject = Number(currentProjectSummary?.final_version_number);
    if (Number.isFinite(finalVersionFromProject) && list.some((v) => v.version_number === finalVersionFromProject)) {
      setSelectedVersionNumber(finalVersionFromProject);
      return list;
    }
    const latestFinal = [...list]
      .filter((v) => String(v?.version_stage || "").trim().toLowerCase() === "final")
      .sort((a, b) => Number(b?.version_number || 0) - Number(a?.version_number || 0))[0] || null;
    const base = list.find((v) => v.version_kind === "base");
    const fallback = latestFinal || base || list[0] || null;
    setSelectedVersionNumber(fallback ? fallback.version_number : null);
    return list;
  }

  function persistAuthToken(token) {
    const next = token || "";
    setAuthToken(next);
    if (next) window.localStorage.setItem("cpublishr_token", next);
    else window.localStorage.removeItem("cpublishr_token");
  }

  async function openEditorialForProject(projectId) {
    const normalizedProjectId = String(projectId || "").trim();
    if (!normalizedProjectId) {
      setError("Project ID is required.");
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const versionsList = await refreshVersions(normalizedProjectId);
      setPage("editorial");
      if (Array.isArray(versionsList) && versionsList.length) {
        setMessage("");
      } else {
        setMessage(`No saved versions found for project "${normalizedProjectId}".`);
      }
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function request(method, path, body) {
    return apiRequest(apiBaseUrl, method, path, body, authToken);
  }

  async function loadCurrentUser() {
    if (!authToken) {
      setCurrentUser(null);
      return;
    }
    try {
      const me = await request("GET", "/api/v1/auth/me");
      setCurrentUser(me || null);
    } catch {
      persistAuthToken("");
      setCurrentUser(null);
    }
  }

  async function loadUserProjects() {
    if (!authToken) {
      setUserProjects([]);
      return;
    }
    setIsProjectsLoading(true);
    try {
      const out = await request("GET", "/api/v1/projects/");
      const rows = Array.isArray(out?.projects) ? out.projects : [];
      setUserProjects(rows);
      const currentProjectId = String(form.project_id || "").trim();
      const hasCurrent = currentProjectId && rows.some((p) => p?.project_id === currentProjectId);
      if (!currentProjectId && rows[0]?.project_id) {
        setForm((prev) => ({ ...prev, project_id: rows[0].project_id }));
      } else if (!hasCurrent && !hasManuallyEditedProjectId && rows[0]?.project_id) {
        setForm((prev) => ({ ...prev, project_id: rows[0].project_id }));
      }
    } catch {
      setUserProjects([]);
    } finally {
      setIsProjectsLoading(false);
    }
  }

  async function onAuthSubmit() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      if (!authForm.password) {
        throw new Error("Password is required.");
      }
      if (!authForm.user_id.trim()) {
        throw new Error("User ID is required.");
      }
      if (authMode === "signup" && !authForm.email.trim()) {
        throw new Error("Email is required for signup.");
      }
      const path = authMode === "signup" ? "/api/v1/auth/signup" : "/api/v1/auth/login";
      const payload = authMode === "signup"
        ? { user_id: authForm.user_id.trim(), email: authForm.email.trim(), password: authForm.password }
        : { user_id: authForm.user_id.trim(), password: authForm.password };
      const out = await apiRequest(apiBaseUrl, "POST", path, payload, "");
      persistAuthToken(out?.access_token || "");
      setCurrentUser(out?.user || null);
      setAuthForm((prev) => ({ ...prev, password: "" }));
      setMessage("");
      setPage("projects");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function onLogout() {
    persistAuthToken("");
    setCurrentUser(null);
    setUserProjects([]);
    setPage("setup");
    setVpCollections([]);
    setVpSelectedCollectionId("");
    setVpCollectionDetail(null);
    setVpSelectedVersionId("");
    setVpVersionDetail(null);
    setShowVpCreateCollectionForm(false);
    setHasManuallyEditedProjectId(false);
    setIsCreatingNewProject(false);
    setMessage("Logged out.");
  }

  function onNewProjectIdChange(nextProjectId) {
    setHasManuallyEditedProjectId(true);
    setIsCreatingNewProject(true);
    setForm((prev) => ({ ...prev, project_id: nextProjectId }));
  }

  async function onSelectExistingProject(projectId) {
    const value = String(projectId || "").trim();
    if (!value) return;
    setHasManuallyEditedProjectId(true);
    setIsCreatingNewProject(false);
    setForm((prev) => ({ ...prev, project_id: value }));
    await openEditorialForProject(value);
  }

  function onCreateNewProject() {
    setHasManuallyEditedProjectId(true);
    setIsCreatingNewProject(true);
    setForm((prev) => ({ ...prev, project_id: "" }));
    setHasExistingContent(false);
    setShowGenerateSetupForm(true);
    setPage("setup");
  }

  function onSelectVpCollection(collectionId) {
    setVpSelectedCollectionId(collectionId);
    setVpSelectedProfileId("");
    setVpProfileDetail(null);
    setVpProfileComposerMode("hidden");
    setVpSelectedVersionId("");
    setVpVersionDetail(null);
    setShowVpCreateCollectionForm(false);
  }

  async function vpRequest(method, path, body) {
    return apiRequest(apiBaseUrl, method, path, body, authToken);
  }

  async function loadVpCollections(preferredCollectionId = "") {
    if (!authToken) {
      setVpCollections([]);
      setVpProfilesIndex([]);
      setVpSelectedCollectionId("");
      setVpCollectionDetail(null);
      setVpSelectedProfileId("");
      setVpProfileDetail(null);
      setVpSelectedVersionId("");
      setVpVersionDetail(null);
      setShowVpCreateCollectionForm(false);
      return;
    }
    const [collectionsOut, profilesOut] = await Promise.all([
      vpRequest("GET", "/api/v1/voice-profiles/collections"),
      vpRequest("GET", "/api/v1/voice-profiles/profiles"),
    ]);
    const rows = Array.isArray(collectionsOut?.collections) ? collectionsOut.collections : [];
    const profiles = Array.isArray(profilesOut?.voice_profiles) ? profilesOut.voice_profiles : [];
    setVpCollections(rows);
    setVpProfilesIndex(profiles);
    const hasPreferred = preferredCollectionId && rows.some((x) => x.collection_id === preferredCollectionId);
    const nextCollectionId = hasPreferred ? preferredCollectionId : rows[0]?.collection_id || "";
    setVpSelectedCollectionId(nextCollectionId);
  }

  async function loadVpCollectionDetail(collectionId) {
    if (!collectionId || !authToken) {
      setVpCollectionDetail(null);
      setVpSelectedProfileId("");
      setVpProfileDetail(null);
      setVpSelectedVersionId("");
      setVpVersionDetail(null);
      return;
    }
    const out = await vpRequest("GET", `/api/v1/voice-profiles/collections/${collectionId}`);
    setVpCollectionDetail(out || null);
    const profiles = Array.isArray(out?.voice_profiles) ? out.voice_profiles : [];
    const preferred =
      profiles.find((p) => p?.active_version && String(p.active_version.generation_status || "").toLowerCase() === "approved")
      || profiles[0]
      || null;
    setVpSelectedProfileId(preferred?.voice_profile_id || "");
  }

  async function loadVpProfileDetail(voiceProfileId) {
    if (!voiceProfileId || !authToken) {
      setVpProfileDetail(null);
      setVpSelectedVersionId("");
      setVpVersionDetail(null);
      return;
    }
    const out = await vpRequest("GET", `/api/v1/voice-profiles/profiles/${voiceProfileId}`);
    setVpProfileDetail(out || null);
    const versions = Array.isArray(out?.versions) ? out.versions : [];
    const active = versions.find((v) => v.is_active);
    setVpSelectedVersionId(active?.voice_profile_version_id || versions[0]?.voice_profile_version_id || "");
  }

  async function loadVpVersionDetail(voiceProfileVersionId) {
    if (!voiceProfileVersionId || !authToken) {
      setVpVersionDetail(null);
      return;
    }
    const out = await vpRequest("GET", `/api/v1/voice-profiles/versions/${voiceProfileVersionId}`);
    setVpVersionDetail(out || null);
  }

  async function loadArtifactVoiceProfilePreview(voiceProfileId) {
    if (!voiceProfileId || !authToken) {
      setArtifactStyleVoiceProfileDetail(null);
      return;
    }
    setIsArtifactStyleVoiceProfileLoading(true);
    try {
      const detail = await vpRequest("GET", `/api/v1/voice-profiles/profiles/${voiceProfileId}`);
      const versions = Array.isArray(detail?.versions) ? detail.versions : [];
      const preferred =
        versions.find((v) => v.is_active && String(v.generation_status || "").toLowerCase() === "approved")
        || versions.find((v) => v.is_active)
        || versions.find((v) => String(v.generation_status || "").toLowerCase() === "approved")
        || versions[0];
      if (!preferred?.voice_profile_version_id) {
        setArtifactStyleVoiceProfileDetail(null);
        return;
      }
      const versionDetail = await vpRequest("GET", `/api/v1/voice-profiles/versions/${preferred.voice_profile_version_id}`);
      setArtifactStyleVoiceProfileDetail(versionDetail || null);
    } catch {
      setArtifactStyleVoiceProfileDetail(null);
    } finally {
      setIsArtifactStyleVoiceProfileLoading(false);
    }
  }

  function updateArtifactToneNuance(field, value) {
    setArtifactToneNuance((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactAdvanced(formatKey, field, value) {
    setArtifactFormatAdvanced((prev) => ({
      ...prev,
      [formatKey]: {
        ...(prev?.[formatKey] || {}),
        [field]: value,
      },
    }));
  }

  function toggleArtifactAdvancedAngle(angle) {
    setArtifactFormatAdvanced((prev) => {
      const curr = new Set(prev?.cta_variants?.angles || []);
      if (curr.has(angle)) curr.delete(angle);
      else curr.add(angle);
      return {
        ...prev,
        cta_variants: {
          ...(prev?.cta_variants || {}),
          angles: Array.from(curr),
        },
      };
    });
  }

  function toggleArtifactAdvancedDrawer(formatKey) {
    setArtifactAdvancedOpen((prev) => ({ ...prev, [formatKey]: !prev?.[formatKey] }));
  }

  function updateArtifactImageStyle(field, value) {
    setArtifactImageStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactImageBrandColor(field, value) {
    setArtifactImageStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function addArtifactImageAvoidTag() {
    const tag = String(artifactImageAvoidInput || "").trim();
    if (!tag) return;
    setArtifactImageStyle((prev) => {
      const curr = Array.isArray(prev?.avoid) ? prev.avoid : [];
      const next = uniqueStrings([...curr, tag]);
      return { ...prev, avoid: next };
    });
    setArtifactImageAvoidInput("");
  }

  function removeArtifactImageAvoidTag(tagToRemove) {
    setArtifactImageStyle((prev) => ({
      ...prev,
      avoid: (Array.isArray(prev?.avoid) ? prev.avoid : []).filter((x) => x !== tagToRemove),
    }));
  }

  function updateArtifactVideoStyle(field, value) {
    setArtifactVideoStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactVideoBrandColor(field, value) {
    setArtifactVideoStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function addArtifactVideoAvoidTag() {
    const tag = String(artifactVideoAvoidInput || "").trim();
    if (!tag) return;
    setArtifactVideoStyle((prev) => {
      const curr = Array.isArray(prev?.avoid) ? prev.avoid : [];
      return { ...prev, avoid: uniqueStrings([...curr, tag]) };
    });
    setArtifactVideoAvoidInput("");
  }

  function removeArtifactVideoAvoidTag(tagToRemove) {
    setArtifactVideoStyle((prev) => ({
      ...prev,
      avoid: (Array.isArray(prev?.avoid) ? prev.avoid : []).filter((x) => x !== tagToRemove),
    }));
  }

  function updateArtifactIterateToneNuance(field, value) {
    setArtifactIterateToneNuance((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactIterateAdvanced(formatKey, field, value) {
    setArtifactIterateFormatAdvanced((prev) => ({
      ...prev,
      [formatKey]: {
        ...(prev?.[formatKey] || {}),
        [field]: value,
      },
    }));
  }

  function updateArtifactIterateImageStyle(field, value) {
    setArtifactIterateImageStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactIterateImageBrandColor(field, value) {
    setArtifactIterateImageStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function updateArtifactIterateVideoStyle(field, value) {
    setArtifactIterateVideoStyle((prev) => ({ ...prev, [field]: value }));
  }

  function updateArtifactIterateVideoBrandColor(field, value) {
    setArtifactIterateVideoStyle((prev) => ({
      ...prev,
      brand_colors: {
        ...(prev?.brand_colors || {}),
        [field]: value,
      },
    }));
  }

  function buildArtifactTextKindStyleSettings() {
    const toneBase = toneBaseFromProjectTone(form.tone_preference);
    const toneNuancePayload = {
      tone_base: toneBase,
      tone_nuance: {
        directness: clampInt(artifactToneNuance.directness, 0, 4, 2),
        warmth: clampInt(artifactToneNuance.warmth, 0, 4, 2),
        energy: clampInt(artifactToneNuance.energy, 0, 4, 2),
        authority: clampInt(artifactToneNuance.authority, 0, 4, 2),
      },
    };
    if (toneBase === "analytical") {
      toneNuancePayload.tone_nuance.rigor = clampInt(artifactToneNuance.rigor, 0, 4, 3);
      toneNuancePayload.tone_nuance.abstraction = clampInt(artifactToneNuance.abstraction, 0, 4, 2);
      toneNuancePayload.tone_nuance.framework_mode = String(artifactFrameworkMode || "light");
    }
    if (toneBase === "professional") {
      toneNuancePayload.tone_nuance.formality = clampInt(artifactToneNuance.formality, 0, 4, 3);
      toneNuancePayload.tone_nuance.diplomacy = clampInt(artifactToneNuance.diplomacy, 0, 4, 3);
    }
    if (toneBase === "conversational") {
      toneNuancePayload.tone_nuance.humor = String(artifactToneNuance.humor || "light");
      toneNuancePayload.tone_nuance.storyness = clampInt(artifactToneNuance.storyness, 0, 4, 2);
    }

    if (artifactStyleSource === "manual") {
      return {
        style_source: "manual",
        core_voice: (artifactManualCoreVoice || "").trim(),
        ...toneNuancePayload,
      };
    }

    return {
      style_source: "voice_profile",
      voice_profile_id: artifactStyleVoiceProfileId || form.voice_profile_id || "",
      voice_profile_preview: artifactSelectedVoiceProfilePreview || null,
      ...toneNuancePayload,
    };
  }

  function buildArtifactKindStyleSettings() {
    const selected = new Set(selectedArtifactFormats);
    const out = {};
    const hasTextSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "text");
    const hasImageSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "image");
    const hasVideoSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "video");
    const hasGifSelection = Array.from(selected).some((fmt) => artifactFormatKindMap?.[fmt] === "gif");
    if (hasTextSelection) {
      out.text = buildArtifactTextKindStyleSettings();
    }
    if (hasImageSelection) {
      const avoid = uniqueStrings((artifactImageStyle?.avoid || []).map((x) => String(x || "").trim()).filter(Boolean));
      out.image = {
        theme: String(artifactImageStyle?.theme || "").trim(),
        subject_prompt: String(artifactImageStyle?.subject_prompt || "").trim(),
        avoid,
        medium: String(artifactImageStyle?.medium || "illustration"),
        texture: String(artifactImageStyle?.texture || "clean"),
        lighting: String(artifactImageStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactImageStyle?.palette_mode || "muted"),
        mood: String(artifactImageStyle?.mood || "premium"),
        focus_negative_space: String(artifactImageStyle?.focus_negative_space || "subject_centered"),
        output_fidelity: String(artifactImageStyle?.output_fidelity || "standard").toLowerCase(),
      };
      if (String(out.image.palette_mode) === "brand") {
        out.image.brand_colors = {
          primary: String(artifactImageStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactImageStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactImageStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactImageStyle?.brand_colors?.background || "").trim(),
        };
      }
    }
    if (hasVideoSelection || hasGifSelection) {
      const avoid = uniqueStrings((artifactVideoStyle?.avoid || []).map((x) => String(x || "").trim()).filter(Boolean));
      const videoPayload = {
        theme: String(artifactVideoStyle?.theme || "").trim(),
        subject_prompt: String(artifactVideoStyle?.subject_prompt || "").trim(),
        avoid,
        mood: String(artifactVideoStyle?.mood || "energetic"),
        lighting: String(artifactVideoStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactVideoStyle?.palette_mode || "muted"),
        output_fidelity: String(artifactVideoStyle?.output_fidelity || "standard").toLowerCase(),
        camera_motion: String(artifactVideoStyle?.camera_motion || "").trim(),
        energy_level: String(artifactVideoStyle?.energy_level || "medium"),
      };
      if (String(videoPayload.palette_mode) === "brand") {
        videoPayload.brand_colors = {
          primary: String(artifactVideoStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactVideoStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactVideoStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactVideoStyle?.brand_colors?.background || "").trim(),
        };
      }
      if (hasVideoSelection) out.video = { ...videoPayload };
      if (hasGifSelection) out.gif = { ...videoPayload };
    }
    return out;
  }

  function buildArtifactFormatStyleOverrides() {
    const selected = new Set(selectedArtifactFormats);
    const out = {};
    for (const fmt of selected) {
      const settings = artifactFormatAdvanced?.[fmt];
      if (!settings || typeof settings !== "object") continue;
      out[fmt] = { ...settings };
      if (fmt === "newsletter") {
        out[fmt].sections = clampInt(settings.sections, 3, 5, 4);
        out[fmt].takeaway_bullets = clampInt(settings.takeaway_bullets, 3, 6, 4);
      }
      if (fmt === "blog") {
        out[fmt].faq_count = clampInt(settings.faq_count, 0, 5, 3);
      }
      if (fmt === "script_short") {
        out[fmt].target_duration_sec = clampInt(settings.target_duration_sec, 15, 60, 30);
      }
      if (fmt === "cta_variants") {
        out[fmt].variant_count = clampInt(settings.variant_count, 7, 11, 7);
        out[fmt].angles = uniqueStrings(settings.angles || []);
      }
    }
    return out;
  }

  function getStoredArtifactSourceBlobPaths(artifact) {
    const assets = Array.isArray(artifact?.payload_json?.assets) ? artifact.payload_json.assets : [];
    return uniqueStrings(
      assets
        .map((a) => String(a?.blob_path || a?.uri || a?.path || "").trim())
        .filter(Boolean)
    );
  }

  function buildIterateKindStyleSettings(artifact) {
    const kind = String(artifact?.kind || "").trim().toLowerCase();
    if (!kind) return {};
    if (kind === "text") {
      const toneBase = toneBaseFromProjectTone(form.tone_preference);
      const toneNuancePayload = {
        tone_base: toneBase,
        tone_nuance: {
          directness: clampInt(artifactIterateToneNuance.directness, 0, 4, 2),
          warmth: clampInt(artifactIterateToneNuance.warmth, 0, 4, 2),
          energy: clampInt(artifactIterateToneNuance.energy, 0, 4, 2),
          authority: clampInt(artifactIterateToneNuance.authority, 0, 4, 2),
        },
      };
      if (toneBase === "analytical") {
        toneNuancePayload.tone_nuance.rigor = clampInt(artifactIterateToneNuance.rigor, 0, 4, 3);
        toneNuancePayload.tone_nuance.abstraction = clampInt(artifactIterateToneNuance.abstraction, 0, 4, 2);
        toneNuancePayload.tone_nuance.framework_mode = String(artifactIterateFrameworkMode || "light");
      }
      const manualCoreVoice = String(artifactIterateManualCoreVoice || "").trim();
      const textStyle = artifactIterateStyleSource === "voice_profile"
        ? {
          style_source: "voice_profile",
          voice_profile_id: (artifactIterateVoiceProfileId || form.voice_profile_id || "").trim(),
          voice_profile_preview: artifactSelectedVoiceProfilePreview || null,
        }
        : (manualCoreVoice
          ? { style_source: "manual", core_voice: manualCoreVoice }
          : {});
      return { text: { ...textStyle, ...toneNuancePayload } };
    }
    if (kind === "image") {
      const imagePayload = {
        medium: String(artifactIterateImageStyle?.medium || "illustration"),
        texture: String(artifactIterateImageStyle?.texture || "clean"),
        lighting: String(artifactIterateImageStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactIterateImageStyle?.palette_mode || "muted"),
        mood: String(artifactIterateImageStyle?.mood || "premium"),
        focus_negative_space: String(artifactIterateImageStyle?.focus_negative_space || "subject_centered"),
        output_fidelity: String(artifactIterateImageStyle?.output_fidelity || "standard").toLowerCase(),
      };
      if (imagePayload.palette_mode === "brand") {
        imagePayload.brand_colors = {
          primary: String(artifactIterateImageStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactIterateImageStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactIterateImageStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactIterateImageStyle?.brand_colors?.background || "").trim(),
        };
      }
      return { image: imagePayload };
    }
    if (kind === "video" || kind === "gif") {
      const videoPayload = {
        mood: String(artifactIterateVideoStyle?.mood || "energetic"),
        lighting: String(artifactIterateVideoStyle?.lighting || "soft_daylight"),
        palette_mode: String(artifactIterateVideoStyle?.palette_mode || "muted"),
        output_fidelity: String(artifactIterateVideoStyle?.output_fidelity || "standard").toLowerCase(),
        camera_motion: String(artifactIterateVideoStyle?.camera_motion || "").trim(),
        energy_level: String(artifactIterateVideoStyle?.energy_level || "medium"),
      };
      if (videoPayload.palette_mode === "brand") {
        videoPayload.brand_colors = {
          primary: String(artifactIterateVideoStyle?.brand_colors?.primary || "").trim(),
          secondary: String(artifactIterateVideoStyle?.brand_colors?.secondary || "").trim(),
          accent: String(artifactIterateVideoStyle?.brand_colors?.accent || "").trim(),
          background: String(artifactIterateVideoStyle?.brand_colors?.background || "").trim(),
        };
      }
      return kind === "gif" ? { gif: videoPayload } : { video: videoPayload };
    }
    return {};
  }

  function buildIterateFormatStyleOverrides(artifact) {
    const fmt = String(artifact?.format || "").trim();
    if (!Object.prototype.hasOwnProperty.call(FORMAT_ADVANCED_DEFAULTS, fmt)) return {};
    const settings = artifactIterateFormatAdvanced?.[fmt];
    if (!settings || typeof settings !== "object") return {};
    const out = { [fmt]: { ...settings } };
    if (fmt === "newsletter") {
      out[fmt].sections = clampInt(settings.sections, 3, 5, 4);
      out[fmt].takeaway_bullets = clampInt(settings.takeaway_bullets, 3, 6, 4);
    }
    if (fmt === "blog") {
      out[fmt].faq_count = clampInt(settings.faq_count, 0, 5, 3);
    }
    if (fmt === "script_short") {
      out[fmt].target_duration_sec = clampInt(settings.target_duration_sec, 15, 60, 30);
    }
    if (fmt === "cta_variants") {
      out[fmt].variant_count = clampInt(settings.variant_count, 7, 11, 7);
      out[fmt].angles = uniqueStrings(settings.angles || []);
    }
    return out;
  }

  function toggleVpPlatform(platform) {
    const curr = new Set(vpCreateForm.platforms || []);
    if (curr.has(platform)) curr.delete(platform);
    else curr.add(platform);
    setVpCreateForm((prev) => ({ ...prev, platforms: Array.from(curr) }));
  }

  async function onVpCreateCollection() {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const payload = {
        collection_name: (vpCreateForm.collection_name || "").trim(),
        platforms: vpCreateForm.platforms || [],
      };
      const out = await vpRequest("POST", "/api/v1/voice-profiles/collections", payload);
      const newId = out?.collection?.collection_id || "";
      setVpCreateForm({ collection_name: "", platforms: ["linkedin"] });
      await loadVpCollections(newId);
      setShowVpCreateCollectionForm(false);
      setMessage("Collection created.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onVpCreateDataset() {
    if (!vpSelectedCollectionId) {
      setError("Select a collection first.");
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const payload = {
        dataset_name: (vpDatasetForm.dataset_name || "").trim(),
        source_profile: (vpDatasetForm.source_profile || "").trim() || null,
        source_type: vpDatasetSourceMode === "local" ? "local_files" : "azure_blob",
        blob_prefix: vpDatasetSourceMode === "local"
          ? JSON.stringify(vpDatasetLocalFiles || [])
          : (vpDatasetForm.blob_prefix || "").trim(),
        sample_scope_note: (vpDatasetForm.sample_scope_note || "").trim() || null,
      };
      const out = await vpRequest("POST", `/api/v1/voice-profiles/collections/${vpSelectedCollectionId}/datasets`, payload);
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      setVpDatasetForm({ dataset_name: "", source_profile: "", blob_prefix: "", sample_scope_note: "" });
      setVpDatasetLocalFiles([]);
      setMessage(`Dataset uploaded. Entries written: ${out?.dataset_entries_written ?? 0}.`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function pickVpDatasetPath(mode = "files") {
    setIsVpPickingLocalDatasetPath(true);
    try {
      const out = await request("POST", "/api/v1/publishing/output-path/pick-local", {
        start_path: String(vpDatasetForm.blob_prefix || "").trim() || null,
        mode,
      });
      const selectedRaw = out?.selected_path;
      const selected = Array.isArray(selectedRaw)
        ? selectedRaw.map((x) => String(x || "").trim()).filter(Boolean)
        : (String(selectedRaw || "").trim() ? [String(selectedRaw || "").trim()] : []);
      if (!selected.length) return;
      setVpDatasetLocalFiles(selected);
      setVpDatasetForm((prev) => ({ ...prev, blob_prefix: selected.join("; ") }));
      window.localStorage.setItem("cpublishr_vp_dataset_last_local_path", selected[0]);
    } finally {
      setIsVpPickingLocalDatasetPath(false);
    }
  }

  async function onVpGenerateVersion() {
    if (!vpSelectedCollectionId) {
      setError("Select a collection first.");
      return;
    }
    const profileName = String(vpProfileForm.voice_profile_name || "").trim();
    if (!profileName) {
      setError("Voice profile name is required.");
      return;
    }
    if (!(vpGenerateForm.dataset_ids || []).length) {
      setError("Select at least one dataset.");
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    setIsVpGenerating(true);
    try {
      const existingProfiles = Array.isArray(vpCollectionDetail?.voice_profiles) ? vpCollectionDetail.voice_profiles : [];
      const existingProfile = existingProfiles.find((p) => String(p?.voice_profile_name || "").trim().toLowerCase() === profileName.toLowerCase());
      let targetProfileId = String(existingProfile?.voice_profile_id || "").trim();
      if (!targetProfileId) {
        const createOut = await vpRequest("POST", `/api/v1/voice-profiles/collections/${vpSelectedCollectionId}/profiles`, {
          voice_profile_name: profileName,
        });
        targetProfileId = String(createOut?.voice_profile?.voice_profile_id || "").trim();
      }
      if (!targetProfileId) {
        throw new Error("Failed to resolve voice profile.");
      }
      const payload = {
        intended_use: (vpProfileForm.intended_use || "").trim() || null,
        dataset_ids: vpGenerateForm.dataset_ids || [],
      };
      const out = await vpRequest(
        "POST",
        `/api/v1/voice-profiles/profiles/${targetProfileId}/versions/generate`,
        payload
      );
      const newVersionId = out?.generated_version?.version?.voice_profile_version_id || "";
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      await loadVpProfileDetail(targetProfileId);
      setVpSelectedProfileId(targetProfileId);
      setVpProfileComposerMode("existing");
      if (newVersionId) setVpSelectedVersionId(newVersionId);
      setMessage(existingProfile ? "Voice profile version generated." : "Voice profile created and version generated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsVpGenerating(false);
    }
  }

  async function onVpActivateVersion() {
    if (!vpSelectedVersionId) return;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await vpRequest("POST", `/api/v1/voice-profiles/versions/${vpSelectedVersionId}/activate`, {});
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      await loadVpProfileDetail(vpSelectedProfileId);
      await loadVpVersionDetail(vpSelectedVersionId);
      setMessage("Voice profile version activated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onVpUpdateStatus() {
    if (!vpSelectedVersionId) return;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await vpRequest("POST", `/api/v1/voice-profiles/versions/${vpSelectedVersionId}/status`, {
        status: (vpStatusInput || "").trim(),
      });
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      await loadVpProfileDetail(vpSelectedProfileId);
      await loadVpVersionDetail(vpSelectedVersionId);
      setMessage("Voice profile version status updated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function toggleVpGenerateDataset(datasetId) {
    setVpGenerateForm((prev) => {
      const curr = new Set(Array.isArray(prev.dataset_ids) ? prev.dataset_ids : []);
      if (curr.has(datasetId)) curr.delete(datasetId);
      else curr.add(datasetId);
      return { ...prev, dataset_ids: Array.from(curr) };
    });
  }

  function toggleVpCheckedProfile(profileId) {
    setVpCheckedProfileIds((prev) => {
      const curr = new Set(prev || []);
      if (curr.has(profileId)) curr.delete(profileId);
      else curr.add(profileId);
      return Array.from(curr);
    });
  }

  async function updateVpProfilesEnabled(isEnabled) {
    const ids = Array.isArray(vpCheckedProfileIds) ? vpCheckedProfileIds.filter(Boolean) : [];
    if (!ids.length) {
      setError(`Select at least one voice profile to ${isEnabled ? "activate" : "deactivate"}.`);
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await Promise.all(ids.map((id) => vpRequest("POST", `/api/v1/voice-profiles/profiles/${id}/status`, { is_enabled: isEnabled })));
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      if (vpSelectedProfileId && ids.includes(vpSelectedProfileId)) {
        await loadVpProfileDetail(vpSelectedProfileId);
      }
      setMessage(isEnabled ? "Selected voice profiles activated." : "Selected voice profiles deactivated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function deleteVpProfiles() {
    const ids = Array.isArray(vpCheckedProfileIds) ? vpCheckedProfileIds.filter(Boolean) : [];
    if (!ids.length) {
      setError("Select at least one voice profile to delete.");
      return;
    }
    if (!window.confirm(`Delete ${ids.length} selected voice profile(s)? This will remove their versions too.`)) {
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await Promise.all(ids.map((id) => vpRequest("DELETE", `/api/v1/voice-profiles/profiles/${id}`)));
      const removedSelected = vpSelectedProfileId && ids.includes(vpSelectedProfileId);
      setVpCheckedProfileIds([]);
      if (removedSelected) {
        setVpSelectedProfileId("");
        setVpProfileDetail(null);
        setVpSelectedVersionId("");
        setVpVersionDetail(null);
        setVpProfileComposerMode("hidden");
      }
      await loadVpCollections(vpSelectedCollectionId);
      await loadVpCollectionDetail(vpSelectedCollectionId);
      setMessage("Selected voice profiles deleted.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function checkExistingContent(projectId) {
    const normalizedProjectId = (projectId || "").trim();
    const requestSeq = ++contentCheckSeqRef.current;
    if (!normalizedProjectId) {
      setHasExistingContent(false);
      setShowGenerateSetupForm(true);
      return;
    }
    setIsCheckingProjectData(true);
    try {
      const data = await request("GET", `/api/v1/versions/${encodePathSegment(normalizedProjectId)}`);
      if (requestSeq !== contentCheckSeqRef.current) return;
      const list = data?.versions || [];
      const exists = Array.isArray(list) && list.length > 0;
      setHasExistingContent(exists);
      setShowGenerateSetupForm(!exists);
    } catch {
      if (requestSeq !== contentCheckSeqRef.current) return;
      setHasExistingContent(false);
      setShowGenerateSetupForm(true);
    } finally {
      if (requestSeq !== contentCheckSeqRef.current) return;
      setIsCheckingProjectData(false);
    }
  }

  function applySelection(versionNumber) {
    const item = versions.find((v) => v.version_number === Number(versionNumber));
    setSelectedVersionNumber(Number(versionNumber));
    setWorkingContent(item?.content || "");
    setFeedbackPreviewContent("");
    setEditorMode("none");
  }

  function toggleTarget(target) {
    const current = new Set(form.distribution_targets);
    if (current.has(target)) current.delete(target);
    else current.add(target);
    setForm({ ...form, distribution_targets: Array.from(current) });
  }

  function buildTopicPayload() {
    const topicTitle = (form.topic_title || "").trim();
    const coreIdea = (form.core_idea || "").trim();
    const voiceProfileId = (form.voice_profile_id || "").trim();
    if (!topicTitle) {
      throw new Error("Topic Title is required.");
    }
    if (!coreIdea) {
      throw new Error("Core Idea is required.");
    }
    if (!voiceProfileId) {
      throw new Error("Voice Profile ID is required.");
    }
    return {
      project_id: (form.project_id || "").trim(),
      topic_title: topicTitle,
      core_idea: coreIdea,
      user_content: (form.user_content || "").trim() || null,
      target_audience: {
        primary_segment: form.target_audience_segment,
        notes: (form.target_audience_notes || "").trim() || null,
      },
      tone_preference: form.tone_preference,
      stance: form.stance || "balanced",
      audience_familiarity: form.audience_familiarity || null,
      detail_level: form.detail_level || null,
      primary_goal: form.primary_goal || null,
      desired_action: form.desired_action || null,
      voice_profile_id: voiceProfileId,
      distribution_targets: form.distribution_targets.length ? form.distribution_targets : null,
    };
  }

  async function fetchAndApplyArtifactSuggestions(formats) {
    const projectId = String(form.project_id || "").trim();
    const mediaFormats = formats.filter((f) =>
      ["post_image", "thumbnail", "banner", "cover", "gif", "reel", "short_video"].includes(f)
    );
    if (!projectId || !mediaFormats.length) return;
    setArtifactSuggestionsLoading(true);
    setArtifactSuggestions(null);
    try {
      const out = await request("POST", "/api/v1/artifacts/suggest", {
        project_id: projectId,
        formats: mediaFormats,
      });
      const suggestions = out?.suggestions || {};
      setArtifactSuggestions(suggestions);
      // Pre-fill image style if theme/subject are still empty (user hasn't typed anything)
      if (suggestions.image && typeof suggestions.image === "object") {
        setArtifactImageStyle((prev) => {
          const s = suggestions.image;
          return {
            ...prev,
            theme: prev.theme || s.theme || prev.theme,
            subject_prompt: prev.subject_prompt || s.subject_prompt || prev.subject_prompt,
            mood: s.mood || prev.mood,
            medium: s.medium || prev.medium,
            texture: s.texture || prev.texture,
            palette_mode: s.palette_mode || prev.palette_mode,
            focus_negative_space: s.focus_negative_space || prev.focus_negative_space,
          };
        });
      }
      // Pre-fill video style if theme/subject are still empty
      if (suggestions.video && typeof suggestions.video === "object") {
        setArtifactVideoStyle((prev) => {
          const s = suggestions.video;
          return {
            ...prev,
            theme: prev.theme || s.theme || prev.theme,
            subject_prompt: prev.subject_prompt || s.subject_prompt || prev.subject_prompt,
            mood: s.mood || prev.mood,
            lighting: s.lighting || prev.lighting,
            palette_mode: s.palette_mode || prev.palette_mode,
          };
        });
      }
    } catch (err) {
      // Suggestions are best-effort; silently continue with manual editing.
      setArtifactSuggestions({});
    } finally {
      setArtifactSuggestionsLoading(false);
    }
  }

  function toggleArtifactFormat(format) {
    const current = new Set(selectedArtifactFormats);
    if (current.has(format)) current.delete(format);
    else current.add(format);
    setSelectedArtifactFormats(Array.from(current));
  }

  function toggleArtifactKind(kind) {
    const formats = orderArtifactFormats(kind, artifactFormatsByKind[kind] || []);
    const current = new Set(selectedArtifactFormats);
    const allSelected = formats.every((fmt) => current.has(fmt));
    if (allSelected) {
      formats.forEach((fmt) => current.delete(fmt));
    } else {
      formats.forEach((fmt) => current.add(fmt));
    }
    setSelectedArtifactFormats(Array.from(current));
  }

  async function onGenerateContent() {
    setError("");
    setMessage("");
    setIsGenerating(true);
    setBusy(true);
    setNodeAudit([]);
    setCanContinueToEditorial(false);
    try {
      const topicPayload = buildTopicPayload();
      setNodeAudit((prev) => [...prev, { node: "Node 0 - Topic Initialization", status: "running", output: null }]);
      const node0 = await request("POST", "/api/v1/projects/", topicPayload);
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 0 - Topic Initialization", status: "completed", output: node0 };
        return next;
      });

      setNodeAudit((prev) => [...prev, { node: "Node 1 - Research Trends", status: "running", output: null }]);
      const node1 = await request("POST", "/api/v1/workflows/nodes/research", {
        topic: topicPayload,
        persist_context: false,
      });
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 1 - Research Trends", status: "completed", output: node1 };
        return next;
      });

      setNodeAudit((prev) => [...prev, { node: "Node 2 - Master Content", status: "running", output: null }]);
      const node2 = await request("POST", "/api/v1/workflows/nodes/master", {
        topic: topicPayload,
        research: node1,
        persist_context: false,
        persist_versions: true,
      });
      setNodeAudit((prev) => {
        const next = [...prev];
        next[next.length - 1] = { node: "Node 2 - Master Content", status: "completed", output: node2 };
        return next;
      });

      await refreshVersions(form.project_id);
      loadUserProjects().catch(() => {});
      setMessage("Node 0-2 completed. Review audit output below, then continue to editorial.");
      setCanContinueToEditorial(true);
    } catch (e) {
      setNodeAudit((prev) => {
        if (!prev.length) return prev;
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.status === "running") {
          next[next.length - 1] = { ...last, status: "failed", output: { error: e.message || String(e) } };
        }
        return next;
      });
      setError(e.message || String(e));
    } finally {
      setIsGenerating(false);
      setBusy(false);
    }
  }

  async function onOpenEditorialPage() {
    await openEditorialForProject(form.project_id);
  }

  async function onPatchKeywords(nextKeywords) {
    if (!selectedVersion) return;
    setError("");
    setBusy(true);
    try {
      await request(
        "PATCH",
        `/api/v1/versions/${form.project_id}/${selectedVersion.version_number}/keywords`,
        { keywords: nextKeywords }
      );
      await refreshVersions(form.project_id, selectedVersion.version_number);
      setKeywordsInput("");
      setMessage("Keywords updated.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  function requestVersionLabel(defaultLabel = "") {
    const raw = window.prompt("Enter a version name", defaultLabel || "");
    if (raw === null) return null;
    const label = raw.trim();
    if (!label) {
      setError("Version name is required to save.");
      return null;
    }
    return label;
  }

  async function saveDraftVersion({ content, versionLabel }) {
    if (!selectedVersion) return null;
    if (!(content || "").trim()) {
      setError("Content cannot be empty.");
      return null;
    }
    if (!(versionLabel || "").trim()) {
      setError("Please enter a version name before saving.");
      return null;
    }
    setError("");
    setBusy(true);
    try {
      const out = await request("POST", "/api/v1/workflows/nodes/editorial/save-inline", {
        project_id: form.project_id,
        source_version: selectedVersion.version_number,
        content: content.trim(),
        version_label: versionLabel.trim(),
      });
      await refreshVersions(form.project_id, out.draft_version);
      setWorkingContent(out?.content || content);
      setFeedbackPreviewContent("");
      setEditorMode("none");
      setMessage(`Saved "${versionLabel.trim()}" as v${out.draft_version}.`);
      return out;
    } catch (e) {
      setError(e.message || String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function onSaveInline() {
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Editorial draft");
    if (!versionLabel) return;
    await saveDraftVersion({
      content: workingContent,
      versionLabel,
    });
  }

  async function onFeedbackPreview() {
    if (!selectedVersion) return;
    if (!feedbackText.trim()) {
      setError("Feedback cannot be empty.");
      return;
    }
    setError("");
    setIsPreviewing(true);
    setBusy(true);
    try {
      const out = await request("POST", "/api/v1/workflows/nodes/editorial/feedback/preview", {
        project_id: form.project_id,
        source_version: selectedVersion.version_number,
        user_feedback: feedbackText,
      });
      setFeedbackPreviewContent(out?.preview_content || "");
      setMessage(`Preview generated from version v${selectedVersion.version_number}.`);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsPreviewing(false);
      setBusy(false);
    }
  }

  async function onFinalizeSelected() {
    if (!selectedVersion) return;
    setError("");
    const prevPage = page;
    setMessage(`Finalizing version v${selectedVersion.version_number}...`);
    setPage("artifacts");
    setBusy(true);
    try {
      await request("POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: selectedVersion.version_number,
      });
      setMessage(`Finalized version v${selectedVersion.version_number}.`);
    } catch (e) {
      setError(e.message || String(e));
      setPage(prevPage);
    } finally {
      setBusy(false);
    }
  }

  async function onFinalizeFromInline() {
    if (!selectedVersion) return;
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Editorial draft");
    if (!versionLabel) return;
    const saved = await saveDraftVersion({
      content: workingContent,
      versionLabel,
    });
    if (!saved?.draft_version) return;
    setError("");
    const prevPage = page;
    setMessage(`Finalizing version v${saved.draft_version}...`);
    setPage("artifacts");
    setBusy(true);
    try {
      await request("POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: saved.draft_version,
      });
      setMessage(`Saved and finalized version v${saved.draft_version}.`);
      // Refresh versions asynchronously (do not block navigation).
      refreshVersions(form.project_id, saved.draft_version).catch(() => {});
    } catch (e) {
      setError(e.message || String(e));
      setPage(prevPage);
    } finally {
      setBusy(false);
    }
  }

  async function onSavePreview() {
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Iterated draft");
    if (!versionLabel) return;
    await saveDraftVersion({
      content: feedbackPreviewContent,
      versionLabel,
    });
  }

  async function onFinalizeFromPreview() {
    const versionLabel = requestVersionLabel(selectedVersion?.variant_label || "Iterated draft");
    if (!versionLabel) return;
    const saved = await saveDraftVersion({
      content: feedbackPreviewContent,
      versionLabel,
    });
    if (!saved?.draft_version) return;
    setError("");
    const prevPage = page;
    setMessage(`Finalizing version v${saved.draft_version}...`);
    setPage("artifacts");
    setBusy(true);
    try {
      await request("POST", "/api/v1/workflows/nodes/editorial/finalize-selected", {
        project_id: form.project_id,
        selected_version: saved.draft_version,
      });
      setMessage(`Saved and finalized version v${saved.draft_version}.`);
      // Refresh versions asynchronously (do not block navigation).
      refreshVersions(form.project_id, saved.draft_version).catch(() => {});
    } catch (e) {
      setError(e.message || String(e));
      setPage(prevPage);
    } finally {
      setBusy(false);
    }
  }

  function onCancelEditorialEdit() {
    setEditorMode("none");
    setFeedbackPreviewContent("");
    if (selectedVersion) {
      setWorkingContent(selectedVersion.content || "");
    }
  }

  function onCloseEditorialPreview() {
    setFeedbackPreviewContent("");
  }

  async function onGenerateArtifacts() {
    if (!selectedArtifactFormats.length) {
      setError("Select at least one artifact format.");
      return;
    }
    if (!canGenerateArtifactsNow) {
      return;
    }
    setError("");
    setMessage("");
    setBusy(true);
    setIsArtifactGenerating(true);
    setArtifactsViewMode("generate");
    setArtifactOutput(null);
    setSelectedArtifactTab(0);
    try {
      const styleSettingsByKind = buildArtifactKindStyleSettings();
      const formatOverrides = buildArtifactFormatStyleOverrides();
      const out = await request("POST", "/api/v1/artifacts/generate", {
        project_id: form.project_id,
        requested_formats: selectedArtifactFormats,
        revision_mode: "new_revision",
        style_settings_by_kind: styleSettingsByKind,
        style_settings_by_format: formatOverrides,
      });
      setArtifactOutput(out);
      setSelectedArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
      setHasStoredArtifactsForProject(count > 0 || hasStoredArtifactsForProject);
      if (Array.isArray(out?.artifacts)) {
        const generatedFormats = out.artifacts.map((a) => String(a?.format || "").trim()).filter(Boolean);
        setStoredArtifactFormatsForProject((prev) => uniqueStrings([...(prev || []), ...generatedFormats]));
      }
      const genErrors = Array.isArray(out?.generation_errors) ? out.generation_errors : [];
      if (genErrors.length) {
        setError(genErrors.map((e) => `${e.format} failed - ${e.error}`).join("; "));
      }
      const errorSummary = genErrors.length
        ? " Warning: " + genErrors.map((e) => `${e.format} failed — ${e.error}`).join("; ")
        : "";
      setMessage(`${count} artifact(s) generated.${errorSummary} Loading your artifacts...`);
      setTimeout(() => onViewStoredArtifacts(), 1500);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsArtifactGenerating(false);
    }
  }

  async function onViewStoredArtifacts() {
    setError("");
    setMessage("");
    setBusy(true);
    setIsStoredArtifactsLoading(true);
    setArtifactsViewMode("stored");
    try {
      const out = await request("GET", `/api/v1/artifacts/${form.project_id}`);
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setStoredArtifacts(items);
      const formats = Array.from(new Set(items.map((a) => (a?.format || "").trim()).filter(Boolean))).sort();
      setStoredArtifactFormatsForProject(formats);
      setSelectedStoredFormat(formats[0] || "");
      setSelectedStoredArtifactTab(0);
      const count = Array.isArray(out?.artifacts) ? out.artifacts.length : 0;
      setHasStoredArtifactsForProject(count > 0);
      setMessage(`Loaded ${count} stored artifact(s).`);
    } catch (e) {
      setHasStoredArtifactsForProject(false);
      setError(e.message || String(e));
    } finally {
      setBusy(false);
      setIsStoredArtifactsLoading(false);
    }
  }

  async function checkStoredArtifactsAvailability(projectId) {
    const normalizedProjectId = (projectId || "").trim();
    const requestSeq = ++storedArtifactsCheckSeqRef.current;
    if (!authToken || !normalizedProjectId) {
      setHasStoredArtifactsForProject(false);
      setIsCheckingStoredArtifacts(false);
      setStoredArtifactFormatsForProject([]);
      return;
    }
    setIsCheckingStoredArtifacts(true);
    try {
      const out = await request("GET", `/api/v1/artifacts/${normalizedProjectId}`);
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setStoredArtifacts(items);
      setHasStoredArtifactsForProject(items.length > 0);
      setStoredArtifactFormatsForProject(
        uniqueStrings(items.map((a) => String(a?.format || "").trim()).filter(Boolean))
      );
    } catch {
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      setStoredArtifacts([]);
      setHasStoredArtifactsForProject(false);
      setStoredArtifactFormatsForProject([]);
    } finally {
      if (requestSeq !== storedArtifactsCheckSeqRef.current) return;
      setIsCheckingStoredArtifacts(false);
    }
  }

  async function loadPublishPlatforms() {
    if (!authToken) {
      setPublishPlatforms([]);
      setPublishSelectedPlatform("");
      return;
    }
    setIsPublishPlatformsLoading(true);
    try {
      const out = await request("GET", "/api/v1/publishing/platforms");
      const items = Array.isArray(out?.platforms) ? out.platforms.map((x) => String(x || "").trim()).filter(Boolean) : [];
      setPublishPlatforms(items);
      setPublishSelectedPlatform((prev) => (prev && items.includes(prev) ? prev : (items[0] || "")));
    } catch {
      setPublishPlatforms([]);
      setPublishSelectedPlatform("");
    } finally {
      setIsPublishPlatformsLoading(false);
    }
  }

  async function loadPublishFieldSchema(platform) {
    const p = String(platform || "").trim().toLowerCase();
    if (!authToken || !p) {
      setPublishFieldSchema([]);
      return;
    }
    setIsPublishFieldSchemaLoading(true);
    try {
      const out = await request("GET", `/api/v1/publishing/platforms/${p}/fields`);
      const fields = Array.isArray(out?.fields) ? out.fields : [];
      setPublishFieldSchema(fields);
      setPublishFieldMappings((prev) => {
        const next = {};
        for (const field of fields) {
          const key = String(field?.field_key || "").trim();
          if (!key) continue;
          next[key] = Array.isArray(prev?.[key]) ? prev[key] : [];
        }
        return next;
      });
    } catch {
      setPublishFieldSchema([]);
      setPublishFieldMappings({});
    } finally {
      setIsPublishFieldSchemaLoading(false);
    }
  }

  async function loadPublishArtifacts(projectId) {
    const pid = String(projectId || "").trim();
    if (!authToken || !pid) {
      setPublishArtifacts([]);
      return;
    }
    setIsPublishArtifactsLoading(true);
    try {
      const out = await request("GET", `/api/v1/artifacts/${pid}`);
      const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
      setPublishArtifacts(items);
    } catch {
      setPublishArtifacts([]);
    } finally {
      setIsPublishArtifactsLoading(false);
    }
  }

  async function browsePublishOutputLocations(pathValue = "") {
    setIsPublishBrowsingPaths(true);
    try {
      const query = String(pathValue || "").trim();
      const endpoint = query
        ? `/api/v1/publishing/output-path/browse?path=${encodeURIComponent(query)}`
        : "/api/v1/publishing/output-path/browse";
      const out = await request("GET", endpoint);
      setPublishBrowseCurrentPath(String(out?.current_path || ""));
      setPublishBrowseParentPath(String(out?.parent_path || ""));
      setPublishBrowseDirectories(Array.isArray(out?.directories) ? out.directories : []);
    } finally {
      setIsPublishBrowsingPaths(false);
    }
  }

  async function pickPublishOutputFolder() {
    setIsPublishPickingLocalPath(true);
    try {
      const out = await request("POST", "/api/v1/publishing/output-path/pick-local", {
        start_path: String(publishSaveOutputPath || publishBrowseCurrentPath || "").trim() || null,
      });
      const selected = String(out?.selected_path || "").trim();
      if (selected) {
        setPublishSaveOutputPath(selected);
        window.localStorage.setItem("cpublishr_publish_output_path", selected);
        await browsePublishOutputLocations(selected);
      }
    } finally {
      setIsPublishPickingLocalPath(false);
    }
  }

  function openSaveToPublishDialog() {
    setError("");
    setPublishSaveMessage("");
    setPublishSaveUserName("");
    setPublishBrowseCurrentPath("");
    setPublishBrowseParentPath("");
    setPublishBrowseDirectories([]);
    setShowPublishSaveDialog(true);
  }

  function closeSaveToPublishDialog() {
    if (busy || isPublishBrowsingPaths || isPublishPickingLocalPath) return;
    setShowPublishSaveDialog(false);
  }

  function buildSaveToPublishFieldMappings() {
    const schemaRows = Array.isArray(publishFieldSchema) ? publishFieldSchema : [];
    const out = [];
    for (const field of schemaRows) {
      const fieldKey = String(field?.field_key || "").trim();
      if (!fieldKey) continue;
      const rows = Array.isArray(publishFieldMappings?.[fieldKey]) ? publishFieldMappings[fieldKey] : [];
      const sources = [];
      let orderBase = 0;
      for (const row of rows) {
        const artifactId = String(row?.artifact_id || "").trim();
        const artifact = publishArtifactsById[artifactId] || null;
        const primaryPart = String(row?.primary_part || "").trim() || defaultPublishPartForArtifact(artifact);
        if (!artifactId || !primaryPart) continue;
        sources.push({
          artifact_id: artifactId,
          part: primaryPart,
          order: orderBase,
        });
        orderBase += 1;
        if (row?.include_tags) {
          sources.push({
            artifact_id: artifactId,
            part: "tags_json",
            order: orderBase,
          });
          orderBase += 1;
        }
      }
      if (sources.length) {
        out.push({ field_key: fieldKey, sources });
      }
    }
    return out;
  }

  async function onDownloadBundle() {
    setError("");
    setPublishSaveMessage("");
    const projectId = String(form.project_id || "").trim();
    const platform = String(publishSelectedPlatform || "").trim();
    if (!projectId) { setError("Project ID is required."); return; }
    if (!platform) { setError("Select a platform first."); return; }
    const userName = String(publishSaveUserName || "").trim();
    if (!userName) { setError("Name is required."); return; }
    setBusy(true);
    try {
      const fieldMappings = buildSaveToPublishFieldMappings();
      const headers = { "Content-Type": "application/json" };
      if (authToken) headers.Authorization = `Bearer ${authToken}`;
      const rawPath = String(publishSaveOutputPath || "").trim();
      const isRemote = /^(azure|az|gs):\/\//i.test(rawPath);
      const outputPath = isRemote ? rawPath : null;
      const res = await fetch(`${apiBaseUrl}/api/v1/publishing/download-bundle`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          project_id: projectId,
          platform,
          user_name: userName,
          output_path: outputPath,
          field_mappings: fieldMappings,
        }),
      });
      if (!res.ok) {
        const txt = await res.text();
        let detail = txt;
        try { detail = JSON.parse(txt)?.detail || txt; } catch {}
        throw new Error(detail);
      }
      if (outputPath) {
        const result = await res.json();
        const savedPath = String(result?.output_path || "").trim();
        setPublishSaveMessage(savedPath ? `ZIP saved to: ${savedPath}` : "ZIP saved.");
      } else {
        const blob = await res.blob();
        const disposition = res.headers.get("Content-Disposition") || "";
        const match = disposition.match(/filename="?([^"]+)"?/);
        const filename = match ? match[1] : `${platform}_${userName}.zip`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        setPublishSaveMessage("Bundle downloaded.");
      }
      window.localStorage.setItem("cpublishr_publish_destination_mode", "download");
      setShowPublishSaveDialog(false);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveToPublish() {
    return onDownloadBundle();
  }

  function addPublishSourceRow(fieldKey) {
    setPublishFieldMappings((prev) => {
      const key = String(fieldKey || "").trim();
      const rows = Array.isArray(prev?.[key]) ? prev[key] : [];
      return { ...prev, [key]: [...rows, makePublishSourceRow()] };
    });
  }

  function removePublishSourceRow(fieldKey, sourceId) {
    setPublishFieldMappings((prev) => {
      const key = String(fieldKey || "").trim();
      const rows = (Array.isArray(prev?.[key]) ? prev[key] : []).filter((r) => r?.source_id !== sourceId);
      return { ...prev, [key]: rows };
    });
  }

  function updatePublishSourceRow(fieldKey, sourceId, patch) {
    setPublishFieldMappings((prev) => {
      const key = String(fieldKey || "").trim();
      const rows = Array.isArray(prev?.[key]) ? prev[key] : [];
      return {
        ...prev,
        [key]: rows.map((row, idx) => {
          if (row?.source_id !== sourceId) return row;
          const next = { ...row, ...patch };
          next.order = idx;
          return next;
        }),
      };
    });
  }

  function resetArtifactEditPanel() {
    setArtifactEditMode("none");
    setIsArtifactEditing(false);
    setArtifactInlineText("");
    setArtifactIterateInstruction("");
  }

  function hydrateIterateStateFromArtifact(artifact) {
    const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
    const settings = payload?.settings && typeof payload.settings === "object" ? payload.settings : {};
    const styleByKind = settings?.style_settings_by_kind && typeof settings.style_settings_by_kind === "object"
      ? settings.style_settings_by_kind
      : {};
    const styleByFormat = settings?.style_settings_by_format && typeof settings.style_settings_by_format === "object"
      ? settings.style_settings_by_format
      : {};
    const kind = String(artifact?.kind || "").trim().toLowerCase();
    const fmt = String(artifact?.format || "").trim();

    if (kind === "text") {
      const textStyle = styleByKind?.text && typeof styleByKind.text === "object" ? styleByKind.text : {};
      const toneBase = toneBaseFromProjectTone(form.tone_preference);
      const nextTone = makeDefaultToneNuance(toneBase);
      const toneNuance = textStyle?.tone_nuance && typeof textStyle.tone_nuance === "object" ? textStyle.tone_nuance : {};
      setArtifactIterateToneNuance({ ...nextTone, ...toneNuance, tone_base: toneBase });
      setArtifactIterateFrameworkMode(String(toneNuance?.framework_mode || "light"));
      const source = String(textStyle?.style_source || "").trim().toLowerCase() === "voice_profile" ? "voice_profile" : "manual";
      setArtifactIterateStyleSource(source);
      setArtifactIterateVoiceProfileId(String(textStyle?.voice_profile_id || form.voice_profile_id || "").trim());
      setArtifactIterateManualCoreVoice(String(textStyle?.core_voice || "").trim());
    }

    if (kind === "image") {
      const imageStyle = styleByKind?.image && typeof styleByKind.image === "object" ? styleByKind.image : {};
      setArtifactIterateImageStyle((prev) => ({
        ...prev,
        ...imageStyle,
        brand_colors: {
          ...(prev?.brand_colors || {}),
          ...(imageStyle?.brand_colors && typeof imageStyle.brand_colors === "object" ? imageStyle.brand_colors : {}),
        },
      }));
    }

    if (kind === "video" || kind === "gif") {
      const videoStyleRaw = kind === "gif" ? styleByKind?.gif : styleByKind?.video;
      const videoStyle = videoStyleRaw && typeof videoStyleRaw === "object" ? videoStyleRaw : {};
      setArtifactIterateVideoStyle((prev) => ({
        ...prev,
        ...videoStyle,
        brand_colors: {
          ...(prev?.brand_colors || {}),
          ...(videoStyle?.brand_colors && typeof videoStyle.brand_colors === "object" ? videoStyle.brand_colors : {}),
        },
      }));
    }

    if (fmt && styleByFormat?.[fmt] && typeof styleByFormat[fmt] === "object") {
      setArtifactIterateFormatAdvanced((prev) => ({
        ...prev,
        [fmt]: {
          ...(prev?.[fmt] || {}),
          ...(styleByFormat[fmt] || {}),
        },
      }));
    }
  }

  function startInlineArtifactEdit(artifact) {
    const payload = artifact?.payload_json && typeof artifact.payload_json === "object" ? artifact.payload_json : {};
    const body = typeof payload?.body === "string" ? payload.body : "";
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const merged = body || items.map((x) => String(x?.text || "").trim()).filter(Boolean).join("\n");
    setArtifactInlineText(merged);
    setArtifactEditMode("inline");
  }

  function startIterateArtifactEdit(artifact) {
    setArtifactIterateInstruction("");
    hydrateIterateStateFromArtifact(artifact);
    setArtifactEditMode("iterate");
  }

  async function refreshStoredArtifactsAfterEdit() {
    const out = await request("GET", `/api/v1/artifacts/${form.project_id}`);
    const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
    setStoredArtifacts(items);
    const formats = uniqueStrings(items.map((a) => String(a?.format || "").trim()).filter(Boolean));
    setStoredArtifactFormatsForProject(formats);
    if (!formats.includes(selectedStoredFormat)) {
      setSelectedStoredFormat(formats[0] || "");
      setSelectedStoredArtifactTab(0);
    }
  }

  async function onSaveInlineArtifactEdit() {
    const artifactId = String(selectedStoredArtifact?.artifact_id || "").trim();
    if (!artifactId) return;
    setError("");
    setIsArtifactEditing(true);
    try {
      await request("POST", "/api/v1/artifacts/edit", {
        artifact_id: artifactId,
        mode: "inline",
        inline_content: String(artifactInlineText || ""),
      });
      await refreshStoredArtifactsAfterEdit();
      resetArtifactEditPanel();
      setMessage("Artifact updated inline.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsArtifactEditing(false);
    }
  }

  async function onIterateArtifactEdit() {
    const artifact = selectedStoredArtifact;
    const artifactId = String(artifact?.artifact_id || "").trim();
    if (!artifactId) return;
    if (!(artifactIterateInstruction || "").trim()) {
      setError("Edit Instruction is required for iterate.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    const iterateKind = String(artifact?.kind || "").trim().toLowerCase();
    if (iterateKind === "text" && artifactIterateStyleSource === "voice_profile" && !(artifactIterateVoiceProfileId || form.voice_profile_id || "").trim()) {
      setError("Select a voice profile or switch to manual style.");
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }
    setError("");
    setIsArtifactEditing(true);
    try {
      await request("POST", "/api/v1/artifacts/edit", {
        artifact_id: artifactId,
        mode: "iterate",
        edit_instruction: String(artifactIterateInstruction || "").trim(),
        style_settings_by_kind: buildIterateKindStyleSettings(artifact),
        style_settings_by_format: buildIterateFormatStyleOverrides(artifact),
        source_blob_paths: getStoredArtifactSourceBlobPaths(artifact),
      });
      await refreshStoredArtifactsAfterEdit();
      resetArtifactEditPanel();
      setMessage("Artifact iterated successfully.");
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setIsArtifactEditing(false);
    }
  }

  function startEditingArtifactTitle(artifact) {
    const id = String(artifact?.artifact_id || "").trim();
    if (!id) return;
    setEditingArtifactTitleId(id);
    setEditingArtifactTitleValue(String(artifact?.title || "").trim());
  }

  function cancelEditingArtifactTitle() {
    setEditingArtifactTitleId("");
    setEditingArtifactTitleValue("");
    setIsSavingArtifactTitle(false);
  }

  async function saveArtifactTitle(artifact) {
    const artifactId = String(artifact?.artifact_id || "").trim();
    if (!artifactId) return;
    if (!editingArtifactTitleId || editingArtifactTitleId !== artifactId) return;
    setError("");
    setIsSavingArtifactTitle(true);
    try {
      const out = await request("PATCH", `/api/v1/artifacts/item/${artifactId}/title`, {
        title: String(editingArtifactTitleValue || "").trim() || null,
      });
      const nextTitle = String(out?.title || "").trim() || null;
      setStoredArtifacts((prev) => (Array.isArray(prev) ? prev.map((a) => (
        a?.artifact_id === artifactId ? { ...a, title: nextTitle } : a
      )) : prev));
      setPublishArtifacts((prev) => (Array.isArray(prev) ? prev.map((a) => (
        a?.artifact_id === artifactId ? { ...a, title: nextTitle } : a
      )) : prev));
      setArtifactOutput((prev) => {
        if (!prev || !Array.isArray(prev.artifacts)) return prev;
        return {
          ...prev,
          artifacts: prev.artifacts.map((a) => (a?.artifact_id === artifactId ? { ...a, title: nextTitle } : a)),
        };
      });
      cancelEditingArtifactTitle();
    } catch (e) {
      setError(e.message || String(e));
      setIsSavingArtifactTitle(false);
    }
  }

  useEffect(() => {
    if (page !== "artifacts") return;
    setArtifactsViewMode("");
    setSelectedArtifactFormats([]);
    setArtifactGenerateStep("formats");
    setArtifactStyleKindPanel("text");
    resetArtifactEditPanel();
  }, [page]);

  useEffect(() => {
    resetArtifactEditPanel();
  }, [selectedStoredFormat, selectedStoredArtifactTab]);

  useEffect(() => {
    if (!isArtifactEditActive) return;
    autoResizeTextarea(artifactInlineTextareaRef.current);
    autoResizeTextarea(artifactIterateInstructionTextareaRef.current);
    autoResizeTextarea(artifactIterateVoiceStyleTextareaRef.current);
  }, [
    isArtifactEditActive,
    artifactInlineText,
    artifactIterateInstruction,
    artifactIterateManualCoreVoice,
    selectedStoredArtifact?.artifact_id,
  ]);

  useEffect(() => {
    if (page !== "editorial") return;
    if (editorMode === "inline") {
      autoResizeTextarea(editorialInlineTextareaRef.current);
    }
    if (editorMode === "iterate") {
      autoResizeTextarea(editorialFeedbackTextareaRef.current);
    }
  }, [page, editorMode, workingContent, feedbackText, selectedVersion?.version_number]);

  useEffect(() => {
    if (!artifactSelectedKinds.length) return;
    if (!artifactSelectedKinds.includes(artifactStyleKindPanel)) {
      setArtifactStyleKindPanel(artifactSelectedKinds[0]);
    }
  }, [artifactSelectedKinds, artifactStyleKindPanel]);

  useEffect(() => {
    const hasMediaStyleConsumer =
      artifactSelectedKinds.includes("image") || artifactSelectedKinds.includes("video") || artifactSelectedKinds.includes("gif");
    if (page !== "artifacts" || artifactsViewMode !== "generate" || artifactGenerateStep !== "style" || !hasMediaStyleConsumer) {
      return;
    }
    const projectId = String(form.project_id || "").trim();
    if (!projectId || !authToken) return;
    if (latestProjectImageStyleSeed) return;
    if (artifactStyleSeedFetchRef.current === projectId) return;
    artifactStyleSeedFetchRef.current = projectId;
    request("GET", `/api/v1/artifacts/${projectId}`)
      .then((out) => {
        const items = Array.isArray(out?.artifacts) ? out.artifacts : [];
        setStoredArtifacts(items);
      })
      .catch(() => {});
  }, [
    page,
    artifactsViewMode,
    artifactGenerateStep,
    artifactSelectedKinds,
    form.project_id,
    authToken,
    latestProjectImageStyleSeed,
  ]);

  useEffect(() => {
    const seed = latestProjectImageStyleSeed;
    if (!seed) return;
    setArtifactImageStyle((prev) => {
      const next = { ...prev };
      let changed = false;
      if ((!String(prev?.palette_mode || "").trim() || String(prev?.palette_mode) === "muted") && seed.palette_mode) {
        next.palette_mode = seed.palette_mode;
        changed = true;
      }
      if ((!String(prev?.mood || "").trim() || String(prev?.mood) === "premium") && seed.mood) {
        next.mood = seed.mood;
        changed = true;
      }
      return changed ? next : prev;
    });
    setArtifactVideoStyle((prev) => {
      const next = { ...prev };
      let changed = false;
      if ((!String(prev?.palette_mode || "").trim() || String(prev?.palette_mode) === "muted") && seed.palette_mode) {
        next.palette_mode = seed.palette_mode;
        changed = true;
      }
      if ((!String(prev?.mood || "").trim() || String(prev?.mood) === "energetic") && seed.mood) {
        next.mood = seed.mood;
        changed = true;
      }
      return changed ? next : prev;
    });
  }, [latestProjectImageStyleSeed]);

  useEffect(() => {
    setArtifactToneNuance((prev) => {
      const nextBase = projectToneBase;
      if ((prev?.tone_base || "") === nextBase) return prev;
      const defaults = makeDefaultToneNuance(nextBase);
      return {
        ...defaults,
        directness: prev?.directness ?? defaults.directness,
        warmth: prev?.warmth ?? defaults.warmth,
        energy: prev?.energy ?? defaults.energy,
        authority: prev?.authority ?? defaults.authority,
      };
    });
    if (projectToneBase === "analytical") setArtifactFrameworkMode("light");
  }, [projectToneBase]);

  useEffect(() => {
    const next = (artifactStyleVoiceProfileId || form.voice_profile_id || "").trim();
    if (!artifactStyleVoiceProfileId && next) {
      setArtifactStyleVoiceProfileId(next);
    }
  }, [form.voice_profile_id, artifactStyleVoiceProfileId]);

  useEffect(() => {
    if (artifactStyleSource !== "voice_profile") return;
    if (!artifactStyleVoiceProfileId) {
      setArtifactStyleVoiceProfileDetail(null);
      return;
    }
    loadArtifactVoiceProfilePreview(artifactStyleVoiceProfileId).catch(() => {});
  }, [artifactStyleSource, artifactStyleVoiceProfileId, authToken]);

  useEffect(() => {
    if (projectHasSavedVoiceProfileOption) return;
    setArtifactStyleSource("manual");
    setArtifactStyleVoiceProfileDetail(null);
  }, [projectHasSavedVoiceProfileOption]);

  useEffect(() => {
    if (!selectedVersion) return;
    setWorkingContent(selectedVersion.content || "");
    setFeedbackPreviewContent("");
  }, [selectedVersionNumber]);

  useEffect(() => {
    loadCurrentUser().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const projectId = (form.project_id || "").trim();
    checkExistingContent(projectId);
  }, [form.project_id, apiBaseUrl, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) {
      setHasStoredArtifactsForProject(false);
      setIsCheckingStoredArtifacts(false);
      setStoredArtifactFormatsForProject([]);
      setPublishArtifacts([]);
      setPublishFieldSchema([]);
      setPublishFieldMappings({});
      setPublishPlatforms([]);
      setPublishSelectedPlatform("");
      return;
    }
    const projectId = (form.project_id || "").trim();
    setStoredArtifacts([]);
    setSelectedStoredFormat("");
    setSelectedStoredArtifactTab(0);
    setSelectedArtifactFormats([]);
    setArtifactsViewMode("");
    setArtifactGenerateStep("formats");
    setPublishArtifacts([]);
    setPublishFieldMappings({});
    checkStoredArtifactsAvailability(projectId);
  }, [form.project_id, apiBaseUrl, isAuthenticated, authToken]);

  useEffect(() => {
    if (!isAuthenticated) {
      setArtifactFormatsByKind({});
      return;
    }
    let ignore = false;
    async function loadArtifactFormats() {
      try {
        const out = await request("GET", "/api/v1/artifacts/catalog/formats");
        const byKind = out?.formats_by_kind && typeof out.formats_by_kind === "object" ? out.formats_by_kind : {};
        if (!ignore) setArtifactFormatsByKind(byKind);
      } catch {
        if (!ignore) setArtifactFormatsByKind({});
      }
    }
    loadArtifactFormats();
    return () => {
      ignore = true;
    };
  }, [apiBaseUrl, isAuthenticated, authToken]);

  useEffect(() => {
    if (!authToken) return;
    loadUserProjects().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!authToken) {
      setUserProjects([]);
      return;
    }
    loadVpCollections().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!authToken) return;
    loadPublishPlatforms().catch(() => {});
  }, [authToken, apiBaseUrl]);

  useEffect(() => {
    if (!authToken || page !== "publish") return;
    loadPublishArtifacts(form.project_id).catch(() => {});
  }, [authToken, apiBaseUrl, page, form.project_id]);

  useEffect(() => {
    if (!authToken || page !== "publish") return;
    loadPublishFieldSchema(publishSelectedPlatform).catch(() => {});
  }, [authToken, apiBaseUrl, page, publishSelectedPlatform]);

  useEffect(() => {
    if (!authToken) return;
    loadVpCollectionDetail(vpSelectedCollectionId).catch(() => {});
  }, [vpSelectedCollectionId, authToken]);

  useEffect(() => {
    if (!authToken) return;
    loadVpProfileDetail(vpSelectedProfileId).catch(() => {});
  }, [vpSelectedProfileId, authToken]);

  useEffect(() => {
    if (!authToken) return;
    loadVpVersionDetail(vpSelectedVersionId).catch(() => {});
  }, [vpSelectedVersionId, authToken]);

  useEffect(() => {
    if (!platformTargets.length) {
      setForm((prev) => ({ ...prev, distribution_targets: [] }));
      setVpCreateForm((prev) => ({ ...prev, platforms: [] }));
      return;
    }
    setForm((prev) => {
      const current = Array.isArray(prev.distribution_targets) ? prev.distribution_targets : [];
      const filtered = current.filter((x) => platformTargets.includes(String(x || "").trim()));
      return { ...prev, distribution_targets: filtered };
    });
    setVpCreateForm((prev) => {
      const current = Array.isArray(prev.platforms) ? prev.platforms : [];
      const filtered = current.filter((x) => platformTargets.includes(String(x || "").trim()));
      return { ...prev, platforms: filtered.length ? filtered : [platformTargets[0]] };
    });
  }, [platformTargets]);

  const showWorkflowRegion = !isAuthenticated || (page !== "settings" && page !== "projects");

  return (
    <>
      <div className="top-banner">
        <div className="container top-banner-inner">
          <div className="row" style={{ justifyContent: "space-between" }}>
            <div className="top-banner-brand">
              <img
                src={publishrLogo}
                alt="Publishr logo"
                className="top-banner-logo"
              />
            </div>
            {isAuthenticated ? (
              <div className="top-banner-actions">
                <div className="row top-banner-buttons">
                  {(page !== "projects" && page !== "settings") ? (
                    <button className="secondary" disabled={busy} onClick={() => setPage("projects")}>Projects</button>
                  ) : null}
                  {page !== "settings" ? (
                    <button className="secondary" disabled={busy} onClick={() => setPage("settings")}>Settings</button>
                  ) : null}
                  {page === "settings" ? (
                    <button
                      className="secondary"
                      disabled={busy}
                      onClick={() => {
                        if (isExistingProjectFlow) {
                          onOpenEditorialPage().catch(() => {});
                          return;
                        }
                        setPage("setup");
                      }}
                    >
                      Back to Workflow
                    </button>
                  ) : null}
                  <button className="secondary" disabled={busy} onClick={onLogout}>Logout</button>
                </div>
                <span className="note top-banner-user">User ID: {currentUser?.user_id || "-"}</span>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="container">
        {isAuthenticated && page === "projects" ? (
          <div className="card">
            <div className="row" style={{ justifyContent: "space-between", marginBottom: "10px" }}>
              <h3 style={{ margin: 0 }}>Created Projects</h3>
              <button className="secondary" disabled={busy} onClick={onCreateNewProject}>+ Create New Project</button>
            </div>
            {isProjectsLoading ? <p className="note">Loading projects...</p> : null}
            {!isProjectsLoading && userProjects.length === 0 ? <p className="note">No projects found.</p> : null}
            <div className="row">
              {userProjects.map((p) => {
                const projectId = String(p?.project_id || "").trim();
                if (!projectId) return null;
                return (
                  <button
                    key={`project-list-${projectId}`}
                    className={form.project_id === projectId ? "primary" : "secondary"}
                    disabled={busy}
                    onClick={() => onSelectExistingProject(projectId)}
                  >
                    {projectId}
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {(showWorkflowRegion || error || isGenerating || isArtifactGenerating || isStoredArtifactsLoading) ? (
          <div className="card">
            {showWorkflowRegion ? (
              <>
                <div className="grid two">
          {!isAuthenticated ? (
            <div className="auth-panel">
              <div className="auth-mode-row">
                <div className="auth-mode-toggle row">
                  <button className={authMode === "login" ? "primary" : "secondary"} disabled={busy} onClick={() => setAuthMode("login")}>Login</button>
                  <button className={authMode === "signup" ? "primary" : "secondary"} disabled={busy} onClick={() => setAuthMode("signup")}>Signup</button>
                </div>
              </div>
              <div className="auth-fields-row">
                <div>
                  <label>User ID</label>
                  <input value={authForm.user_id} onChange={(e) => setAuthForm({ ...authForm, user_id: e.target.value })} />
                </div>
                <div>
                  <label>Password</label>
                  <input type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} />
                </div>
              </div>
              {authMode === "signup" ? (
                <div className="auth-email-row">
                  <div>
                    <label>Email</label>
                    <input value={authForm.email} onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} />
                  </div>
                </div>
              ) : null}
              <div className="auth-submit-row">
                <button className="primary" disabled={busy} onClick={onAuthSubmit}>
                  {busy ? "Please wait..." : authMode === "signup" ? "Sign Up" : "Login"}
                </button>
              </div>
            </div>
          ) : (
            <>
              <div>
                <label>Project ID</label>
                {isCreatingNewProject ? (
                  <input
                    value={form.project_id}
                    onChange={(e) => onNewProjectIdChange(e.target.value)}
                    placeholder="Enter a new project ID"
                  />
                ) : (
                  <div className="project-id-inline">{form.project_id || "-"}</div>
                )}
                {page === "setup" && isProjectsLoading ? (
                  <p className="note" style={{ marginTop: "6px" }}>Loading your projects...</p>
                ) : null}
                {page === "setup" && hasExistingContent ? (
                  <div className="row" style={{ marginTop: "8px" }}>
                    <button
                      type="button"
                      className="primary"
                      disabled={busy || isCheckingProjectData || !canGenerateContent}
                      onClick={() => setShowGenerateSetupForm(true)}
                    >
                      Generate Content
                    </button>
                  </div>
                ) : null}
                {page === "setup" && isCheckingProjectData ? (
                  <p className="note" style={{ marginTop: "6px" }}>Checking project data...</p>
                ) : null}
              </div>
              <div className="workflow-steps-block">
                <div className="workflow-stepper">
                  {!isExistingProjectFlow ? (
                    <>
                      <button
                        className={`workflow-step ${page === "setup" ? "workflow-step-active" : ""}`}
                        disabled={busy}
                        onClick={() => setPage("setup")}
                      >
                        <span className="workflow-step-label">Setup</span>
                      </button>
                      <span className="workflow-step-arrow">›</span>
                    </>
                  ) : null}
                  <button
                    className={`workflow-step ${page === "editorial" ? "workflow-step-active" : ""}`}
                    disabled={busy}
                    onClick={onOpenEditorialPage}
                  >
                    <span className="workflow-step-label">Editorial</span>
                  </button>
                  <span className="workflow-step-arrow">›</span>
                  <button
                    className={`workflow-step ${page === "artifacts" ? "workflow-step-active" : ""}`}
                    disabled={busy}
                    onClick={() => setPage("artifacts")}
                  >
                    <span className="workflow-step-label">Artifacts</span>
                  </button>
                  <span className="workflow-step-arrow">›</span>
                  <button
                    className={`workflow-step ${page === "publish" ? "workflow-step-active" : ""}`}
                    disabled={busy}
                    onClick={() => setPage("publish")}
                  >
                    <span className="workflow-step-label">Publish</span>
                  </button>
                </div>
              </div>
              </>
            )}
            </div>
            </>
          ) : null}
            {error ? <div className="status warn">{error}</div> : null}
            {(isGenerating || isArtifactGenerating || isStoredArtifactsLoading) ? (
              <div style={{ marginTop: "10px" }}>
                <div className="progress-label">
                  {isGenerating
                    ? `Generating content (Node 0-2): ${nodeProgress}%`
                    : (isArtifactGenerating ? "Generating artifacts..." : "Loading stored artifacts...")}
                </div>
                {isArtifactGenerating && selectedArtifactFormats.some((f) => ["post_image","thumbnail","banner","cover"].includes(f)) && (
                  <div style={{ fontSize: "0.82em", color: "#888", marginTop: "4px" }}>
                    Image and video generation may take a while — please hang on.
                  </div>
                )}
                <div className="progress-track">
                  <div
                    className={`progress-fill ${isGenerating ? "" : "indeterminate"}`}
                    style={isGenerating ? { width: `${nodeProgress}%` } : { width: "35%" }}
                  />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

      <SetupContentForm
        active={isAuthenticated && page === "setup" && showGenerateSetupForm}
        busy={busy}
        isCheckingProjectData={isCheckingProjectData}
        canGenerateContent={canGenerateContent}
        onGenerateContent={onGenerateContent}
        isGenerating={isGenerating}
        canContinueToEditorial={canContinueToEditorial}
        setPage={setPage}
        nodeAudit={nodeAudit}
        form={form}
        setForm={setForm}
        TOPIC_TITLE_SUGGESTION={TOPIC_TITLE_SUGGESTION}
        CORE_IDEA_SUGGESTION={CORE_IDEA_SUGGESTION}
        AUDIENCE_OPTIONS={AUDIENCE_OPTIONS}
        AUDIENCE_FAMILIARITY_OPTIONS={AUDIENCE_FAMILIARITY_OPTIONS}
        DETAIL_LEVEL_OPTIONS={DETAIL_LEVEL_OPTIONS}
        TONE_OPTIONS={TONE_OPTIONS}
        STANCE_OPTIONS={STANCE_OPTIONS}
        PRIMARY_GOAL_OPTIONS={PRIMARY_GOAL_OPTIONS}
        DESIRED_ACTION_OPTIONS={DESIRED_ACTION_OPTIONS}
        platformTargets={platformTargets}
        toggleTarget={toggleTarget}
        userContentTextareaRef={userContentTextareaRef}
        USER_CONTENT_SUGGESTION={USER_CONTENT_SUGGESTION}
      />
      <VoiceProfilesSettings
        active={isAuthenticated && page === "settings"}
        busy={busy}
        authToken={authToken}
        showVpCreateCollectionForm={showVpCreateCollectionForm}
        setShowVpCreateCollectionForm={setShowVpCreateCollectionForm}
        vpCreateForm={vpCreateForm}
        setVpCreateForm={setVpCreateForm}
        platformTargets={platformTargets}
        toggleVpPlatform={toggleVpPlatform}
        onVpCreateCollection={onVpCreateCollection}
        vpCollections={vpCollections}
        vpSelectedCollectionId={vpSelectedCollectionId}
        onSelectVpCollection={onSelectVpCollection}
        vpDatasetSourceMode={vpDatasetSourceMode}
        setVpDatasetSourceMode={setVpDatasetSourceMode}
        vpDatasetForm={vpDatasetForm}
        setVpDatasetForm={setVpDatasetForm}
        vpDatasetLocalFiles={vpDatasetLocalFiles}
        setVpDatasetLocalFiles={setVpDatasetLocalFiles}
        isVpPickingLocalDatasetPath={isVpPickingLocalDatasetPath}
        pickVpDatasetPath={pickVpDatasetPath}
        onVpCreateDataset={onVpCreateDataset}
        vpCollectionDetail={vpCollectionDetail}
        hasSelectedActiveVoiceProfiles={hasSelectedActiveVoiceProfiles}
        hasSelectedInactiveVoiceProfiles={hasSelectedInactiveVoiceProfiles}
        vpCheckedProfileIds={vpCheckedProfileIds}
        updateVpProfilesEnabled={updateVpProfilesEnabled}
        deleteVpProfiles={deleteVpProfiles}
        vpSelectedProfileId={vpSelectedProfileId}
        vpProfileComposerMode={vpProfileComposerMode}
        setVpSelectedProfileId={setVpSelectedProfileId}
        setVpProfileDetail={setVpProfileDetail}
        setVpSelectedVersionId={setVpSelectedVersionId}
        setVpVersionDetail={setVpVersionDetail}
        vpProfileForm={vpProfileForm}
        setVpProfileForm={setVpProfileForm}
        vpGenerateForm={vpGenerateForm}
        setVpGenerateForm={setVpGenerateForm}
        setVpProfileComposerMode={setVpProfileComposerMode}
        toggleVpCheckedProfile={toggleVpCheckedProfile}
        vpSelectedProfileSummary={vpSelectedProfileSummary}
        vpProfileDetail={vpProfileDetail}
        toggleVpGenerateDataset={toggleVpGenerateDataset}
        isVpGenerating={isVpGenerating}
        onVpGenerateVersion={onVpGenerateVersion}
        vpVersionDetail={vpVersionDetail}
        vpSelectedVersionId={vpSelectedVersionId}
        vpStatusInput={vpStatusInput}
        setVpStatusInput={setVpStatusInput}
        onVpActivateVersion={onVpActivateVersion}
        onVpUpdateStatus={onVpUpdateStatus}
      />

      <EditorialWorkspace
        active={isAuthenticated && page === "editorial"}
        busy={busy}
        versions={versions}
        selectedVersionNumber={selectedVersionNumber}
        applySelection={applySelection}
        getVersionLabel={getVersionLabel}
        selectedVersion={selectedVersion}
        editorMode={editorMode}
        editorialInlineTextareaRef={editorialInlineTextareaRef}
        workingContent={workingContent}
        setWorkingContent={setWorkingContent}
        autoResizeTextarea={autoResizeTextarea}
        onCancelEditorialEdit={onCancelEditorialEdit}
        onSaveInline={onSaveInline}
        onFinalizeFromInline={onFinalizeFromInline}
        setEditorMode={setEditorMode}
        setFeedbackPreviewContent={setFeedbackPreviewContent}
        onFinalizeSelected={onFinalizeSelected}
        feedbackPreviewContent={feedbackPreviewContent}
        editorialFeedbackTextareaRef={editorialFeedbackTextareaRef}
        feedbackText={feedbackText}
        setFeedbackText={setFeedbackText}
        isPreviewing={isPreviewing}
        onFeedbackPreview={onFeedbackPreview}
        onCloseEditorialPreview={onCloseEditorialPreview}
        onSavePreview={onSavePreview}
        onFinalizeFromPreview={onFinalizeFromPreview}
        onPatchKeywords={onPatchKeywords}
        keywordsInput={keywordsInput}
        setKeywordsInput={setKeywordsInput}
      />

      <ArtifactGeneratorPanel
        active={isAuthenticated && page === "artifacts"}
        busy={busy}
        artifactsViewMode={artifactsViewMode}
        setArtifactsViewMode={setArtifactsViewMode}
        isCheckingStoredArtifacts={isCheckingStoredArtifacts}
        hasStoredArtifactsForProject={hasStoredArtifactsForProject}
        onViewStoredArtifacts={onViewStoredArtifacts}
        isStoredArtifactsLoading={isStoredArtifactsLoading}
        selectedStoredFormat={selectedStoredFormat}
        setSelectedStoredFormat={setSelectedStoredFormat}
        setSelectedStoredArtifactTab={setSelectedStoredArtifactTab}
        storedFormats={storedFormats}
        artifactGenerateStep={artifactGenerateStep}
        setArtifactGenerateStep={setArtifactGenerateStep}
        setArtifactSuggestions={setArtifactSuggestions}
        selectedArtifactFormats={selectedArtifactFormats}
        fetchAndApplyArtifactSuggestions={fetchAndApplyArtifactSuggestions}
        orderArtifactFormats={orderArtifactFormats}
        artifactFormatsByKind={artifactFormatsByKind}
        artifactFormatMeta={artifactFormatMeta}
        storedArtifactCountsByFormat={storedArtifactCountsByFormat}
        toggleArtifactFormat={toggleArtifactFormat}
        artifactSelectedFormatCards={artifactSelectedFormatCards}
        artifactSelectedKinds={artifactSelectedKinds}
        artifactStyleKindPanel={artifactStyleKindPanel}
        setArtifactStyleKindPanel={setArtifactStyleKindPanel}
        projectHasSavedVoiceProfileOption={projectHasSavedVoiceProfileOption}
        artifactStyleSource={artifactStyleSource}
        setArtifactStyleSource={setArtifactStyleSource}
        artifactStyleVoiceProfileId={artifactStyleVoiceProfileId}
        setArtifactStyleVoiceProfileId={setArtifactStyleVoiceProfileId}
        setArtifactStyleVoiceProfileDetail={setArtifactStyleVoiceProfileDetail}
        approvedActiveVoiceProfileOptions={approvedActiveVoiceProfileOptions}
        isArtifactStyleVoiceProfileLoading={isArtifactStyleVoiceProfileLoading}
        artifactSelectedVoiceProfilePreview={artifactSelectedVoiceProfilePreview}
        artifactManualCoreVoice={artifactManualCoreVoice}
        setArtifactManualCoreVoice={setArtifactManualCoreVoice}
        projectToneBase={projectToneBase}
        artifactToneNuance={artifactToneNuance}
        updateArtifactToneNuance={updateArtifactToneNuance}
        artifactFrameworkMode={artifactFrameworkMode}
        setArtifactFrameworkMode={setArtifactFrameworkMode}
        humorLabelToSlider={humorLabelToSlider}
        humorSliderToLabel={humorSliderToLabel}
        artifactSelectedAdvancedFormatCards={artifactSelectedAdvancedFormatCards}
        artifactFormatAdvanced={artifactFormatAdvanced}
        artifactAdvancedOpen={artifactAdvancedOpen}
        toggleArtifactAdvancedDrawer={toggleArtifactAdvancedDrawer}
        updateArtifactAdvanced={updateArtifactAdvanced}
        toggleArtifactAdvancedAngle={toggleArtifactAdvancedAngle}
        artifactSuggestionsLoading={artifactSuggestionsLoading}
        artifactSuggestions={artifactSuggestions}
        artifactImageStyle={artifactImageStyle}
        updateArtifactImageStyle={updateArtifactImageStyle}
        artifactImageAvoidInput={artifactImageAvoidInput}
        setArtifactImageAvoidInput={setArtifactImageAvoidInput}
        addArtifactImageAvoidTag={addArtifactImageAvoidTag}
        removeArtifactImageAvoidTag={removeArtifactImageAvoidTag}
        updateArtifactImageBrandColor={updateArtifactImageBrandColor}
        artifactVideoStyle={artifactVideoStyle}
        updateArtifactVideoStyle={updateArtifactVideoStyle}
        artifactVideoAvoidInput={artifactVideoAvoidInput}
        setArtifactVideoAvoidInput={setArtifactVideoAvoidInput}
        addArtifactVideoAvoidTag={addArtifactVideoAvoidTag}
        removeArtifactVideoAvoidTag={removeArtifactVideoAvoidTag}
        updateArtifactVideoBrandColor={updateArtifactVideoBrandColor}
        canGenerateArtifactsNow={canGenerateArtifactsNow}
        onGenerateArtifacts={onGenerateArtifacts}
        isArtifactGenerating={isArtifactGenerating}
        generatedArtifacts={generatedArtifacts}
        selectedArtifactTab={selectedArtifactTab}
        setSelectedArtifactTab={setSelectedArtifactTab}
        selectedGeneratedArtifact={selectedGeneratedArtifact}
        storedArtifacts={storedArtifacts}
        filteredStoredArtifacts={filteredStoredArtifacts}
        selectedStoredArtifactTab={selectedStoredArtifactTab}
        editingArtifactTitleId={editingArtifactTitleId}
        editingArtifactTitleValue={editingArtifactTitleValue}
        setEditingArtifactTitleValue={setEditingArtifactTitleValue}
        saveArtifactTitle={saveArtifactTitle}
        cancelEditingArtifactTitle={cancelEditingArtifactTitle}
        startEditingArtifactTitle={startEditingArtifactTitle}
        selectedStoredArtifact={selectedStoredArtifact}
        artifactEditMode={artifactEditMode}
        isArtifactEditActive={isArtifactEditActive}
        artifactInlineTextareaRef={artifactInlineTextareaRef}
        artifactInlineText={artifactInlineText}
        setArtifactInlineText={setArtifactInlineText}
        autoResizeTextarea={autoResizeTextarea}
        isArtifactEditing={isArtifactEditing}
        onSaveInlineArtifactEdit={onSaveInlineArtifactEdit}
        resetArtifactEditPanel={resetArtifactEditPanel}
        artifactIterateInstructionTextareaRef={artifactIterateInstructionTextareaRef}
        artifactIterateInstruction={artifactIterateInstruction}
        setArtifactIterateInstruction={setArtifactIterateInstruction}
        artifactIterateStyleSource={artifactIterateStyleSource}
        setArtifactIterateStyleSource={setArtifactIterateStyleSource}
        artifactIterateVoiceProfileId={artifactIterateVoiceProfileId}
        setArtifactIterateVoiceProfileId={setArtifactIterateVoiceProfileId}
        artifactIterateVoiceStyleTextareaRef={artifactIterateVoiceStyleTextareaRef}
        artifactIterateManualCoreVoice={artifactIterateManualCoreVoice}
        setArtifactIterateManualCoreVoice={setArtifactIterateManualCoreVoice}
        artifactIterateToneNuance={artifactIterateToneNuance}
        updateArtifactIterateToneNuance={updateArtifactIterateToneNuance}
        artifactIterateFrameworkMode={artifactIterateFrameworkMode}
        setArtifactIterateFrameworkMode={setArtifactIterateFrameworkMode}
        artifactIterateFormatAdvanced={artifactIterateFormatAdvanced}
        updateArtifactIterateAdvanced={updateArtifactIterateAdvanced}
        artifactIterateImageStyle={artifactIterateImageStyle}
        updateArtifactIterateImageStyle={updateArtifactIterateImageStyle}
        updateArtifactIterateImageBrandColor={updateArtifactIterateImageBrandColor}
        artifactIterateVideoStyle={artifactIterateVideoStyle}
        updateArtifactIterateVideoStyle={updateArtifactIterateVideoStyle}
        updateArtifactIterateVideoBrandColor={updateArtifactIterateVideoBrandColor}
        onIterateArtifactEdit={onIterateArtifactEdit}
        startInlineArtifactEdit={startInlineArtifactEdit}
        startIterateArtifactEdit={startIterateArtifactEdit}
      />
      <PublishPanel
        active={isAuthenticated && page === "publish"}
        busy={busy}
        publishSelectedPlatform={publishSelectedPlatform}
        setPublishSelectedPlatform={setPublishSelectedPlatform}
        isPublishPlatformsLoading={isPublishPlatformsLoading}
        publishPlatforms={publishPlatforms}
        isPublishArtifactsLoading={isPublishArtifactsLoading}
        isPublishFieldSchemaLoading={isPublishFieldSchemaLoading}
        publishFieldSchema={publishFieldSchema}
        publishFieldMappings={publishFieldMappings}
        publishArtifacts={publishArtifacts}
        publishArtifactsById={publishArtifactsById}
        addPublishSourceRow={addPublishSourceRow}
        updatePublishSourceRow={updatePublishSourceRow}
        removePublishSourceRow={removePublishSourceRow}
        formProjectId={form.project_id}
        areRequiredPublishFieldsMapped={areRequiredPublishFieldsMapped}
        openSaveToPublishDialog={openSaveToPublishDialog}
        publishSaveMessage={publishSaveMessage}
        showPublishSaveDialog={showPublishSaveDialog}
        closeSaveToPublishDialog={closeSaveToPublishDialog}
        publishSaveUserName={publishSaveUserName}
        setPublishSaveUserName={setPublishSaveUserName}
        publishSaveOutputPath={publishSaveOutputPath}
        setPublishSaveOutputPath={setPublishSaveOutputPath}
        onSaveToPublish={onSaveToPublish}
      />

      </div>
    </>
  );
}






