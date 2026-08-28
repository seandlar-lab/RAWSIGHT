import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { getCurrentWindow } from "@tauri-apps/api/window";
import type { RawsightProject } from "./types/project";
import "./App.css";

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
type ColumnInfo = {
  name: string;
  type: string;
  null_count: number;
  null_percent: number;
  distinct_count: number;
  unique_percent: number;
  min: string | number | null;
  max: string | number | null;
  semantic_hint: SemanticHint | null;

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

type DatasetProfile = {
  file: string;
  rows: number;
  column_count: number;
  duplicate_rows: number;
  duplicate_percent: number;
  missing_values: number;
  missing_percent: number;
  columns: ColumnInfo[];
};

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
  | "analysis"
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

function getColumnSignals(
  column: ColumnInfo,
  rowCount: number
): string[] {
  const signals: string[] = [];
  const nonNullCount = rowCount - column.null_count;

  if (
    nonNullCount > 0 &&
    column.distinct_count === nonNullCount
  ) {
    signals.push("Unique");
  }

  if (column.distinct_count === 1) {
    signals.push("Constant");
  }

  if (
    nonNullCount > 0 &&
    column.distinct_count > 1 &&
    column.distinct_count <= 20
  ) {
    signals.push("Low cardinality");
  }

  if (column.null_count > 0) {
    signals.push("Missing");
  }

  return signals;
}

function App() {
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);

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

      const savedProjectPath = await invoke<string>("save_project_json", {
        projectId: project.id,
        projectJson: JSON.stringify(project, null, 2),
        projectRoot: appSettings?.defaultProjectRoot ?? null,
      });

      setActiveProject(project);
      setActiveSection("overview");

      console.log("RAWSIGHT project saved:", savedProjectPath);
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

      console.log("RAWSIGHT project loaded:", project);
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
      const rawProfile = await invoke<string>("profile_dataset", {
        path: fileInfo.path,
      });

      const parsedProfile = JSON.parse(rawProfile) as DatasetProfile;

      setProfile(parsedProfile);
      setAnalysisComplete(true);
    } catch (err) {
      setError(String(err));
    } finally {
      setIsAnalyzing(false);
    }
  }
  async function inspectDatasetStructure(path: string) {
    const rawStructure = await invoke<string>("inspect_structure", {
      path,
    });

    const structure = JSON.parse(
      rawStructure,
    ) as StructureInspectionResult;

    console.log("RAWSIGHT structure inspection:", structure);

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
      <section className="hero">
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
                  onClick={() => setActiveSection("analysis")}
                  className={activeSection === "analysis" ? "active" : ""}
                >
                  Light Analysis
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
                  {activeSection === "metadata" && "Metadata"}
                  {activeSection === "analysis" && "Light Analysis"}
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
                        Check structure, missing values, exact duplicates and basic data quality.
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
                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Structure</strong>
                          <span>Observed</span>
                        </div>

                        <div className="analysis-group-content">
                          <span>
                            <strong>{profile.rows.toLocaleString()}</strong> rows
                          </span>

                          <span>
                            <strong>{profile.column_count.toLocaleString()}</strong> columns
                          </span>
                        </div>
                      </div>

                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Completeness</strong>
                          <span>
                            {profile.missing_values === 0 ? "No findings" : "Review"}
                          </span>
                        </div>

                        <div className="analysis-group-content">
                          <span>
                            <strong>{profile.missing_values.toLocaleString()}</strong>{" "}
                            NULL values
                          </span>

                          <span>
                            {profile.missing_percent.toFixed(2)}% of all values
                          </span>
                        </div>
                      </div>

                      <div className="analysis-group">
                        <div className="analysis-group-header">
                          <strong>Duplicates</strong>
                          <span>
                            {profile.duplicate_rows === 0 ? "No findings" : "Review"}
                          </span>
                        </div>

                        <div className="analysis-group-content">
                          <span>
                            <strong>{profile.duplicate_rows.toLocaleString()}</strong>{" "}
                            exact duplicate rows
                          </span>

                          <span>
                            {profile.duplicate_percent.toFixed(2)}% of rows
                          </span>
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

                      {profile.columns.slice(0, 8).map((column) => (
                        <div className="column-profile" key={column.name}>
                          <div className="column-profile-title">
                            <span>{column.name}</span>
                            <code>{column.type}</code>
                          </div>

                          <div className="column-metrics">
                            <span>
                              Missing{" "}
                              <strong>
                                {column.null_count.toLocaleString()}
                              </strong>
                            </span>

                            <span>
                              Distinct{" "}
                              <strong>
                                {column.distinct_count.toLocaleString()}
                              </strong>
                            </span>

                            <span>
                              Cardinality{" "}
                              <strong>
                                {column.unique_percent.toFixed(1)}%
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
                        <div className="more-columns">
                          + {profile.columns.length - 8} more columns
                        </div>
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