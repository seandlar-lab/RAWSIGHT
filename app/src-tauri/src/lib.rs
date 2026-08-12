use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use tauri::{AppHandle, Emitter};

#[derive(serde::Serialize)]
struct FileInfo {
    name: String,
    path: String,
    extension: String,
    size: u64,
}

#[derive(Clone, serde::Serialize)]
struct ProfileProgress {
    message: String,
}

#[tauri::command]
fn get_file_info(path: String) -> Result<FileInfo, String> {
    let file_path = Path::new(&path);

    let metadata = std::fs::metadata(file_path)
        .map_err(|error| format!("Could not read file metadata: {error}"))?;

    let name = file_path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or("")
        .to_string();

    let extension = file_path
        .extension()
        .and_then(|extension| extension.to_str())
        .unwrap_or("")
        .to_lowercase();

    Ok(FileInfo {
        name,
        path,
        extension,
        size: metadata.len(),
    })
}

#[tauri::command(async)]
fn profile_dataset(app: AppHandle, path: String) -> Result<String, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

    let project_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .ok_or("Could not locate RAWSIGHT project root")?;

    let python = project_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");

    let profile_script = project_root
        .join("engine")
        .join("profile.py");

    if !python.exists() {
        return Err(format!(
            "Python environment not found: {}",
            python.display()
        ));
    }

    if !profile_script.exists() {
        return Err(format!(
            "Profiling engine not found: {}",
            profile_script.display()
        ));
    }

    let mut child = Command::new(&python)
        .arg(&profile_script)
        .arg(&path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("Could not start profiling engine: {error}"))?;

    let stdout = child
        .stdout
        .take()
        .ok_or("Could not read profiling engine output")?;

    let reader = BufReader::new(stdout);

    let mut result: Option<String> = None;
    let mut engine_error: Option<String> = None;

    for line in reader.lines() {
        let line =
            line.map_err(|error| format!("Could not read profiling output: {error}"))?;

        if let Some(message) = line.strip_prefix("PROGRESS\t") {
            app.emit(
                "profile-progress",
                ProfileProgress {
                    message: message.to_string(),
                },
            )
            .map_err(|error| format!("Could not send progress event: {error}"))?;
        } else if let Some(json) = line.strip_prefix("RESULT\t") {
            result = Some(json.to_string());
        } else if let Some(message) = line.strip_prefix("ERROR\t") {
            engine_error = Some(message.to_string());
        }
    }

    let status = child
        .wait()
        .map_err(|error| format!("Could not wait for profiling engine: {error}"))?;

    let mut stderr = String::new();

    if let Some(mut error_output) = child.stderr.take() {
        error_output
            .read_to_string(&mut stderr)
            .map_err(|error| format!("Could not read profiling error: {error}"))?;
    }

    if !status.success() {
        return Err(
            engine_error.unwrap_or_else(|| {
                if stderr.trim().is_empty() {
                    "Dataset profiling failed".to_string()
                } else {
                    stderr.trim().to_string()
                }
            }),
        );
    }

    result.ok_or_else(|| "Profiling engine returned no result".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_file_info,
            profile_dataset
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}