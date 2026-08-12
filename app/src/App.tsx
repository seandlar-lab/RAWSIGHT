import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";

type FileInfo = {
  name: string;
  path: string;
  extension: string;
  size: number;
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

function App() {
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);

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

    const info = await invoke<FileInfo>("get_file_info", {
      path: file,
    });

    setFileInfo(info);
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

          <button type="button" onClick={openDataset}>
            Open dataset
          </button>
        </div>

        {fileInfo && (
          <div className="selected-file">
            <div className="file-name">{fileInfo.name}</div>

            <div className="file-details">
              <span>{fileInfo.extension.toUpperCase()}</span>
              <span>{formatFileSize(fileInfo.size)}</span>
            </div>

            <div className="file-path">{fileInfo.path}</div>
          </div>
        )}

        <p className="local-note">Your source data stays local.</p>
      </section>
    </main>
  );
}

export default App;
