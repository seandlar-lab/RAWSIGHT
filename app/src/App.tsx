import { useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

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

    if (typeof file === "string") {
      setSelectedFile(file);
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

          <button type="button" onClick={openDataset}>
            Open dataset
          </button>
        </div>

        {selectedFile && (
          <div className="selected-file">
            <strong>Selected dataset</strong>
            <span>{selectedFile}</span>
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
