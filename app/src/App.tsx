import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";

import { getCurrentWindow } from "@tauri-apps/api/window";
import type {
  AnalysisColumnRole,
  RawsightProject,
} from "./types/project";
import "./App.css";
import type {
  RawAnalysisColumnResult,
} from "./types/rawAnalysis";
import { RawAnalysisVisualization } from "./components/RawAnalysisVisualization";
import { WideTemporalSeriesDetailPanel } from "./components/WideTemporalSeriesDetailPanel";
import type {
  LongTemporalSeriesDetailResult,
  LongTemporalSeriesResult,
} from "./types/longTemporalSeries";
import {
  LongTemporalSeriesChart,
} from "./components/LongTemporalSeriesChart";
import type {
  WideTemporalSeriesDetail,
  WideTemporalSeriesPage,
  WideTemporalSeriesSummary,
} from "./types/wideTemporalExplore";
import type {
  WideTemporalReferenceExecution,
} from "./types/wideTemporalReference";
import type {
  WideTemporalReferenceComparisonExecution,
} from "./types/wideTemporalReferenceComparison";

type FileInfo = {
  name: string;
  path: string;
  extension: string;
  size: number;

};
type SemanticHint = {
  suggested_type: string;
  format: string;
  confidence: number;
  valid_count: number;
  candidate_count: number;
  zero_count: number;
};
type ValueEvidence = {
  kind: string;
  observed_values: number[];
  observed_state_count: number;
  zero_count: number;
  one_count: number;
  other_count: number;
};
type ColumnInfo = {
  name: string;
  type: string;
  null_count: number | null;
  null_percent: number | null;
  distinct_count: number | null;
  unique_percent: number | null;
  min: string | number | null;
  max: string | number | null;
  semantic_hint: SemanticHint | null;
  value_evidence?: ValueEvidence | null;
};
type RowInspection = {
  filter: {
    column: string;
    value: string;
  };
  total_rows: number;
  returned_rows: number;
  columns: string[];
  rows: (string | number | boolean | null)[][];
};

type TemporalAxisOrientation = {
  orientation: "horizontal" | "vertical" | "ambiguous" | "none";
  horizontal_candidate_count: number;
  vertical_candidate_count: number;
};

type AnalysisStrategyProfile = {
  strategy:
  | "wide_temporal"
  | "long_temporal"
  | "conservative_tabular"
  | "conservative_unknown"
  | string;
  can_use_legacy_profile: boolean;
  reason_codes: string[];
};

type StructuralTemporalAxis = {
  orientation: "horizontal" | "vertical";
  sequence_index: number;
  start_index: number;
  end_index: number;
  length: number;
  format: string | null;
  range_start: string | null;
  range_end: string | null;
  order: string | null;
};

type StructuralModelProfile = {
  logical_structure?: {
    structure_type?: string;
    temporal_axis?: StructuralTemporalAxis | null;
    temporal_axis_candidates?: StructuralTemporalAxis[];
    temporal_axis_orientation?: TemporalAxisOrientation;
  };
};

type DatasetProfile = {
  file: string;
  rows: number;
  column_count: number;
  duplicate_rows: number | null;
  duplicate_percent: number | null;
  missing_values: number | null;
  missing_percent: number | null;
  columns: ColumnInfo[];
  analysis_strategy?: AnalysisStrategyProfile;
  structural_model?: StructuralModelProfile;
  wide_temporal?: WideTemporalProfile;
  long_temporal?: LongTemporalProfile;
};

type WideTemporalSeriesClassification = {
  no_numeric_data: number;
  insufficient_adjacent_observations: number;
  constant: number;
  non_decreasing: number;
  non_increasing: number;
  mixed: number;
};

type WideTemporalValueAnalysis = {
  status: string;
  analysis_kind: string;

  series_count: number;
  temporal_value_count: number;
  numeric_value_count: number;
  missing_value_count: number;
  non_numeric_value_count: number;
  zero_value_count: number;

  numeric_min: number | null;
  numeric_max: number | null;

  adjacent_transition_count: number;
  positive_transition_count: number;
  negative_transition_count: number;
  unchanged_transition_count: number;

  largest_positive_change: number | null;
  largest_negative_change: number | null;

  series_with_missing_values: number;
  series_with_non_numeric_values: number;
  series_with_negative_transitions: number;

  series_classification: WideTemporalSeriesClassification;
};

type WideTemporalValueExecution = {
  status: string;
  execution_mode: string;
  rows_processed: number;
};

type WideTemporalProfile = {
  status: string;
  axis_orientation: string | null;

  temporal_column_start_index: number | null;
  temporal_column_end_index: number | null;

  temporal_column_count: number | null;
  non_temporal_column_count: number | null;

  format: string | null;
  range_start: string | null;
  range_end: string | null;
  order: string | null;

  distinct_timestamp_count: number | null;
  dominant_interval_seconds: number | null;
  cadence_consistency: number | null;

  value_analysis?: WideTemporalValueAnalysis;
  value_analysis_execution?: WideTemporalValueExecution;
};

type LongTemporalLargestPositiveInterval = {
  from_index: number;
  to_index: number;
  from_value: string;
  to_value: string;
  interval_seconds: number;
  multiple_of_dominant_interval: number | null;
};

type LongTemporalContinuity = {
  value_count: number;
  temporal_value_count: number;
  missing_count: number;

  first_value: string | null;
  last_value: string | null;
  range_start: string | null;
  range_end: string | null;

  observed_order: string | null;

  positive_observed_transitions: number;
  zero_observed_transitions: number;
  negative_observed_transitions: number;

  adjacent_delta_count: number;

  positive_adjacent_intervals: number;
  zero_adjacent_deltas: number;
  negative_adjacent_deltas: number;

  min_observed_delta_seconds: number | null;
  max_observed_delta_seconds: number | null;

  min_positive_interval_seconds: number | null;
  max_positive_interval_seconds: number | null;

  dominant_positive_interval_seconds: number | null;
  dominant_positive_interval_count: number;
  positive_interval_consistency: number | null;

  interval_frequency_complete: boolean;
  distinct_positive_interval_count: number | null;

  largest_positive_interval_limit: number;
  largest_positive_interval_count: number;
  largest_positive_intervals: LongTemporalLargestPositiveInterval[];
};

type LongTemporalExecution = {
  mode: string | null;
  observed_order_basis: string | null;
  canonical_order_established: boolean | null;
  limitations: string[];

  execution_limits: {
    interval_frequency_limit: number;
    largest_positive_interval_limit: number;
  };
};

type LongTemporalProfile = {
  status: string;
  axis_orientation: string | null;

  temporal_column_index: number | null;
  temporal_column_name: string | null;

  range_start: string | null;
  range_end: string | null;

  continuity?: LongTemporalContinuity | null;
  execution?: LongTemporalExecution | null;
};

const WIDE_TEMPORAL_SERIES_PAGE_SIZE = 10;

type StructureInspectionResult = {
  file_name: string;
  extension: string;
  column_count: number;
  columns: {
    name: string;
    technical_type: string;
  }[];
};

type ProfileProgress = {
  message: string;
};

type AppSettings = {
  defaultProjectRoot: string;
};

type ProjectListItem = {
  id: string;
  name: string;
  path: string;
  updatedAt: string;
};

type ProjectSection =
  | "overview"
  | "data"
  | "metadata"
  | "lineup"
  | "analysis"
  | "raw_analysis"
  | "history";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kilobytes = bytes / 1024;

  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`;
  }

  const megabytes = kilobytes / 1024;

  if (megabytes < 1024) {
    return `${megabytes.toFixed(1)} MB`;
  }

  const gigabytes = megabytes / 1024;

  return `${gigabytes.toFixed(2)} GB`;
}
function formatProfileValue(value: string | number | null): string {
  if (value === null) {
    return "—";
  }

  return String(value);
}

function formatCadence(
  seconds: number | null,
): string {
  if (seconds === null) {
    return "Unknown";
  }

  if (seconds === 86400) {
    return "Daily";
  }

  if (seconds === 3600) {
    return "Hourly";
  }

  if (seconds === 604800) {
    return "Weekly";
  }

  if (seconds % 86400 === 0) {
    const days = seconds / 86400;
    return `${days} day${days === 1 ? "" : "s"}`;
  }

  if (seconds % 3600 === 0) {
    const hours = seconds / 3600;
    return `${hours} hour${hours === 1 ? "" : "s"}`;
  }

  return `${seconds.toLocaleString()} seconds`;
}

function getColumnSignals(
  column: ColumnInfo,
  rowCount: number
): string[] {
  const signals: string[] = [];

  const nullCount = column.null_count;
  const distinctCount = column.distinct_count;

  if (nullCount === null || distinctCount === null) {
    return signals;
  }

  const nonNullCount = rowCount - nullCount;

  if (
    nonNullCount > 0 &&
    distinctCount === nonNullCount
  ) {
    signals.push("Unique");
  }

  if (distinctCount === 1) {
    signals.push("Constant");
  }

  if (
    nonNullCount > 0 &&
    distinctCount > 1 &&
    distinctCount <= 20
  ) {
    signals.push("Low cardinality");
  }

  if (nullCount > 0) {
    signals.push("Missing");
  }

  if (
    nonNullCount > 0 &&
    column.distinct_count === nonNullCount
  ) {
    signals.push("Unique");
  }

  if (distinctCount === 1) {
    signals.push("Constant");
  }

  if (
    nonNullCount > 0 &&
    distinctCount > 1 &&
    distinctCount <= 20
  ) {
    signals.push("Low cardinality");
  }

  if (nullCount > 0) {
    signals.push("Missing");
  }

  return signals;
}

function formatWideTemporalScalar(
  value: string | number | boolean | null,
): string {
  if (value === null) {
    return "∅";
  }

  return String(value);
}

function formatWideTemporalSeriesDescriptor(
  series: WideTemporalSeriesSummary,
): string {
  const visibleDescriptors =
    series.descriptors.filter(
      (descriptor) =>
        descriptor.value !== null &&
        String(descriptor.value).trim() !== "",
    );

  if (visibleDescriptors.length === 0) {
    return `Series ${series.series_index}`;
  }

  return visibleDescriptors
    .map(
      (descriptor) =>
        `${descriptor.column_name}=${formatWideTemporalScalar(
          descriptor.value,
        )}`,
    )
    .join(" · ");
}

function buildWideTemporalAxisContext(
  profile: DatasetProfile | null,
): string | null {
  const wideTemporal =
    profile?.wide_temporal;

  if (
    !wideTemporal ||
    wideTemporal.axis_orientation !== "horizontal" ||
    wideTemporal.temporal_column_start_index === null ||
    wideTemporal.temporal_column_end_index === null
  ) {
    return null;
  }

  return JSON.stringify({
    orientation: "horizontal",
    start_index:
      wideTemporal.temporal_column_start_index,
    end_index:
      wideTemporal.temporal_column_end_index,
  });
}

function App() {
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [rawAnalysisResult, setRawAnalysisResult] =
    useState<RawAnalysisColumnResult | null>(null);
  const [rawAnalysisColumnName, setRawAnalysisColumnName] =
    useState("");

  const [showAllDetectedColumns, setShowAllDetectedColumns] = useState(false);

  const [temporalValueColumn, setTemporalValueColumn] =
    useState("");

  const [
    longTemporalSeries,
    setLongTemporalSeries,
  ] = useState<LongTemporalSeriesResult | null>(
    null,
  );

  const [
    isLoadingLongTemporalSeries,
    setIsLoadingLongTemporalSeries,
  ] = useState(false);

  const [
    longTemporalSeriesDetail,
    setLongTemporalSeriesDetail,
  ] = useState<LongTemporalSeriesDetailResult | null>(
    null,
  );

  const [
    isLoadingLongTemporalSeriesDetail,
    setIsLoadingLongTemporalSeriesDetail,
  ] = useState(false);

  const longTemporalDetailRequestIdRef =
    useRef(0);

  const [
    wideTemporalSeriesClassification,
    setWideTemporalSeriesClassification,
  ] = useState("");
  const [wideTemporalSeriesPage, setWideTemporalSeriesPage] =
    useState<WideTemporalSeriesPage | null>(null);
  const [wideTemporalSeriesDetail, setWideTemporalSeriesDetail] =
    useState<WideTemporalSeriesDetail | null>(null);
  const [
    wideTemporalReference,
    setWideTemporalReference,
  ] = useState<WideTemporalReferenceExecution | null>(null);
  const [
    isLoadingWideTemporalReference,
    setIsLoadingWideTemporalReference,
  ] = useState(false);
  const wideTemporalReferencePromiseRef = useRef<
    Promise<WideTemporalReferenceExecution | null> | null
  >(null);
  const wideTemporalReferenceRequestIdRef =
    useRef(0);
  const wideTemporalSourceKeyRef =
    useRef<string | null>(null);
  const [
    wideTemporalReferenceComparison,
    setWideTemporalReferenceComparison,
  ] = useState<WideTemporalReferenceComparisonExecution | null>(null);
  const [
    isLoadingWideTemporalReferenceComparison,
    setIsLoadingWideTemporalReferenceComparison,
  ] = useState(false);
  const wideTemporalComparisonRequestIdRef =
    useRef(0);
  const [
    isLoadingWideTemporalSeries,
    setIsLoadingWideTemporalSeries,
  ] = useState(false);
  const [
    wideTemporalSeriesLoadingIndex,
    setWideTemporalSeriesLoadingIndex,
  ] = useState<number | null>(null);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [progressMessage, setProgressMessage] =
    useState("Preparing analysis");
  const [progressSteps, setProgressSteps] = useState<string[]>([]);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rowInspection, setRowInspection] =
    useState<RowInspection | null>(null);

  const [isInspecting, setIsInspecting] = useState(false);
  const [metadataColumnLinkDrafts, setMetadataColumnLinkDrafts] = useState<
    Record<string, string>
  >({});
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [projects, setProjects] = useState<ProjectListItem[]>([]);
  const [editingColumnName, setEditingColumnName] = useState<string | null>(null);
  const [columnDescriptionDraft, setColumnDescriptionDraft] = useState("");
  const [columnSemanticTypeDraft, setColumnSemanticTypeDraft] = useState("");
  const [columnUnitDraft, setColumnUnitDraft] = useState("");
  const [columnFormatDraft, setColumnFormatDraft] = useState("");
  const [specialValueDraft, setSpecialValueDraft] = useState("");
  const [specialValueMeaningDraft, setSpecialValueMeaningDraft] = useState("");
  const [columnSpecialValuesDraft, setColumnSpecialValuesDraft] = useState<
    {
      value: string;
      meaning: string;
      representsMissing: boolean;
      origin: "user";
    }[]
  >([]);
  const [specialValueRepresentsMissingDraft, setSpecialValueRepresentsMissingDraft] =
    useState(false);
  const [activeProject, setActiveProject] =
    useState<RawsightProject | null>(null);
  const [activeSection, setActiveSection] =
    useState<ProjectSection>("overview");

  wideTemporalSourceKeyRef.current =
    fileInfo?.path ?? null;

  useEffect(() => {
    const unlistenPromise = listen<ProfileProgress>(
      "profile-progress",
      (event) => {
        const message = event.payload.message;

        setProgressMessage(message);

        setProgressSteps((current) => {
          if (current.includes(message)) {
            return current;
          }

          return [...current, message];
        });
      }
    );

    return () => {
      unlistenPromise.then((unlisten) => unlisten());
    };
  }, []);
  useEffect(() => {
    async function loadAppState() {
      try {
        const settings = await invoke<AppSettings>("get_app_settings");
        setAppSettings(settings);

        const projectList =
          await invoke<ProjectListItem[]>("list_projects");

        setProjects(projectList);
      } catch (err) {
        console.error("Could not load RAWSIGHT state:", err);
        setError(`Could not load RAWSIGHT state: ${String(err)}`);
      }
    }

    void loadAppState();
  }, []);

  useEffect(() => {
    longTemporalDetailRequestIdRef.current += 1;
    setLongTemporalSeriesDetail(null);
    setIsLoadingLongTemporalSeriesDetail(false);

    wideTemporalReferenceRequestIdRef.current += 1;
    wideTemporalComparisonRequestIdRef.current += 1;

    setWideTemporalSeriesPage(null);
    setWideTemporalSeriesDetail(null);
    setWideTemporalSeriesClassification("");
    setWideTemporalSeriesLoadingIndex(null);

    setWideTemporalReference(null);
    setIsLoadingWideTemporalReference(false);
    wideTemporalReferencePromiseRef.current = null;

    setWideTemporalReferenceComparison(null);
    setIsLoadingWideTemporalReferenceComparison(false);
  }, [fileInfo?.path]);

  async function exitApplication() {
    await getCurrentWindow().close();
  }

  async function openDataset() {
    const file = await open({
      multiple: false,
      directory: false,
      filters: [
        {
          name: "Data files",
          extensions: ["csv", "xlsx", "xls", "parquet"],
        },
      ],
    });

    if (typeof file !== "string") {
      return;
    }

    setProfile(null);
    setError(null);
    setRowInspection(null);
    setProgressSteps([]);
    setAnalysisComplete(false);
    setProgressMessage("Preparing analysis");

    try {
      const info = await invoke<FileInfo>("get_file_info", {
        path: file,
      });

      setFileInfo(info);
      const inspectedStructure = await inspectDatasetStructure(info.path);
      const now = new Date().toISOString();
      const projectId = crypto.randomUUID();

      const project: RawsightProject = {
        schemaVersion: 1,

        id: projectId,
        name: info.name.replace(/\.[^/.]+$/, ""),

        createdAt: now,
        updatedAt: now,

        datasets: [
          {
            id: crypto.randomUUID(),
            name: info.name,

            kind: "source",

            source: {
              path: info.path,
              name: info.name,
              size: info.size,
            },
            structure: {
              columnCount: inspectedStructure.column_count,
              columns: inspectedStructure.columns.map((column) => ({
                name: column.name,
                technicalType: column.technical_type,
              })),
              inspectedAt: now,
            },
            metadata: {
              sources: [],
              links: [],
              columns: [],
            },

            expectations: [],

            analysis: {
              light: {
                status: "not_run",
              },
              deep: {
                status: "not_run",
              },
            },

            createdAt: now,
            updatedAt: now,
          },
        ],
      };

      project.activeDatasetId = project.datasets[0].id;

      await invoke<string>("save_project_json", {
        projectId: project.id,
        projectJson: JSON.stringify(project, null, 2),
        projectRoot: appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(project);
      setActiveSection("overview");

    } catch (err) {
      setError(String(err));
    } finally {
      setIsAnalyzing(false);
    }
  }
  async function inspectZeroRows(column: ColumnInfo) {
    if (!fileInfo) {
      return;
    }

    setIsInspecting(true);
    setRowInspection(null);

    try {
      const result = await invoke<string>("inspect_rows", {
        path: fileInfo.path,
        column: column.name,
        value: "0",
        limit: 100,
      });

      const parsed = JSON.parse(result) as RowInspection;

      setRowInspection(parsed);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsInspecting(false);
    }
  }
  async function openExistingProject(projectItem: ProjectListItem) {
    setActiveSection("overview");
    try {
      const rawProject = await invoke<string>("load_project", {
        projectPath: projectItem.path,
      });

      const project = JSON.parse(rawProject) as RawsightProject;

      setActiveProject(project);
      setError(null);

      const activeDataset = project.datasets.find(
        (dataset) => dataset.id === project.activeDatasetId,
      );

      if (activeDataset?.source) {
        const extension =
          activeDataset.source.name.split(".").pop()?.toLowerCase() ?? "";

        setFileInfo({
          name: activeDataset.source.name,
          path: activeDataset.source.path,
          extension,
          size: activeDataset.source.size,
        });
      } else {
        setFileInfo(null);
      }

    } catch (err) {
      setError(`Could not open project: ${String(err)}`);
    }
  } async function changeProjectRoot() {
    const selected = await open({
      directory: true,
      multiple: false,
      title: "Choose RAWSIGHT project location",
    });

    if (typeof selected !== "string") {
      return;
    }

    const settings: AppSettings = {
      defaultProjectRoot: selected,
    };

    try {
      await invoke("save_app_settings", {
        settings,
      });

      setAppSettings(settings);
    } catch (err) {
      setError(`Could not save project location: ${String(err)}`);
    }
    const projectList =
      await invoke<ProjectListItem[]>("list_projects");

    setProjects(projectList);
  }
  function goHome() {
    setActiveProject(null);
    setActiveSection("overview");
    setFileInfo(null);
    setProfile(null);
    setRowInspection(null);

    setEditingColumnName(null);
    setColumnDescriptionDraft("");
    setColumnSemanticTypeDraft("");
    setColumnUnitDraft("");
    setColumnFormatDraft("");
    setColumnSpecialValuesDraft([]);
    setSpecialValueDraft("");
    setSpecialValueMeaningDraft("");
    setSpecialValueRepresentsMissingDraft(false);

    setError(null);
  }
  function beginEditColumnDescription(columnName: string) {
    if (!activeProject) {
      return;
    }

    const activeDataset = activeProject.datasets.find(
      (dataset) => dataset.id === activeProject.activeDatasetId,
    );

    const existingMetadata = activeDataset?.metadata.columns.find(
      (column) => column.columnName === columnName,
    );

    setEditingColumnName(columnName);
    setColumnDescriptionDraft(existingMetadata?.description ?? "");
    setColumnSemanticTypeDraft(existingMetadata?.semanticType ?? "");
    setColumnUnitDraft(existingMetadata?.unit ?? "");
    setColumnFormatDraft(existingMetadata?.format ?? "");

    setColumnSpecialValuesDraft(
      existingMetadata?.specialValues.map((specialValue) => ({
        ...specialValue,
        origin: "user" as const,
      })) ?? [],
    );

  }
  function addSpecialValueDraft() {
    const value = specialValueDraft.trim();
    const meaning = specialValueMeaningDraft.trim();

    if (!value || !meaning) {
      return;
    }
    const valueAlreadyExists = columnSpecialValuesDraft.some(
      (specialValue) => specialValue.value === value,
    );

    if (valueAlreadyExists) {
      return;
    }
    setColumnSpecialValuesDraft((currentValues) => [
      ...currentValues,
      {
        value,
        meaning,
        representsMissing: specialValueRepresentsMissingDraft,
        origin: "user" as const,
      },
    ]);

    setSpecialValueDraft("");
    setSpecialValueMeaningDraft("");
    setSpecialValueRepresentsMissingDraft(false);
  }
  async function saveColumnDescription() {
    if (!activeProject || !editingColumnName) {
      return;
    }

    const now = new Date().toISOString();

    const updatedProject: RawsightProject = {
      ...activeProject,
      updatedAt: now,

      datasets: activeProject.datasets.map((dataset) => {
        if (dataset.id !== activeProject.activeDatasetId) {
          return dataset;
        }

        const existingMetadata = dataset.metadata.columns.find(
          (column) => column.columnName === editingColumnName,
        );

        const updatedColumnMetadata = existingMetadata
          ? {
            ...existingMetadata,
            description: columnDescriptionDraft.trim(),
            semanticType: columnSemanticTypeDraft.trim() || undefined,
            unit: columnUnitDraft.trim() || undefined,
            format: columnFormatDraft.trim() || undefined,
            specialValues: columnSpecialValuesDraft,
          }
          : {
            columnName: editingColumnName,
            description: columnDescriptionDraft.trim(),
            semanticType: columnSemanticTypeDraft.trim() || undefined,
            unit: columnUnitDraft.trim() || undefined,
            format: columnFormatDraft.trim() || undefined,
            specialValues: columnSpecialValuesDraft,
            origin: "user" as const,
          };

        return {
          ...dataset,
          updatedAt: now,

          metadata: {
            ...dataset.metadata,

            columns: existingMetadata
              ? dataset.metadata.columns.map((column) =>
                column.columnName === editingColumnName
                  ? updatedColumnMetadata
                  : column,
              )
              : [
                ...dataset.metadata.columns,
                updatedColumnMetadata,
              ],
          },
        };
      }),
    };

    try {
      await invoke<string>("save_project_json", {
        projectId: updatedProject.id,
        projectJson: JSON.stringify(updatedProject, null, 2),
        projectRoot: appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(updatedProject);
      setEditingColumnName(null);
      setColumnDescriptionDraft("");
      setColumnSemanticTypeDraft("");
      setColumnUnitDraft("");
      setColumnFormatDraft("");
      setError(null);
    } catch (err) {
      setError(`Could not save column description: ${String(err)}`);
    }
  }
  async function toggleAnalysisScopeColumn(
    columnName: string,
  ) {
    if (!activeProject) {
      return;
    }

    const now = new Date().toISOString();

    const updatedProject: RawsightProject = {
      ...activeProject,
      updatedAt: now,

      datasets: activeProject.datasets.map((dataset) => {
        if (dataset.id !== activeProject.activeDatasetId) {
          return dataset;
        }

        const existingScopeColumn =
          dataset.analysisScope?.columns.find(
            (column) => column.columnName === columnName,
          );

        const currentlyIncluded =
          existingScopeColumn?.included ?? true;

        const updatedScopeColumn = existingScopeColumn
          ? {
            ...existingScopeColumn,
            included: !currentlyIncluded,
            origin: "user" as const,
            decisionStatus: "confirmed" as const,
          }
          : {
            columnName,
            included: false,
            origin: "user" as const,
            decisionStatus: "confirmed" as const,
          };

        const existingScopeColumns =
          dataset.analysisScope?.columns ?? [];

        return {
          ...dataset,
          updatedAt: now,

          analysisScope: {
            columns: existingScopeColumn
              ? existingScopeColumns.map((column) =>
                column.columnName === columnName
                  ? updatedScopeColumn
                  : column,
              )
              : [
                ...existingScopeColumns,
                updatedScopeColumn,
              ],

            updatedAt: now,
          },
        };
      }),
    };

    try {
      await invoke<string>("save_project_json", {
        projectId: updatedProject.id,
        projectJson: JSON.stringify(
          updatedProject,
          null,
          2,
        ),
        projectRoot:
          appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(updatedProject);
      setError(null);
    } catch (err) {
      setError(
        `Could not update The Lineup: ${String(err)}`,
      );
    }
  }
  async function setAnalysisScopeColumnRole(
    columnName: string,
    role: AnalysisColumnRole,
  ) {
    if (!activeProject) {
      return;
    }

    const now = new Date().toISOString();

    const updatedProject: RawsightProject = {
      ...activeProject,
      updatedAt: now,

      datasets: activeProject.datasets.map((dataset) => {
        if (dataset.id !== activeProject.activeDatasetId) {
          return dataset;
        }

        const existingScopeColumn =
          dataset.analysisScope?.columns.find(
            (column) => column.columnName === columnName,
          );

        const updatedScopeColumn = existingScopeColumn
          ? {
            ...existingScopeColumn,
            role,
            origin: "user" as const,
            decisionStatus: "confirmed" as const,
          }
          : {
            columnName,
            included: true,
            role,
            origin: "user" as const,
            decisionStatus: "confirmed" as const,
          };

        const existingScopeColumns =
          dataset.analysisScope?.columns ?? [];

        return {
          ...dataset,
          updatedAt: now,

          analysisScope: {
            columns: existingScopeColumn
              ? existingScopeColumns.map((column) =>
                column.columnName === columnName
                  ? updatedScopeColumn
                  : column,
              )
              : [
                ...existingScopeColumns,
                updatedScopeColumn,
              ],

            updatedAt: now,
          },
        };
      }),
    };

    try {
      await invoke<string>("save_project_json", {
        projectId: updatedProject.id,
        projectJson: JSON.stringify(
          updatedProject,
          null,
          2,
        ),
        projectRoot:
          appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(updatedProject);
      setError(null);
    } catch (err) {
      setError(
        `Could not update column role: ${String(err)}`,
      );
    }
  }
  async function runLightAnalysis() {
    if (!fileInfo) {
      return;
    }

    setProfile(null);
    setError(null);
    setRowInspection(null);
    setProgressSteps([]);
    setAnalysisComplete(false);
    setProgressMessage("Preparing analysis");
    setIsAnalyzing(true);

    try {
      const rawProfile = await invoke<string>(
        "profile_dataset",
        {
          path: fileInfo.path,
        },
      );

      const parsedProfile =
        JSON.parse(rawProfile) as DatasetProfile;

      setProfile(parsedProfile);
      setAnalysisComplete(true);

    } catch (err) {
      setError(String(err));
    } finally {
      setIsAnalyzing(false);
    }
  }
  async function loadWideTemporalReference(
  ): Promise<WideTemporalReferenceExecution | null> {
    if (wideTemporalReference) {
      return wideTemporalReference;
    }

    if (wideTemporalReferencePromiseRef.current) {
      return wideTemporalReferencePromiseRef.current;
    }

    if (!fileInfo) {
      return null;
    }

    const sourcePath =
      fileInfo.path;

    const temporalAxisJson =
      buildWideTemporalAxisContext(profile);

    if (!temporalAxisJson) {
      setError(
        "Reference profiling requires the horizontal temporal axis established by Light Analysis.",
      );
      return null;
    }

    const requestId =
      ++wideTemporalReferenceRequestIdRef.current;

    setIsLoadingWideTemporalReference(true);

    const request = (async () => {
      try {
        const rawResult = await invoke<string>(
          "explore_wide_temporal_reference",
          {
            path: sourcePath,
            temporalAxisJson,
          },
        );

        const parsedResult = JSON.parse(
          rawResult,
        ) as WideTemporalReferenceExecution;

        if (
          requestId !==
          wideTemporalReferenceRequestIdRef.current ||
          wideTemporalSourceKeyRef.current !==
          sourcePath
        ) {
          return null;
        }

        setWideTemporalReference(
          parsedResult,
        );

        return parsedResult;
      } catch (err) {
        if (
          requestId ===
          wideTemporalReferenceRequestIdRef.current &&
          wideTemporalSourceKeyRef.current ===
          sourcePath
        ) {
          setError(String(err));
        }

        return null;
      } finally {
        if (
          requestId ===
          wideTemporalReferenceRequestIdRef.current
        ) {
          setIsLoadingWideTemporalReference(
            false,
          );
          wideTemporalReferencePromiseRef.current =
            null;
        }
      }
    })();

    wideTemporalReferencePromiseRef.current =
      request;

    return request;
  }

  async function loadWideTemporalSeriesPage(
    offset: number,
  ): Promise<WideTemporalSeriesPage | null> {
    if (!fileInfo) {
      return null;
    }

    const temporalAxisJson =
      buildWideTemporalAxisContext(profile);

    if (!temporalAxisJson) {
      setError(
        "Series Explorer requires the horizontal temporal axis established by Light Analysis.",
      );
      return null;
    }

    setIsLoadingWideTemporalSeries(true);
    setWideTemporalSeriesLoadingIndex(null);
    setError(null);

    try {
      const rawResult = await invoke<string>(
        "explore_wide_temporal_series_page",
        {
          path: fileInfo.path,
          temporalAxisJson,
          classification:
            wideTemporalSeriesClassification || null,
          offset,
          limit: WIDE_TEMPORAL_SERIES_PAGE_SIZE,
        },
      );

      const parsedResult = JSON.parse(
        rawResult,
      ) as WideTemporalSeriesPage;

      setWideTemporalSeriesPage(parsedResult);
      setWideTemporalSeriesDetail(null);
      setWideTemporalReferenceComparison(null);
      wideTemporalComparisonRequestIdRef.current += 1;

      void loadWideTemporalReference();

      return parsedResult;
    } catch (err) {
      setError(String(err));
      return null;
    } finally {
      setIsLoadingWideTemporalSeries(false);
    }
  }

  async function loadWideTemporalSeriesDetail(
    seriesIndex: number,
  ): Promise<WideTemporalSeriesDetail | null> {
    if (!fileInfo) {
      return null;
    }

    const sourcePath =
      fileInfo.path;

    const temporalAxisJson =
      buildWideTemporalAxisContext(profile);

    if (!temporalAxisJson) {
      setError(
        "Series Explorer requires the horizontal temporal axis established by Light Analysis.",
      );
      return null;
    }

    if (
      wideTemporalSeriesDetail?.series_index ===
      seriesIndex
    ) {
      wideTemporalComparisonRequestIdRef.current += 1;
      setWideTemporalSeriesDetail(null);
      setWideTemporalReferenceComparison(null);
      setIsLoadingWideTemporalReferenceComparison(false);
      setWideTemporalSeriesLoadingIndex(null);
      return null;
    }

    const requestId =
      ++wideTemporalComparisonRequestIdRef.current;

    setWideTemporalSeriesDetail(null);
    setWideTemporalReferenceComparison(null);

    setWideTemporalSeriesLoadingIndex(
      seriesIndex,
    );
    setIsLoadingWideTemporalSeries(true);
    setIsLoadingWideTemporalReferenceComparison(true);
    setError(null);

    let parsedDetail:
      WideTemporalSeriesDetail | null =
      null;

    try {
      const rawDetail = await invoke<string>(
        "explore_wide_temporal_series_detail",
        {
          path: sourcePath,
          temporalAxisJson,
          seriesIndex,
        },
      );

      parsedDetail = JSON.parse(
        rawDetail,
      ) as WideTemporalSeriesDetail;

      if (
        requestId !==
        wideTemporalComparisonRequestIdRef.current ||
        wideTemporalSourceKeyRef.current !==
        sourcePath
      ) {
        return null;
      }

      setWideTemporalSeriesDetail(
        parsedDetail,
      );
      setWideTemporalSeriesLoadingIndex(
        null,
      );
      setIsLoadingWideTemporalSeries(false);

      const rawComparison =
        await invoke<string>(
          "explore_wide_temporal_reference_comparison",
          {
            path: sourcePath,
            temporalAxisJson,
            seriesIndex,
          },
        );

      const parsedComparison =
        JSON.parse(
          rawComparison,
        ) as WideTemporalReferenceComparisonExecution;

      if (
        requestId !==
        wideTemporalComparisonRequestIdRef.current ||
        wideTemporalSourceKeyRef.current !==
        sourcePath
      ) {
        return null;
      }

      if (
        parsedComparison.series_index !==
        seriesIndex
      ) {
        throw new Error(
          "Reference comparison returned a different series index than requested.",
        );
      }

      setWideTemporalReferenceComparison(
        parsedComparison,
      );

      return parsedDetail;
    } catch (err) {
      if (
        requestId ===
        wideTemporalComparisonRequestIdRef.current &&
        wideTemporalSourceKeyRef.current ===
        sourcePath
      ) {
        setError(String(err));
      }

      return parsedDetail;
    } finally {
      if (
        requestId ===
        wideTemporalComparisonRequestIdRef.current
      ) {
        setWideTemporalSeriesLoadingIndex(
          null,
        );
        setIsLoadingWideTemporalSeries(false);
        setIsLoadingWideTemporalReferenceComparison(
          false,
        );
      }
    }
  }

  async function runRawAnalysisColumn(
    column: string,
    role?: AnalysisColumnRole,
  ) {
    if (!fileInfo || !activeProject) {
      return null;
    }

    const activeDataset = activeProject.datasets.find(
      (dataset) =>
        dataset.id === activeProject.activeDatasetId,
    );

    const columnMetadata =
      activeDataset?.metadata.columns.find(
        (metadata) =>
          metadata.columnName === column,
      );

    const excludedValues =
      columnMetadata?.specialValues.map(
        (specialValue) => specialValue.value,
      ) ?? [];

    const rawResult = await invoke<string>(
      "raw_analysis_dataset",
      {
        path: fileInfo.path,
        column,
        role: role ?? null,
        semanticType:
          columnMetadata?.semanticType ?? null,
        formatHint:
          columnMetadata?.format ?? null,
        excludedValues,
      },
    );

    const parsedResult = JSON.parse(
      rawResult,
    ) as RawAnalysisColumnResult;

    setRawAnalysisResult(parsedResult);

    return parsedResult;
  }

  async function loadLongTemporalSeries(
    valueColumnName: string,
  ): Promise<LongTemporalSeriesResult | null> {
    if (!fileInfo) {
      return null;
    }

    const temporalAxis =
      profile?.structural_model
        ?.logical_structure
        ?.temporal_axis;

    if (
      !temporalAxis ||
      temporalAxis.orientation !== "vertical"
    ) {
      setError(
        "Time / Value Explorer requires the vertical temporal axis established by Light Analysis.",
      );

      return null;
    }

    const temporalAxisJson =
      JSON.stringify(temporalAxis);

    setIsLoadingLongTemporalSeries(true);
    setError(null);

    try {
      const rawResult =
        await invoke<string>(
          "explore_long_temporal_series",
          {
            path: fileInfo.path,
            temporalAxisJson,
            valueColumnName,
            pointLimit: 1000,
          },
        );

      const parsedResult =
        JSON.parse(
          rawResult,
        ) as LongTemporalSeriesResult;

      longTemporalDetailRequestIdRef.current += 1;
      setLongTemporalSeriesDetail(null);
      setIsLoadingLongTemporalSeriesDetail(false);

      /*
       * Replace the displayed series only
       * after the new series has loaded
       * successfully.
       */
      setLongTemporalSeries(
        parsedResult,
      );

      return parsedResult;
    } catch (err) {
      /*
       * Preserve the currently displayed
       * series if loading the replacement
       * fails.
       */
      setError(String(err));

      return null;
    } finally {
      setIsLoadingLongTemporalSeries(
        false,
      );
    }
  }
  async function loadLongTemporalSeriesDetail(
    valueColumnName: string,
    startTime: string,
    endTime: string,
  ): Promise<LongTemporalSeriesDetailResult | null> {
    if (!fileInfo || !longTemporalSeries) {
      return null;
    }

    if (
      longTemporalSeries.value_column_name !==
      valueColumnName
    ) {
      setError(
        "Temporal detail must belong to the currently displayed value field.",
      );
      return null;
    }

    if (!startTime || !endTime) {
      setError(
        "Temporal detail requires a start and end time.",
      );
      return null;
    }

    if (
      longTemporalSeriesDetail &&
      longTemporalSeriesDetail.value_column_name ===
      valueColumnName &&
      longTemporalSeriesDetail.requested_range.start ===
      startTime &&
      longTemporalSeriesDetail.requested_range.end ===
      endTime
    ) {
      return longTemporalSeriesDetail;
    }

    const temporalAxis =
      profile?.structural_model
        ?.logical_structure
        ?.temporal_axis;

    if (
      !temporalAxis ||
      temporalAxis.orientation !== "vertical"
    ) {
      setError(
        "Temporal detail requires the vertical temporal axis established by Light Analysis.",
      );
      return null;
    }

    const sourcePath =
      fileInfo.path;

    const temporalAxisJson =
      JSON.stringify(temporalAxis);

    const requestId =
      ++longTemporalDetailRequestIdRef.current;

    setIsLoadingLongTemporalSeriesDetail(true);
    setError(null);

    try {
      const rawResult = await invoke<string>(
        "explore_long_temporal_series_detail",
        {
          path: sourcePath,
          temporalAxisJson,
          valueColumnName,
          startTime,
          endTime,
          pointLimit: 1000,
        },
      );

      const parsedResult = JSON.parse(
        rawResult,
      ) as LongTemporalSeriesDetailResult;

      if (
        requestId !==
        longTemporalDetailRequestIdRef.current
      ) {
        return null;
      }

      if (
        parsedResult.value_column_name !==
        valueColumnName
      ) {
        throw new Error(
          "Temporal detail returned a different value field than requested.",
        );
      }

      setLongTemporalSeriesDetail(
        parsedResult,
      );

      return parsedResult;
    } catch (err) {
      if (
        requestId ===
        longTemporalDetailRequestIdRef.current
      ) {
        setError(String(err));
      }

      return null;
    } finally {
      if (
        requestId ===
        longTemporalDetailRequestIdRef.current
      ) {
        setIsLoadingLongTemporalSeriesDetail(
          false,
        );
      }
    }
  }
  async function inspectDatasetStructure(path: string) {
    const rawStructure = await invoke<string>("inspect_structure", {
      path,
    });

    const structure = JSON.parse(
      rawStructure,
    ) as StructureInspectionResult;

    return structure;
  }
  async function linkMetadataSourceToDataset(metadataSourceId: string) {
    if (!activeProject) {
      return;
    }

    const activeDataset = activeProject.datasets.find(
      (dataset) => dataset.id === activeProject.activeDatasetId,
    );

    if (!activeDataset) {
      return;
    }

    const linkAlreadyExists = activeDataset.metadata.links.some(
      (link) =>
        link.metadataSourceId === metadataSourceId &&
        link.targetType === "dataset" &&
        link.status === "linked",
    );

    if (linkAlreadyExists) {
      return;
    }

    const now = new Date().toISOString();

    const metadataLink = {
      id: crypto.randomUUID(),
      metadataSourceId,
      targetType: "dataset" as const,
      status: "linked" as const,
      origin: "user" as const,
    };

    const updatedProject: RawsightProject = {
      ...activeProject,
      updatedAt: now,

      datasets: activeProject.datasets.map((dataset) =>
        dataset.id === activeProject.activeDatasetId
          ? {
            ...dataset,
            updatedAt: now,
            metadata: {
              ...dataset.metadata,
              links: [
                ...dataset.metadata.links,
                metadataLink,
              ],
            },
          }
          : dataset,
      ),
    };

    try {
      await invoke<string>("save_project_json", {
        projectId: updatedProject.id,
        projectJson: JSON.stringify(updatedProject, null, 2),
        projectRoot: appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(updatedProject);
      setError(null);
    } catch (err) {
      setError(`Could not link metadata source: ${String(err)}`);
    }
  }

  async function linkMetadataSourceToColumn(
    metadataSourceId: string,
    columnName: string,
  ) {
    if (!activeProject) {
      return;
    }

    const activeDataset = activeProject.datasets.find(
      (dataset) => dataset.id === activeProject.activeDatasetId,
    );

    if (!activeDataset) {
      return;
    }

    const linkAlreadyExists = activeDataset.metadata.links.some(
      (link) =>
        link.metadataSourceId === metadataSourceId &&
        link.targetType === "column" &&
        link.columnName === columnName &&
        link.status === "linked",
    );

    if (linkAlreadyExists) {
      return;
    }

    const now = new Date().toISOString();

    const metadataLink = {
      id: crypto.randomUUID(),
      metadataSourceId,
      targetType: "column" as const,
      columnName,
      status: "linked" as const,
      origin: "user" as const,
    };

    const updatedProject: RawsightProject = {
      ...activeProject,
      updatedAt: now,

      datasets: activeProject.datasets.map((dataset) =>
        dataset.id === activeProject.activeDatasetId
          ? {
            ...dataset,
            updatedAt: now,
            metadata: {
              ...dataset.metadata,
              links: [
                ...dataset.metadata.links,
                metadataLink,
              ],
            },
          }
          : dataset,
      ),
    };

    try {
      await invoke<string>("save_project_json", {
        projectId: updatedProject.id,
        projectJson: JSON.stringify(updatedProject, null, 2),
        projectRoot: appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(updatedProject);

      setMetadataColumnLinkDrafts((current) => ({
        ...current,
        [metadataSourceId]: "",
      }));

      setError(null);
    } catch (err) {
      setError(`Could not link metadata source to column: ${String(err)}`);
    }
  }

  async function addMetadataFile() {
    if (!activeProject) {
      return;
    }

    const selected = await open({
      multiple: false,
      directory: false,
      title: "Add metadata file",
      filters: [
        {
          name: "Metadata files",
          extensions: ["pdf", "txt", "csv", "xlsx", "xls", "json", "xml"],
        },
      ],
    });

    if (typeof selected !== "string") {
      return;
    }

    const fileName =
      selected.split(/[\\/]/).pop() ?? "Metadata file";

    const metadataSource = {
      id: crypto.randomUUID(),
      type: "file" as const,
      name: fileName,
      path: selected,
      scope: "mixed" as const,
      addedAt: new Date().toISOString(),
    };

    const updatedProject: RawsightProject = {
      ...activeProject,
      updatedAt: new Date().toISOString(),
      datasets: activeProject.datasets.map((dataset) =>
        dataset.id === activeProject.activeDatasetId
          ? {
            ...dataset,
            updatedAt: new Date().toISOString(),
            metadata: {
              ...dataset.metadata,
              sources: [
                ...dataset.metadata.sources,
                metadataSource,
              ],
            },
          }
          : dataset,
      ),
    };

    try {
      await invoke<string>("save_project_json", {
        projectId: updatedProject.id,
        projectJson: JSON.stringify(updatedProject, null, 2),
        projectRoot: appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(updatedProject);
      setError(null);
    } catch (err) {
      setError(`Could not add metadata file: ${String(err)}`);
    }
  }
  return (
    <main className="app-shell">
      <section
        className={
          activeProject
            ? "project-page"
            : "hero"
        }
      >
        <div className="app-header">
          <div className="brand">RAWSIGHT</div>

          <button
            type="button"
            className="power-button"
            onClick={exitApplication}
            title="Exit RAWSIGHT"
            aria-label="Exit RAWSIGHT"
          >
            ⏻
          </button>
        </div>

        {activeProject ? (
          <div className="project-shell">
            <aside className="project-sidebar">
              <div className="project-sidebar-brand">RAWSIGHT</div>

              <button
                type="button"
                className="sidebar-home-button"
                onClick={goHome}
              >
                ← Home
              </button>

              <div className="sidebar-project-name">
                {activeProject.name}
              </div>

              <nav className="project-navigation">
                <button
                  type="button"
                  onClick={() => setActiveSection("overview")}
                  className={activeSection === "overview" ? "active" : ""}
                >
                  Overview
                </button>

                <button
                  type="button"
                  onClick={() => setActiveSection("data")}
                  className={activeSection === "data" ? "active" : ""}
                >
                  Data
                </button>

                <button
                  type="button"
                  onClick={() => setActiveSection("metadata")}
                  className={activeSection === "metadata" ? "active" : ""}
                >
                  Metadata
                </button>

                <button
                  type="button"
                  onClick={() => setActiveSection("lineup")}
                  className={activeSection === "lineup" ? "active" : ""}
                >
                  The Lineup
                </button>

                <button
                  type="button"
                  onClick={() => setActiveSection("analysis")}
                  className={activeSection === "analysis" ? "active" : ""}
                >
                  Light Analysis
                </button>

                <button
                  type="button"
                  onClick={() => setActiveSection("raw_analysis")}
                  className={activeSection === "raw_analysis" ? "active" : ""}
                >
                  Explore
                </button>

                <button
                  type="button"
                  onClick={() => setActiveSection("history")}
                  className={activeSection === "history" ? "active" : ""}
                >
                  History
                </button>
              </nav>
            </aside>

            <main className="project-main">
              <div className="project-workspace-header">
                <div className="workspace-section-label">
                  {activeSection === "overview" && "Overview"}
                  {activeSection === "data" && "Data"}
                  {activeSection === "lineup" && "The Lineup"}
                  {activeSection === "metadata" && "Metadata"}
                  {activeSection === "analysis" && "Light Analysis"}
                  {activeSection === "raw_analysis" && "Explore"}
                  {activeSection === "history" && "History"}
                </div>

                <h1>{activeProject.name}</h1>
              </div>

              <div className="project-workspace-content">
                {activeSection === "analysis" && (
                  <div className="light-analysis-start">
                    <div>
                      <strong>Light Analysis</strong>
                      <p>
                        Inspect structure and apply safe analysis appropriate to the detected data shape.
                        No changes will be made to your source data.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={runLightAnalysis}
                      disabled={isAnalyzing || !fileInfo}
                    >
                      {isAnalyzing
                        ? "Analyzing..."
                        : analysisComplete
                          ? "Run Light Analysis again"
                          : "Run Light Analysis"}
                    </button>
                  </div>
                )}
                {activeSection === "raw_analysis" && (
                  <div className="metadata-workspace">
                    <div className="metadata-header">
                      <div>
                        <strong>Explore</strong>
                        <p>
                          Explore the dataset using the structure detected by Light Analysis.
                        </p>
                      </div>
                    </div>

                    {!profile ? (
                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Structure required</strong>
                          <span>Not detected</span>
                        </div>

                        <div className="analysis-group-content">
                          <span>
                            Run Light Analysis first. Explore uses the detected
                            structure and analysis strategy rather than assuming
                            that every dataset is column-oriented.
                          </span>
                        </div>
                      </div>
                    ) : (
                      (() => {
                        const activeDataset = activeProject.datasets.find(
                          (dataset) =>
                            dataset.id === activeProject.activeDatasetId,
                        );

                        const columns =
                          activeDataset?.structure?.columns ?? [];

                        const scopeColumns =
                          activeDataset?.analysisScope?.columns ?? [];

                        const strategy =
                          profile.analysis_strategy?.strategy ??
                          "conservative_unknown";

                        const logicalStructure =
                          profile.structural_model?.logical_structure;

                        const orientation =
                          logicalStructure?.temporal_axis_orientation
                            ?.orientation ?? "none";

                        const horizontalCandidateCount =
                          logicalStructure?.temporal_axis_orientation
                            ?.horizontal_candidate_count ?? 0;

                        const verticalCandidateCount =
                          logicalStructure?.temporal_axis_orientation
                            ?.vertical_candidate_count ?? 0;

                        const detectedTemporalAxis =
                          logicalStructure?.temporal_axis;

                        const detectedTemporalColumnName =
                          detectedTemporalAxis?.orientation === "vertical" &&
                            Number.isInteger(
                              detectedTemporalAxis.sequence_index,
                            )
                            ? columns[
                              detectedTemporalAxis.sequence_index
                            ]?.name ?? ""
                            : "";
                        const selectedScopeColumn =
                          scopeColumns.find(
                            (column) =>
                              column.columnName ===
                              rawAnalysisColumnName,
                          );
                        return (
                          <>
                            <div className="analysis-group">
                              <div className="analysis-group-header">
                                <strong>Detected structure</strong>
                                <span>{strategy}</span>
                              </div>

                              <div className="analysis-group-content">
                                <span>
                                  Temporal orientation{" "}
                                  <strong>{orientation}</strong>
                                </span>

                                <span>
                                  Horizontal candidates{" "}
                                  <strong>
                                    {horizontalCandidateCount.toLocaleString()}
                                  </strong>
                                </span>

                                <span>
                                  Vertical candidates{" "}
                                  <strong>
                                    {verticalCandidateCount.toLocaleString()}
                                  </strong>
                                </span>
                              </div>
                            </div>

                            {strategy === "wide_temporal" && (
                              <>
                                <div className="analysis-group">
                                  <div className="analysis-group-header">
                                    <strong>Series Explorer</strong>
                                    <span>Horizontal temporal axis</span>
                                  </div>

                                  <div className="analysis-group-content">
                                    <span>
                                      RAWSIGHT detected a horizontal temporal
                                      structure. The time axis is already known,
                                      so no time-column selection is required.
                                    </span>

                                    {profile.wide_temporal?.value_analysis && (
                                      <>
                                        <span>
                                          Series{" "}
                                          <strong>
                                            {profile.wide_temporal.value_analysis.series_count.toLocaleString()}
                                          </strong>
                                        </span>

                                        <span>
                                          Mixed series{" "}
                                          <strong>
                                            {profile.wide_temporal.value_analysis.series_classification.mixed.toLocaleString()}
                                          </strong>
                                        </span>

                                        <span>
                                          Series with negative transitions{" "}
                                          <strong>
                                            {profile.wide_temporal.value_analysis.series_with_negative_transitions.toLocaleString()}
                                          </strong>
                                        </span>

                                        <span>
                                          Constant series{" "}
                                          <strong>
                                            {profile.wide_temporal.value_analysis.series_classification.constant.toLocaleString()}
                                          </strong>
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>

                                <div className="analysis-group">
                                  <div className="analysis-group-header">
                                    <strong>Browse series</strong>
                                    <span>
                                      Page size{" "}
                                      {WIDE_TEMPORAL_SERIES_PAGE_SIZE}
                                    </span>
                                  </div>

                                  <div
                                    className="analysis-group-content"
                                    style={{ gap: "12px" }}
                                  >
                                    <div
                                      style={{
                                        display: "flex",
                                        flexWrap: "wrap",
                                        gap: "8px",
                                        alignItems: "center",
                                      }}
                                    >
                                      <select
                                        value={
                                          wideTemporalSeriesClassification
                                        }
                                        onChange={(event) => {
                                          setWideTemporalSeriesClassification(
                                            event.target.value,
                                          );
                                          setWideTemporalSeriesPage(null);
                                          setWideTemporalSeriesDetail(null);
                                        }}
                                      >
                                        <option value="">
                                          All observed series
                                        </option>
                                        <option value="mixed">
                                          Mixed
                                        </option>
                                        <option value="non_decreasing">
                                          Non-decreasing
                                        </option>
                                        <option value="non_increasing">
                                          Non-increasing
                                        </option>
                                        <option value="constant">
                                          Constant
                                        </option>
                                        <option value="insufficient_adjacent_observations">
                                          Insufficient adjacent observations
                                        </option>
                                        <option value="no_numeric_data">
                                          No numeric data
                                        </option>
                                      </select>

                                      <button
                                        type="button"
                                        disabled={
                                          isLoadingWideTemporalSeries
                                        }
                                        onClick={() => {
                                          void loadWideTemporalSeriesPage(0);
                                        }}
                                      >
                                        {isLoadingWideTemporalSeries
                                          ? "Loading..."
                                          : "Load series"}
                                      </button>
                                    </div>

                                    {wideTemporalSeriesPage && (
                                      <>
                                        <span>
                                          Showing{" "}
                                          <strong>
                                            {wideTemporalSeriesPage.returned_count.toLocaleString()}
                                          </strong>{" "}
                                          matching series from offset{" "}
                                          <strong>
                                            {wideTemporalSeriesPage.offset.toLocaleString()}
                                          </strong>
                                        </span>

                                        <span>
                                          Source rows scanned{" "}
                                          <strong>
                                            {wideTemporalSeriesPage.rows_scanned.toLocaleString()}
                                          </strong>
                                        </span>

                                        {wideTemporalSeriesPage.series.length ===
                                          0 ? (
                                          <span>
                                            No series matched this observation
                                            classification.
                                          </span>
                                        ) : (
                                          <div
                                            style={{
                                              display: "grid",
                                              gap: "8px",
                                            }}
                                          >
                                            {wideTemporalSeriesPage.series.map(
                                              (series) => {
                                                const isSelected =
                                                  wideTemporalSeriesDetail?.series_index ===
                                                  series.series_index;

                                                const isLoadingThisSeries =
                                                  wideTemporalSeriesLoadingIndex ===
                                                  series.series_index;

                                                return (
                                                  <div
                                                    key={
                                                      series.series_index
                                                    }
                                                    style={{
                                                      display: "grid",
                                                      gap: "8px",
                                                    }}
                                                  >
                                                    <button
                                                      type="button"
                                                      disabled={
                                                        isLoadingWideTemporalSeries &&
                                                        !isLoadingThisSeries
                                                      }
                                                      onClick={() => {
                                                        void loadWideTemporalSeriesDetail(
                                                          series.series_index,
                                                        );
                                                      }}
                                                      aria-expanded={
                                                        isSelected
                                                      }
                                                      style={{
                                                        textAlign: "left",
                                                        display: "grid",
                                                        gap: "4px",
                                                        outline: isSelected
                                                          ? "2px solid currentColor"
                                                          : undefined,
                                                        outlineOffset: isSelected
                                                          ? "2px"
                                                          : undefined,
                                                      }}
                                                    >
                                                      <strong>
                                                        Series{" "}
                                                        {series.series_index}
                                                      </strong>

                                                      <span>
                                                        {formatWideTemporalSeriesDescriptor(
                                                          series,
                                                        )}
                                                      </span>

                                                      <span>
                                                        {
                                                          series.classification
                                                        }
                                                        {" · "}
                                                        negative transitions{" "}
                                                        {
                                                          series.negative_transition_count
                                                        }
                                                        {" · "}
                                                        largest negative change{" "}
                                                        {series.largest_negative_change ??
                                                          "—"}
                                                      </span>

                                                      {isLoadingThisSeries && (
                                                        <span>
                                                          Loading details...
                                                        </span>
                                                      )}
                                                    </button>

                                                    {isSelected &&
                                                      wideTemporalSeriesDetail && (
                                                        <WideTemporalSeriesDetailPanel
                                                          detail={
                                                            wideTemporalSeriesDetail
                                                          }
                                                          reference={
                                                            wideTemporalReference?.reference_profile ??
                                                            null
                                                          }
                                                          isReferenceLoading={
                                                            isLoadingWideTemporalReference
                                                          }
                                                          comparison={
                                                            wideTemporalReferenceComparison
                                                          }
                                                          isComparisonLoading={
                                                            isLoadingWideTemporalReferenceComparison
                                                          }
                                                          onClose={() => {
                                                            wideTemporalComparisonRequestIdRef.current += 1;
                                                            setWideTemporalSeriesDetail(
                                                              null,
                                                            );
                                                            setWideTemporalReferenceComparison(
                                                              null,
                                                            );
                                                            setIsLoadingWideTemporalReferenceComparison(
                                                              false,
                                                            );
                                                          }}
                                                        />
                                                      )}
                                                  </div>
                                                );
                                              },
                                            )}
                                          </div>
                                        )}

                                        <div
                                          style={{
                                            display: "flex",
                                            gap: "8px",
                                          }}
                                        >
                                          <button
                                            type="button"
                                            disabled={
                                              isLoadingWideTemporalSeries ||
                                              wideTemporalSeriesPage.offset ===
                                              0
                                            }
                                            onClick={() => {
                                              void loadWideTemporalSeriesPage(
                                                Math.max(
                                                  0,
                                                  wideTemporalSeriesPage.offset -
                                                  wideTemporalSeriesPage.limit,
                                                ),
                                              );
                                            }}
                                          >
                                            Previous
                                          </button>

                                          <button
                                            type="button"
                                            disabled={
                                              isLoadingWideTemporalSeries ||
                                              !wideTemporalSeriesPage.has_more ||
                                              wideTemporalSeriesPage.next_offset ===
                                              null
                                            }
                                            onClick={() => {
                                              if (
                                                wideTemporalSeriesPage.next_offset !==
                                                null
                                              ) {
                                                void loadWideTemporalSeriesPage(
                                                  wideTemporalSeriesPage.next_offset,
                                                );
                                              }
                                            }}
                                          >
                                            Next
                                          </button>
                                        </div>
                                      </>
                                    )}
                                  </div>
                                </div>

                              </>
                            )}

                            {strategy === "long_temporal" &&
                              profile.long_temporal?.continuity && (
                                <div className="analysis-group">
                                  <div className="analysis-group-header">
                                    <strong>Temporal continuity</strong>
                                    <span>Observed sequence</span>
                                  </div>

                                  <div className="analysis-group-content">
                                    <span>
                                      Time field{" "}
                                      <strong>
                                        {profile.long_temporal.temporal_column_name ??
                                          "Unknown"}
                                      </strong>
                                    </span>

                                    <span>
                                      Observed order{" "}
                                      <strong>
                                        {profile.long_temporal.continuity.observed_order ??
                                          "Not established"}
                                      </strong>
                                    </span>

                                    <span>
                                      Dominant positive interval{" "}
                                      <strong>
                                        {profile.long_temporal.continuity
                                          .dominant_positive_interval_seconds !== null
                                          ? `${profile.long_temporal.continuity
                                            .dominant_positive_interval_seconds.toLocaleString()} s`
                                          : "Not established"}
                                      </strong>
                                    </span>

                                    <span>
                                      Share at dominant interval{" "}
                                      <strong>
                                        {profile.long_temporal.continuity
                                          .positive_interval_consistency !== null
                                          ? `${(
                                            profile.long_temporal.continuity
                                              .positive_interval_consistency * 100
                                          ).toFixed(1)}%`
                                          : "Not evaluated"}
                                      </strong>
                                    </span>

                                    <span>
                                      Distinct positive intervals{" "}
                                      <strong>
                                        {profile.long_temporal.continuity
                                          .distinct_positive_interval_count !== null
                                          ? profile.long_temporal.continuity
                                            .distinct_positive_interval_count.toLocaleString()
                                          : "Not fully retained"}
                                      </strong>
                                    </span>

                                    <span>
                                      Interval frequency analysis{" "}
                                      <strong>
                                        {profile.long_temporal.continuity
                                          .interval_frequency_complete
                                          ? "Complete"
                                          : "Bounded"}
                                      </strong>
                                    </span>

                                    {profile.long_temporal.execution && (
                                      <>
                                        <span>
                                          Observed order basis{" "}
                                          <strong>
                                            {profile.long_temporal.execution
                                              .observed_order_basis ?? "Unknown"}
                                          </strong>
                                        </span>

                                        <span>
                                          Canonical order established{" "}
                                          <strong>
                                            {profile.long_temporal.execution
                                              .canonical_order_established === true
                                              ? "Yes"
                                              : profile.long_temporal.execution
                                                .canonical_order_established === false
                                                ? "No"
                                                : "Not evaluated"}
                                          </strong>
                                        </span>
                                      </>
                                    )}

                                    {profile.long_temporal.continuity
                                      .largest_positive_intervals.length > 0 && (
                                        <>
                                          <span>
                                            <strong>
                                              Largest observed positive intervals
                                            </strong>
                                          </span>

                                          {profile.long_temporal.continuity
                                            .largest_positive_intervals.map(
                                              (interval) => (
                                                <span
                                                  key={`${interval.from_index}-${interval.to_index}`}
                                                >
                                                  <strong>
                                                    {interval.interval_seconds >= 3600
                                                      ? `${(
                                                        interval.interval_seconds / 3600
                                                      ).toFixed(1)} h`
                                                      : `${interval.interval_seconds.toLocaleString()} s`}
                                                  </strong>{" "}
                                                  {interval.from_value} → {interval.to_value}
                                                </span>
                                              ),
                                            )}
                                        </>
                                      )}
                                  </div>
                                </div>
                              )}


                            {strategy === "long_temporal" && (
                              <div className="analysis-group">
                                <div className="analysis-group-header">
                                  <strong>Time / Value Explorer</strong>
                                  <span>Vertical temporal axis</span>
                                </div>

                                <div className="analysis-group-content">
                                  <span>
                                    Detected time field{" "}
                                    <strong>
                                      {detectedTemporalColumnName ||
                                        "Unknown"}
                                    </strong>
                                  </span>
                                </div>

                                {columns.length === 0 ? (
                                  <p>
                                    No observed column structure available.
                                  </p>
                                ) : (
                                  <div
                                    style={{
                                      marginTop: "24px",
                                      marginBottom: "24px",
                                    }}
                                  >
                                    <select
                                      value={temporalValueColumn}
                                      disabled={
                                        isLoadingLongTemporalSeries
                                      }
                                      onChange={(event) => {
                                        setTemporalValueColumn(
                                          event.target.value,
                                        );
                                      }}
                                    >
                                      <option value="">
                                        Choose value column
                                      </option>

                                      {columns
                                        .filter((column) => {
                                          if (
                                            column.name ===
                                            detectedTemporalColumnName
                                          ) {
                                            return false;
                                          }

                                          const technicalType =
                                            column.technicalType
                                              .trim()
                                              .toUpperCase();

                                          return [
                                            "TINYINT",
                                            "SMALLINT",
                                            "INTEGER",
                                            "BIGINT",
                                            "HUGEINT",
                                            "UTINYINT",
                                            "USMALLINT",
                                            "UINTEGER",
                                            "UBIGINT",
                                            "UHUGEINT",
                                            "FLOAT",
                                            "REAL",
                                            "DOUBLE",
                                            "DECIMAL",
                                          ].some((prefix) =>
                                            technicalType.startsWith(
                                              prefix,
                                            ),
                                          );
                                        })
                                        .map((column) => (
                                          <option
                                            key={column.name}
                                            value={column.name}
                                          >
                                            {column.name}
                                          </option>
                                        ))}
                                    </select>

                                    <button
                                      type="button"
                                      disabled={
                                        !temporalValueColumn ||
                                        !detectedTemporalColumnName ||
                                        isLoadingLongTemporalSeries
                                      }
                                      onClick={() => {
                                        void loadLongTemporalSeries(
                                          temporalValueColumn,
                                        );
                                      }}
                                    >
                                      {isLoadingLongTemporalSeries
                                        ? "Loading..."
                                        : "Show temporal series"}
                                    </button>

                                    {longTemporalSeries && (
                                      <div
                                        style={{
                                          marginTop: "24px",
                                          display: "grid",
                                          gap: "16px",
                                        }}
                                      >
                                        <div className="analysis-group-content">
                                          <span>
                                            Value field{" "}
                                            <strong>
                                              {
                                                longTemporalSeries
                                                  .value_column_name
                                              }
                                            </strong>
                                          </span>

                                          <span>
                                            Usable observations{" "}
                                            <strong>
                                              {longTemporalSeries.source
                                                .usable_observation_count
                                                .toLocaleString()}
                                            </strong>
                                          </span>

                                          <span>
                                            Projection{" "}
                                            <strong>
                                              {
                                                longTemporalSeries
                                                  .display_projection
                                                  .mode
                                              }
                                            </strong>
                                          </span>

                                          <span>
                                            Display points{" "}
                                            <strong>
                                              {longTemporalSeries
                                                .display_projection
                                                .point_count
                                                .toLocaleString()}
                                            </strong>
                                          </span>
                                        </div>
                                        {longTemporalSeries.execution
                                          .limitations.length > 0 && (
                                            <div className="analysis-group-content">
                                              {longTemporalSeries.execution
                                                .limitations.map(
                                                  (limitation) => (
                                                    <span key={limitation}>
                                                      {limitation}
                                                    </span>
                                                  ),
                                                )}
                                            </div>
                                          )}

                                        <LongTemporalSeriesChart
                                          result={longTemporalSeries}
                                          selectedRange={
                                            longTemporalSeriesDetail
                                              ?.requested_range ?? null
                                          }
                                          onSelectBucket={(bucket) => {
                                            void loadLongTemporalSeriesDetail(
                                              longTemporalSeries.value_column_name,
                                              bucket.bucket_start,
                                              bucket.bucket_end,
                                            );
                                          }}
                                        />

                                        {isLoadingLongTemporalSeriesDetail && (
                                          <div className="analysis-group-content">
                                            <span>
                                              Loading selected temporal interval...
                                            </span>
                                          </div>
                                        )}

                                        {longTemporalSeriesDetail && (
                                          <div
                                            style={{
                                              display: "grid",
                                              gap: "12px",
                                            }}
                                          >
                                            <div className="analysis-group-content">
                                              <span>
                                                Selected interval{" "}
                                                <strong>
                                                  {longTemporalSeriesDetail.requested_range.start}
                                                  {" -> "}
                                                  {longTemporalSeriesDetail.requested_range.end}
                                                </strong>
                                              </span>

                                              <span>
                                                Matching observations{" "}
                                                <strong>
                                                  {longTemporalSeriesDetail.source
                                                    .matching_observation_count
                                                    .toLocaleString()}
                                                </strong>
                                              </span>
                                            </div>

                                            <LongTemporalSeriesChart
                                              result={longTemporalSeriesDetail}
                                              onSelectBucket={(bucket) => {
                                                void loadLongTemporalSeriesDetail(
                                                  longTemporalSeriesDetail.value_column_name,
                                                  bucket.bucket_start,
                                                  bucket.bucket_end,
                                                );
                                              }}
                                            />
                                          </div>
                                        )}

                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {strategy === "conservative_tabular" &&
                              orientation === "ambiguous" && (
                                <div className="analysis-group">
                                  <div className="analysis-group-header">
                                    <strong>Candidate Explorer</strong>
                                    <span>Ambiguous orientation</span>
                                  </div>

                                  <div className="analysis-group-content">
                                    <span>
                                      Temporal structure was detected in both
                                      directions. RAWSIGHT will not choose an
                                      axis automatically.
                                    </span>

                                    <span>
                                      Horizontal candidates{" "}
                                      <strong>
                                        {horizontalCandidateCount.toLocaleString()}
                                      </strong>
                                    </span>

                                    <span>
                                      Vertical candidates{" "}
                                      <strong>
                                        {verticalCandidateCount.toLocaleString()}
                                      </strong>
                                    </span>
                                  </div>
                                </div>
                              )}

                            {(strategy === "conservative_tabular" &&
                              orientation !== "ambiguous") ||
                              strategy === "conservative_unknown" ? (
                              <div className="analysis-group">
                                <div className="analysis-group-header">
                                  <strong>Column Explorer</strong>
                                  <span>Tabular exploration</span>
                                </div>

                                {columns.length === 0 ? (
                                  <div className="analysis-group-content">
                                    <span>
                                      No observed column structure available.
                                    </span>
                                  </div>
                                ) : (
                                  <div
                                    style={{
                                      marginTop: "24px",
                                      marginBottom: "24px",
                                    }}
                                  >
                                    <select
                                      value={rawAnalysisColumnName}
                                      onChange={(event) => {
                                        setRawAnalysisColumnName(
                                          event.target.value,
                                        );
                                        setRawAnalysisResult(null);
                                      }}
                                    >
                                      <option value="">
                                        Choose a column
                                      </option>

                                      {columns.map((column) => (
                                        <option
                                          key={column.name}
                                          value={column.name}
                                        >
                                          {column.name}
                                        </option>
                                      ))}
                                    </select>

                                    <button
                                      type="button"
                                      disabled={
                                        !rawAnalysisColumnName
                                      }
                                      onClick={() => {
                                        void runRawAnalysisColumn(
                                          rawAnalysisColumnName,
                                          selectedScopeColumn?.role,
                                        );
                                      }}
                                    >
                                      Explore Column
                                    </button>

                                    {rawAnalysisResult && (
                                      <p>
                                        Result:{" "}
                                        <strong>
                                          {rawAnalysisResult.column}
                                        </strong>
                                        {" · "}
                                        {rawAnalysisResult.routing}
                                      </p>
                                    )}

                                    {rawAnalysisResult && (
                                      <RawAnalysisVisualization
                                        result={rawAnalysisResult}
                                      />
                                    )}
                                  </div>
                                )}
                              </div>
                            ) : null}
                          </>
                        );
                      })()
                    )}
                  </div>
                )}
                {activeSection === "lineup" && (
                  <div className="metadata-workspace">
                    <div className="metadata-header">
                      <div>
                        <strong>The Lineup</strong>
                        <p>
                          Choose which columns matter for the analysis.
                          Your source data is never changed.
                        </p>
                      </div>
                    </div>


                    {(() => {
                      const activeDataset = activeProject.datasets.find(
                        (dataset) =>
                          dataset.id === activeProject.activeDatasetId,
                      );

                      const columns =
                        activeDataset?.structure?.columns ?? [];

                      if (columns.length === 0) {
                        return (
                          <p>
                            No observed column structure available.
                          </p>
                        );
                      }

                      return (
                        <div className="column-metadata-list">
                          {columns.map((column) => {
                            const scopeColumn =
                              activeDataset?.analysisScope?.columns.find(
                                (scopeColumn) =>
                                  scopeColumn.columnName === column.name,
                              );

                            const included =
                              scopeColumn?.included ?? true;

                            return (
                              <div
                                key={column.name}
                                className="column-metadata-row"
                              >
                                <strong>{column.name}</strong>

                                <span>{column.technicalType}</span>
                                <select
                                  value={scopeColumn?.role ?? ""}
                                  disabled={!included}
                                  onChange={(event) =>
                                    setAnalysisScopeColumnRole(
                                      column.name,
                                      event.target.value as AnalysisColumnRole,
                                    )
                                  }
                                >
                                  <option value="">Select role...</option>
                                  <option value="target">Target</option>
                                  <option value="feature">Feature</option>
                                  <option value="identifier">Identifier</option>
                                  <option value="time_axis">Time axis</option>
                                  <option value="grouping">Grouping</option>
                                  <option value="context">Context</option>
                                  <option value="provenance">Provenance</option>
                                </select>
                                <button
                                  type="button"
                                  onClick={() =>
                                    toggleAnalysisScopeColumn(column.name)
                                  }
                                >
                                  {included ? "Included" : "Excluded"}
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </div>
                )}
                {activeSection === "metadata" && (

                  <div className="metadata-workspace">
                    <div className="metadata-header">
                      <div>
                        <strong>Metadata</strong>
                        <p>
                          Add documentation and context that helps describe and interpret
                          this dataset.
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={addMetadataFile}
                      >
                        Add metadata file
                      </button>
                    </div>

                    <div className="metadata-sources">
                      <strong>Metadata sources</strong>

                      {activeProject.datasets
                        .find((dataset) => dataset.id === activeProject.activeDatasetId)
                        ?.metadata.sources.length === 0 ? (
                        <p>No metadata sources attached.</p>
                      ) : (
                        activeProject.datasets
                          .find((dataset) => dataset.id === activeProject.activeDatasetId)
                          ?.metadata.sources.map((source) => {
                            const activeDataset = activeProject.datasets.find(
                              (dataset) => dataset.id === activeProject.activeDatasetId,
                            );
                            const linkedColumns = (
                              activeDataset?.metadata.links ?? []
                            )
                              .filter(
                                (link) =>
                                  link.metadataSourceId === source.id &&
                                  link.targetType === "column" &&
                                  link.status === "linked",
                              )
                              .map((link) => link.columnName)
                              .filter((columnName): columnName is string => Boolean(columnName));
                            const linkedToDataset = (
                              activeDataset?.metadata.links ?? []
                            ).some(
                              (link) =>
                                link.metadataSourceId === source.id &&
                                link.targetType === "dataset" &&
                                link.status === "linked",
                            );

                            return (
                              <div className="metadata-source" key={source.id}>
                                <strong>{source.name}</strong>

                                <span>
                                  {source.type} · {source.scope}
                                </span>

                                {source.path && (
                                  <div>{source.path}</div>
                                )}

                                {linkedToDataset ? (
                                  <span>Linked to dataset</span>
                                ) : (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void linkMetadataSourceToDataset(source.id)
                                    }
                                  >
                                    Link to dataset
                                  </button>
                                )}
                                {linkedColumns.length > 0 && (
                                  <div>
                                    <strong>Linked columns</strong>

                                    {linkedColumns.map((columnName) => (
                                      <div key={columnName}>{columnName}</div>
                                    ))}
                                  </div>
                                )}

                                <div className="metadata-column-link">
                                  <select
                                    value={metadataColumnLinkDrafts[source.id] ?? ""}
                                    onChange={(event) =>
                                      setMetadataColumnLinkDrafts((current) => ({
                                        ...current,
                                        [source.id]: event.target.value,
                                      }))
                                    }
                                  >
                                    <option value="">Select column...</option>

                                    {(activeDataset?.structure?.columns ?? [])
                                      .filter((column) => !linkedColumns.includes(column.name))
                                      .map((column) => (
                                        <option key={column.name} value={column.name}>
                                          {column.name}
                                        </option>
                                      ))}
                                  </select>

                                  <button
                                    type="button"
                                    disabled={!metadataColumnLinkDrafts[source.id]}
                                    onClick={() => {
                                      const columnName = metadataColumnLinkDrafts[source.id];

                                      if (!columnName) {
                                        return;
                                      }

                                      void linkMetadataSourceToColumn(source.id, columnName);
                                    }}
                                  >
                                    Link to column
                                  </button>
                                </div>
                              </div>
                            );
                          })
                      )}
                    </div>
                    <div className="column-metadata">
                      <strong>Column metadata</strong>

                      {(() => {
                        const activeDataset = activeProject.datasets.find(
                          (dataset) => dataset.id === activeProject.activeDatasetId,
                        );

                        const columns = activeDataset?.structure?.columns ?? [];

                        if (columns.length === 0) {
                          return <p>No observed column structure available.</p>;
                        }

                        return (
                          <div className="column-metadata-list">
                            {columns.map((column) => {
                              const columnMetadata = activeDataset?.metadata.columns.find(
                                (metadata) => metadata.columnName === column.name,
                              );
                              const linkedMetadataSources = (
                                activeDataset?.metadata.links ?? []
                              )
                                .filter(
                                  (link) =>
                                    link.targetType === "column" &&
                                    link.columnName === column.name &&
                                    link.status === "linked",
                                )
                                .map((link) =>
                                  activeDataset?.metadata.sources.find(
                                    (source) => source.id === link.metadataSourceId,
                                  )?.name,
                                )
                                .filter((sourceName): sourceName is string => Boolean(sourceName));
                              return (
                                <div className="column-metadata-row" key={column.name}>
                                  <div>
                                    <strong>{column.name}</strong>
                                    <span>{column.technicalType}</span>
                                  </div>

                                  {editingColumnName === column.name ? (
                                    <div className="column-description-editor">
                                      <label>
                                        Semantic type
                                        <input
                                          type="text"
                                          value={columnSemanticTypeDraft}
                                          onChange={(event) =>
                                            setColumnSemanticTypeDraft(event.target.value)
                                          }
                                          placeholder="e.g. identifier, date, category"
                                        />
                                      </label>
                                      <label>
                                        Unit
                                        <input
                                          type="text"
                                          value={columnUnitDraft}
                                          onChange={(event) =>
                                            setColumnUnitDraft(event.target.value)
                                          }
                                          placeholder="e.g. kg, °C, EUR, metres"
                                        />
                                      </label>
                                      <label>
                                        <label>
                                          Format
                                          <input
                                            type="text"
                                            value={columnFormatDraft}
                                            onChange={(event) =>
                                              setColumnFormatDraft(event.target.value)
                                            }
                                            placeholder="e.g. YYYYMMDD, ISO 8601, decimal(10,2)"
                                          />
                                        </label>
                                        Description
                                        <textarea
                                          value={columnDescriptionDraft}
                                          onChange={(event) =>
                                            setColumnDescriptionDraft(event.target.value)
                                          }
                                          placeholder="Describe this column..."
                                          rows={3}
                                        />
                                      </label>
                                      {linkedMetadataSources.length > 0 && (
                                        <div className="column-metadata-links">
                                          <strong>Metadata links</strong>

                                          {linkedMetadataSources.map((sourceName) => (
                                            <div key={sourceName}>
                                              {sourceName}
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                      <div className="special-values-editor">
                                        <strong>Special values</strong>
                                        {columnSpecialValuesDraft.length > 0 && (
                                          <div className="special-values-list">
                                            {columnSpecialValuesDraft.map((specialValue, index) => (
                                              <div
                                                className="special-value-item"
                                                key={`${specialValue.value}-${index}`}
                                              >
                                                <div>
                                                  <strong>{specialValue.value}</strong>
                                                  <span>{specialValue.meaning}</span>
                                                </div>

                                                <div className="special-value-item-actions">
                                                  <span>
                                                    {specialValue.representsMissing
                                                      ? "Represents missing"
                                                      : "Valid value"}
                                                  </span>

                                                  <button
                                                    type="button"
                                                    onClick={() =>
                                                      setColumnSpecialValuesDraft((currentValues) =>
                                                        currentValues.filter(
                                                          (_, currentIndex) => currentIndex !== index,
                                                        ),
                                                      )
                                                    }
                                                  >
                                                    Remove
                                                  </button>
                                                </div>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                        <label>
                                          Value
                                          <input
                                            type="text"
                                            value={specialValueDraft}
                                            onChange={(event) =>
                                              setSpecialValueDraft(event.target.value)
                                            }
                                            placeholder="e.g. 0, -999, UNKNOWN"
                                          />
                                        </label>

                                        <label>
                                          Meaning
                                          <input
                                            type="text"
                                            value={specialValueMeaningDraft}
                                            onChange={(event) =>
                                              setSpecialValueMeaningDraft(event.target.value)
                                            }
                                            placeholder="e.g. No occurrence"
                                          />
                                        </label>

                                        <label className="special-value-missing">
                                          <input
                                            type="checkbox"
                                            checked={specialValueRepresentsMissingDraft}
                                            onChange={(event) =>
                                              setSpecialValueRepresentsMissingDraft(event.target.checked)
                                            }
                                          />
                                          Represents missing data
                                        </label>

                                        <button
                                          type="button"
                                          onClick={addSpecialValueDraft}
                                        >
                                          Add special value
                                        </button>

                                      </div>
                                      <div className="column-description-actions">
                                        <button
                                          type="button"
                                          onClick={() => void saveColumnDescription()}
                                        >
                                          Save
                                        </button>

                                        <button
                                          type="button"
                                          onClick={() => {
                                            setEditingColumnName(null);
                                            setColumnDescriptionDraft("");
                                            setColumnSemanticTypeDraft("");
                                            setColumnUnitDraft("");
                                            setColumnFormatDraft("");

                                            setColumnSpecialValuesDraft([]);
                                            setSpecialValueDraft("");
                                            setSpecialValueMeaningDraft("");
                                            setSpecialValueRepresentsMissingDraft(false);
                                          }}
                                        >
                                          Cancel
                                        </button>
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="column-description-display">
                                      <span>
                                        {columnMetadata?.description || "No description"}
                                      </span>

                                      <button
                                        type="button"
                                        onClick={() => beginEditColumnDescription(column.name)}
                                      >
                                        Edit
                                      </button>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()}
                    </div>
                  </div>
                )}

                {activeSection === "history" && (
                  <div className="workspace-placeholder">
                    <strong>History</strong>
                    <p>
                      Project events, decisions and transformations will be recorded here.
                    </p>
                  </div>
                )}
                {(activeSection === "overview" || activeSection === "data") && fileInfo && (
                  <div className="selected-file">
                    <div className="file-name">
                      {fileInfo.name}
                    </div>

                    <div className="file-details">
                      <span>{fileInfo.extension.toUpperCase()}</span>
                      <span>{formatFileSize(fileInfo.size)}</span>
                    </div>

                    <div className="file-path">
                      {fileInfo.path}
                    </div>
                  </div>
                )}

                {activeSection === "analysis" && (isAnalyzing || analysisComplete) && (
                  <div className="analysis-status">
                    <div className="analysis-text">
                      <strong>
                        {isAnalyzing
                          ? "Analyzing dataset..."
                          : "Analysis completed"}
                      </strong>

                      {isAnalyzing && (
                        <span>{progressMessage}</span>
                      )}
                    </div>

                    <div className="progress-steps">
                      {progressSteps.map((step, index) => {
                        const isCurrent =
                          isAnalyzing &&
                          index === progressSteps.length - 1;

                        return (
                          <div className="progress-step" key={step}>
                            <span className="progress-symbol">
                              {isCurrent ? "●" : "✓"}
                            </span>

                            <span>{step}</span>
                          </div>
                        );
                      })}
                    </div>

                    {isAnalyzing && (
                      <div className="progress-track">
                        <div className="progress-bar" />
                      </div>
                    )}
                  </div>
                )}

                {activeSection === "analysis" && profile && (
                  <div className="profile-result">
                    <div className="light-analysis-summary">
                      {profile.wide_temporal && (
                        <div className="analysis-group">
                          <div className="analysis-group-header">
                            <strong>Temporal structure</strong>
                            <span>
                              {profile.wide_temporal.status === "candidate"
                                ? "Wide temporal candidate"
                                : "Wide temporal"}
                            </span>
                          </div>

                          <div className="analysis-group-content">
                            <span>
                              Temporal columns{" "}
                              <strong>
                                {profile.wide_temporal.temporal_column_count !== null
                                  ? profile.wide_temporal.temporal_column_count.toLocaleString()
                                  : "Unknown"}
                              </strong>
                            </span>

                            <span>
                              Other columns{" "}
                              <strong>
                                {profile.wide_temporal.non_temporal_column_count !== null
                                  ? profile.wide_temporal.non_temporal_column_count.toLocaleString()
                                  : "Unknown"}
                              </strong>
                            </span>

                            <span>
                              Time range{" "}
                              <strong>
                                {profile.wide_temporal.range_start &&
                                  profile.wide_temporal.range_end
                                  ? `${profile.wide_temporal.range_start.slice(0, 10)} – ${profile.wide_temporal.range_end.slice(0, 10)}`
                                  : "Unknown"}
                              </strong>
                            </span>

                            <span>
                              Cadence{" "}
                              <strong>
                                {formatCadence(
                                  profile.wide_temporal.dominant_interval_seconds,
                                )}
                              </strong>
                            </span>

                            <span>
                              Sequence{" "}
                              <strong>
                                {profile.wide_temporal.order ?? "Unknown"}
                              </strong>
                            </span>

                            <span>
                              Cadence consistency{" "}
                              <strong>
                                {profile.wide_temporal.cadence_consistency !== null
                                  ? `${(
                                    profile.wide_temporal.cadence_consistency * 100
                                  ).toFixed(1)}%`
                                  : "Unknown"}
                              </strong>
                            </span>
                          </div>
                        </div>
                      )}

                      {profile.wide_temporal?.value_analysis && (
                        <>
                          <div className="analysis-group">
                            <div className="analysis-group-header">
                              <strong>Temporal value analysis</strong>
                              <span>
                                {profile.wide_temporal.value_analysis.status === "measured"
                                  ? "Measured"
                                  : profile.wide_temporal.value_analysis.status}
                              </span>
                            </div>

                            <div className="analysis-group-content">
                              <span>
                                Series{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.series_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Values analysed{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.temporal_value_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Numeric values{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.numeric_value_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Missing{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.missing_value_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Non-numeric{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.non_numeric_value_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Zero values{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.zero_value_count.toLocaleString()}
                                </strong>
                              </span>

                              {profile.wide_temporal.value_analysis_execution && (
                                <span>
                                  Execution{" "}
                                  <strong>
                                    {profile.wide_temporal.value_analysis_execution.execution_mode}
                                  </strong>
                                  {" · "}
                                  {profile.wide_temporal.value_analysis_execution.rows_processed.toLocaleString()}
                                  {" rows"}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="analysis-group">
                            <div className="analysis-group-header">
                              <strong>Series behaviour</strong>
                              <span>Observed</span>
                            </div>

                            <div className="analysis-group-content">
                              <span>
                                Constant{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.series_classification.constant.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Non-decreasing{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.series_classification.non_decreasing.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Non-increasing{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.series_classification.non_increasing.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Mixed{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.series_classification.mixed.toLocaleString()}
                                </strong>
                              </span>

                              {profile.wide_temporal.value_analysis.series_classification
                                .insufficient_adjacent_observations > 0 && (
                                  <span>
                                    Insufficient adjacent observations{" "}
                                    <strong>
                                      {profile.wide_temporal.value_analysis.series_classification
                                        .insufficient_adjacent_observations.toLocaleString()}
                                    </strong>
                                  </span>
                                )}

                              {profile.wide_temporal.value_analysis.series_classification
                                .no_numeric_data > 0 && (
                                  <span>
                                    No numeric observations{" "}
                                    <strong>
                                      {profile.wide_temporal.value_analysis.series_classification
                                        .no_numeric_data.toLocaleString()}
                                    </strong>
                                  </span>
                                )}
                            </div>
                          </div>

                          <div className="analysis-group">
                            <div className="analysis-group-header">
                              <strong>Observed transitions</strong>
                              <span>
                                {profile.wide_temporal.value_analysis.adjacent_transition_count.toLocaleString()}
                                {" comparable"}
                              </span>
                            </div>

                            <div className="analysis-group-content">
                              <span>
                                Increase{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.positive_transition_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Decrease{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.negative_transition_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Unchanged{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.unchanged_transition_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Series with decreases{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.series_with_negative_transitions.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Largest increase{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.largest_positive_change !== null
                                    ? profile.wide_temporal.value_analysis.largest_positive_change.toLocaleString()
                                    : "Not observed"}
                                </strong>
                              </span>

                              <span>
                                Largest decrease{" "}
                                <strong>
                                  {profile.wide_temporal.value_analysis.largest_negative_change !== null
                                    ? profile.wide_temporal.value_analysis.largest_negative_change.toLocaleString()
                                    : "Not observed"}
                                </strong>
                              </span>
                            </div>
                          </div>
                        </>
                      )}

                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Completeness</strong>
                          <span>
                            {profile.missing_values === null
                              ? "Not evaluated"
                              : profile.missing_values === 0
                                ? "No findings"
                                : "Review"}
                          </span>
                        </div>

                        <div className="analysis-group-content">
                          {profile.missing_values === null ? (
                            <span>Not evaluated by this analysis strategy</span>
                          ) : (
                            <>
                              <span>
                                <strong>
                                  {profile.missing_values.toLocaleString()}
                                </strong>{" "}
                                NULL values
                              </span>

                              <span>
                                {profile.missing_percent !== null
                                  ? `${profile.missing_percent.toFixed(2)}% of all values`
                                  : "Percentage not evaluated"}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Duplicates</strong>
                          <span>
                            {profile.duplicate_rows === null
                              ? "Not evaluated"
                              : profile.duplicate_rows === 0
                                ? "No findings"
                                : "Review"}
                          </span>
                        </div>

                        <div className="analysis-group-content">
                          {profile.duplicate_rows === null ? (
                            <span>Not evaluated by this analysis strategy</span>
                          ) : (
                            <>
                              <span>
                                <strong>
                                  {profile.duplicate_rows.toLocaleString()}
                                </strong>{" "}
                                exact duplicate rows
                              </span>

                              <span>
                                {profile.duplicate_percent !== null
                                  ? `${profile.duplicate_percent.toFixed(2)}% of rows`
                                  : "Percentage not evaluated"}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Metadata validation</strong>
                          <span>Not checked</span>
                        </div>

                        <div className="analysis-group-content">
                          <span>
                            Add or detect metadata to validate documented meaning against
                            the actual dataset.
                          </span>
                        </div>
                      </div>

                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Expectations</strong>
                          <span>None defined</span>
                        </div>

                        <div className="analysis-group-content">
                          <span>
                            Confirmed data rules and expectations will be checked here.
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="column-preview">
                      <div className="column-preview-header">
                        <strong>Detected structure</strong>
                        <span>{profile.column_count} columns</span>
                      </div>

                      {profile.columns
                        .slice(
                          0,
                          showAllDetectedColumns
                            ? profile.columns.length
                            : 8,
                        )
                        .map((column) => (
                          <div className="column-profile" key={column.name}>
                            <div className="column-profile-title">
                              <span>{column.name}</span>
                              <code>{column.type}</code>
                            </div>

                            <div className="column-metrics">
                              <span>
                                Missing{" "}
                                <strong>
                                  {column.null_count === null
                                    ? "Not evaluated"
                                    : column.null_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Distinct{" "}
                                <strong>
                                  {column.distinct_count === null
                                    ? "Not evaluated"
                                    : column.distinct_count.toLocaleString()}
                                </strong>
                              </span>

                              <span>
                                Cardinality{" "}
                                <strong>
                                  {column.unique_percent === null
                                    ? "Not evaluated"
                                    : `${column.unique_percent.toFixed(1)}%`}
                                </strong>
                              </span>

                              {column.min !== null && (
                                <span>
                                  Min{" "}
                                  <strong>
                                    {formatProfileValue(column.min)}
                                  </strong>
                                </span>
                              )}

                              {column.max !== null && (
                                <span>
                                  Max{" "}
                                  <strong>
                                    {formatProfileValue(column.max)}
                                  </strong>
                                </span>
                              )}
                            </div>

                            {column.value_evidence?.kind === "binary_compatible_numeric" && (
                              <>
                                <div className="column-signals">
                                  <span className="column-signal">
                                    Binary-valued numeric
                                  </span>
                                </div>

                                <div className="column-metrics">
                                  <span>
                                    Observed{" "}
                                    <strong>
                                      {column.value_evidence.observed_values.join(", ")}
                                    </strong>
                                  </span>

                                  <span>
                                    0{" "}
                                    <strong>
                                      {column.value_evidence.zero_count.toLocaleString()}
                                    </strong>
                                  </span>

                                  <span>
                                    1{" "}
                                    <strong>
                                      {column.value_evidence.one_count.toLocaleString()}
                                    </strong>
                                  </span>
                                </div>
                              </>
                            )}

                            <div className="column-signals">
                              {getColumnSignals(column, profile.rows).map(
                                (signal) => (
                                  <span
                                    className="column-signal"
                                    key={signal}
                                  >
                                    {signal}
                                  </span>
                                ),
                              )}
                            </div>

                            {column.semantic_hint && (
                              <div className="semantic-hint">
                                <div>
                                  <strong>
                                    Possible{" "}
                                    {column.semantic_hint.suggested_type}
                                  </strong>

                                  <span>
                                    {column.semantic_hint.format} ·{" "}
                                    {column.semantic_hint.confidence.toFixed(1)}%
                                    {" "}pattern match
                                  </span>
                                </div>

                                {column.semantic_hint.zero_count > 0 && (
                                  <div className="semantic-actions">
                                    <span className="semantic-warning">
                                      {column.semantic_hint.zero_count.toLocaleString()}
                                      {" "}zero values
                                    </span>

                                    <button
                                      type="button"
                                      onClick={() => inspectZeroRows(column)}
                                      disabled={isInspecting}
                                    >
                                      {isInspecting
                                        ? "Loading..."
                                        : "Show rows"}
                                    </button>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}

                      {profile.columns.length > 8 && (
                        <button
                          type="button"
                          className="more-columns"
                          onClick={() =>
                            setShowAllDetectedColumns((current) => !current)
                          }
                        >
                          {showAllDetectedColumns
                            ? "Show less"
                            : `+ ${profile.columns.length - 8} more columns`}
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {activeSection === "analysis" && rowInspection && (
                  <div className="row-inspection">
                    <div className="row-inspection-header">
                      <div>
                        <strong>
                          Rows where {rowInspection.filter.column} ={" "}
                          {rowInspection.filter.value}
                        </strong>

                        <span>
                          Showing{" "}
                          {rowInspection.returned_rows.toLocaleString()} of{" "}
                          {rowInspection.total_rows.toLocaleString()} matching
                          rows
                        </span>
                      </div>

                      <button
                        type="button"
                        onClick={() => setRowInspection(null)}
                      >
                        Close
                      </button>
                    </div>

                    <div className="row-table-container">
                      <table className="row-table">
                        <thead>
                          <tr>
                            {rowInspection.columns.map((column) => (
                              <th key={column}>{column}</th>
                            ))}
                          </tr>
                        </thead>

                        <tbody>
                          {rowInspection.rows.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                              {row.map((value, columnIndex) => (
                                <td key={columnIndex}>
                                  {value === null ? "NULL" : String(value)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {error && (
                  <div className="analysis-error">
                    <strong>Something went wrong</strong>
                    <span>{error}</span>
                  </div>
                )}

                <p className="local-note">
                  Your source data stays local.
                </p>
              </div>
            </main>
          </div>
        ) : (
          <>
            <h1>The good, the bad and the ugly of your data.</h1>

            <p className="subtitle">
              Understand, validate and prepare your data for AI.
            </p>

            <div className="drop-zone">
              <div className="drop-icon">+</div>

              <h2>Drop a dataset here</h2>

              <p>CSV · Excel · Parquet</p>

              <button
                type="button"
                onClick={openDataset}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? "Analyzing..." : "Open dataset"}
              </button>
            </div>

            {error && (
              <div className="analysis-error">
                <strong>Something went wrong</strong>
                <span>{error}</span>
              </div>
            )}

            <p className="local-note">
              Your source data stays local.
            </p>
            <div className="home-project-tools">
              {appSettings && (
                <div className="project-location">
                  <div>
                    <div className="project-location-label">
                      Project location
                    </div>

                    <div className="project-location-path">
                      {appSettings.defaultProjectRoot}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="project-location-button"
                    onClick={changeProjectRoot}
                  >
                    Change...
                  </button>
                </div>
              )}

              {projects.length > 0 && (
                <div className="recent-projects">
                  <strong>Recent projects</strong>

                  {projects.map((project) => (
                    <button
                      key={project.id}
                      type="button"
                      onClick={() => openExistingProject(project)}
                    >
                      {project.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </section>
    </main>
  );
}

export default App;