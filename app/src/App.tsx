import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";

type FileInfo = {
  name: string;
  path: string;
  extension: string;
  size: number;
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

type ProfileProgress = {
  message: string;
};

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
    setProgressSteps([]);
    setAnalysisComplete(false);
    setProgressMessage("Preparing analysis");

    try {
      const info = await invoke<FileInfo>("get_file_info", {
        path: file,
      });

      setFileInfo(info);
      setProgressMessage("Starting analysis");
      setIsAnalyzing(true);

      const rawProfile = await invoke<string>("profile_dataset", {
        path: file,
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

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="brand">RAWSIGHT</div>

        <h1>The good, the bad and the ugly of your data.</h1>

        <p className="subtitle">
          Understand, validate and prepare your data for AI.
        </p>

        <div className="drop-zone">
          <div className="drop-icon">＋</div>

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

        {fileInfo && (
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

        {(isAnalyzing || analysisComplete) && (
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

        {profile && (
          <div className="profile-result">
            <div className="profile-summary">
              <div className="profile-card">
                <strong>{profile.rows.toLocaleString()}</strong>
                <span>Rows</span>
              </div>

              <div className="profile-card">
                <strong>{profile.column_count.toLocaleString()}</strong>
                <span>Columns</span>
              </div>

              <div className="profile-card">
                <strong>{profile.duplicate_rows.toLocaleString()}</strong>
                <span>
                  Exact duplicates · {profile.duplicate_percent.toFixed(2)}%
                </span>
              </div>

              <div className="profile-card">
                <strong>{profile.missing_values.toLocaleString()}</strong>
                <span>
                  Missing values · {profile.missing_percent.toFixed(2)}%
                </span>
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
                      <strong>{column.null_count.toLocaleString()}</strong>
                    </span>

                    <span>
                      Distinct{" "}
                      <strong>{column.distinct_count.toLocaleString()}</strong>
                    </span>

                    <span>
                      Cardinality{" "}
                      <strong>{column.unique_percent.toFixed(1)}%</strong>
                    </span>

                    {column.min !== null && (
                      <span>
                        Min{" "}
                        <strong>{formatProfileValue(column.min)}</strong>
                      </span>
                    )}

                    {column.max !== null && (
                      <span>
                        Max{" "}
                        <strong>{formatProfileValue(column.max)}</strong>
                      </span>
                    )}
                  </div>

                  <div className="column-signals">
                    {getColumnSignals(column, profile.rows).map((signal) => (
                      <span className="column-signal" key={signal}>
                        {signal}
                      </span>
                    ))}
                  </div>
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
        {error && (
          <div className="analysis-error">
            <strong>Could not analyze dataset</strong>
            <span>{error}</span>
          </div>
        )}

        <p className="local-note">
          Your source data stays local.
        </p>
      </section>
    </main>
  );
}

export default App;