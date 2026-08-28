use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use tauri::{AppHandle, Emitter, Manager};

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

#[derive(serde::Serialize)]
#[serde(rename_all = "camelCase")]
struct ProjectListItem {
    id: String,
    name: String,
    path: String,
    updated_at: String,
}

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppSettings {
    default_project_root: String,
}

fn default_project_root(app: &AppHandle) -> Result<PathBuf, String> {
    let documents_dir = app
        .path()
        .document_dir()
        .map_err(|error| format!("Could not resolve Documents directory: {error}"))?;

    Ok(documents_dir.join("RAWSIGHT Projects"))
}

fn app_settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|error| format!("Could not resolve application data directory: {error}"))?;

    Ok(app_data_dir.join("settings.json"))
}

fn load_app_settings_from_disk(app: &AppHandle) -> Result<AppSettings, String> {
    let settings_path = app_settings_path(app)?;

    if !settings_path.exists() {
        return Ok(AppSettings {
            default_project_root: default_project_root(app)?
                .to_string_lossy()
                .into_owned(),
        });
    }

    let contents = fs::read_to_string(&settings_path)
        .map_err(|error| format!("Could not read application settings: {error}"))?;

    let mut settings: AppSettings = serde_json::from_str(&contents)
        .map_err(|error| format!("Application settings are invalid: {error}"))?;

    if settings.default_project_root.trim().is_empty() {
        settings.default_project_root = default_project_root(app)?
            .to_string_lossy()
            .into_owned();
    }

    Ok(settings)
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

    let profile_script = project_root.join("engine").join("profile.py");

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
        let line = line.map_err(|error| format!("Could not read profiling output: {error}"))?;

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
        return Err(engine_error.unwrap_or_else(|| {
            if stderr.trim().is_empty() {
                "Dataset profiling failed".to_string()
            } else {
                stderr.trim().to_string()
            }
        }));
    }

    result.ok_or_else(|| "Profiling engine returned no result".to_string())
}

#[tauri::command(async)]
fn inspect_rows(path: String, column: String, value: String, limit: u32) -> Result<String, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));

    let project_root = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .ok_or("Could not locate RAWSIGHT project root")?;

    let python = project_root
        .join(".venv")
        .join("Scripts")
        .join("python.exe");

    let inspect_script = project_root.join("engine").join("inspect_rows.py");

    if !python.exists() {
        return Err(format!(
            "Python environment not found: {}",
            python.display()
        ));
    }

    if !inspect_script.exists() {
        return Err(format!(
            "Row inspection engine not found: {}",
            inspect_script.display()
        ));
    }

    let output = Command::new(&python)
        .arg(&inspect_script)
        .arg(&path)
        .arg(&column)
        .arg(&value)
        .arg(limit.to_string())
        .output()
        .map_err(|error| format!("Could not start row inspection engine: {error}"))?;

    let stdout = String::from_utf8(output.stdout)
        .map_err(|error| format!("Invalid output from row inspection engine: {error}"))?;

    if !output.status.success() {
        return Err(stdout.trim().to_string());
    }

    Ok(stdout.trim().to_string())
}

#[tauri::command]
async fn inspect_structure(path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let project_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .and_then(|path| path.parent())
            .ok_or_else(|| "Could not resolve RAWSIGHT project root.".to_string())?
            .to_path_buf();

        let python_path = project_root
            .join(".venv")
            .join("Scripts")
            .join("python.exe");

        let script_path = project_root
            .join("engine")
            .join("inspect_structure.py");

        let output = std::process::Command::new(&python_path)
            .arg(&script_path)
            .arg(&path)
            .output()
            .map_err(|err| format!("Could not start structure inspection: {err}"))?;

        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);

        for line in stdout.lines() {
            if let Some(result) = line.strip_prefix("RESULT\t") {
                return Ok(result.to_string());
            }

            if let Some(error) = line.strip_prefix("ERROR\t") {
                return Err(error.to_string());
            }
        }

        if !output.status.success() {
            return Err(format!(
                "Structure inspection failed: {}",
                stderr.trim()
            ));
        }

        Err("Structure inspection returned no result.".to_string())
    })
    .await
    .map_err(|err| format!("Structure inspection task failed: {err}"))?
}

#[tauri::command]
fn save_project_json(
    app: AppHandle,
    project_id: String,
    project_json: String,
    project_root: Option<String>,
) -> Result<String, String> {
    if project_id.is_empty()
        || !project_id
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
    {
        return Err("Invalid project ID".to_string());
    }

    let project_value: serde_json::Value =
        serde_json::from_str(&project_json)
            .map_err(|error| format!("Project JSON is invalid: {error}"))?;

    let project_name = project_value
        .get("name")
        .and_then(|value| value.as_str())
        .unwrap_or("Untitled Project");

    let mut safe_name: String = project_name
        .chars()
        .map(|c| match c {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '_',
            _ => c,
        })
        .collect();

    safe_name = safe_name
        .trim()
        .trim_end_matches(|c| c == '.' || c == ' ')
        .to_string();

    if safe_name.is_empty() {
        safe_name = "Untitled Project".to_string();
    }

    let root_dir = match project_root
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
    {
        Some(root) => PathBuf::from(root),

        None => app
            .path()
            .document_dir()
            .map_err(|error| {
                format!("Could not resolve Documents directory: {error}")
            })?
            .join("RAWSIGHT Projects"),
    };

    fs::create_dir_all(&root_dir)
        .map_err(|error| format!("Could not create project root directory: {error}"))?;

    let preferred_project_dir =
        root_dir.join(format!("{safe_name}.rawsight"));

    let project_dir = if preferred_project_dir.exists() {
        let existing_project_path =
            preferred_project_dir.join("project.json");

        let existing_project_id = fs::read_to_string(&existing_project_path)
            .ok()
            .and_then(|contents| {
                serde_json::from_str::<serde_json::Value>(&contents).ok()
            })
            .and_then(|value| {
                value
                    .get("id")
                    .and_then(|id| id.as_str())
                    .map(str::to_string)
            });

        if existing_project_id.as_deref() == Some(project_id.as_str()) {
            preferred_project_dir
        } else {
            let short_id = project_id
                .chars()
                .take(8)
                .collect::<String>();

            root_dir.join(
                format!("{safe_name}-{short_id}.rawsight")
            )
        }
    } else {
        preferred_project_dir
    };

    fs::create_dir_all(&project_dir)
        .map_err(|error| format!("Could not create project directory: {error}"))?;

    let project_path = project_dir.join("project.json");
    let temp_path = project_dir.join("project.json.tmp");
    let backup_path = project_dir.join("project.json.bak");

    {
        let mut file = fs::File::create(&temp_path)
            .map_err(|error| {
                format!("Could not create temporary project file: {error}")
            })?;

        file.write_all(project_json.as_bytes())
            .map_err(|error| {
                format!("Could not write project data: {error}")
            })?;

        file.sync_all()
            .map_err(|error| {
                format!("Could not flush project data to disk: {error}")
            })?;
    }

    if backup_path.exists() {
        fs::remove_file(&backup_path)
            .map_err(|error| {
                format!("Could not remove old project backup: {error}")
            })?;
    }

    if project_path.exists() {
        fs::rename(&project_path, &backup_path)
            .map_err(|error| {
                format!("Could not create project backup: {error}")
            })?;
    }

    if let Err(error) = fs::rename(&temp_path, &project_path) {
        if backup_path.exists() {
            let _ = fs::rename(&backup_path, &project_path);
        }

        let _ = fs::remove_file(&temp_path);

        return Err(format!("Could not save project: {error}"));
    }

    if backup_path.exists() {
        let _ = fs::remove_file(&backup_path);
    }

    Ok(project_path.to_string_lossy().into_owned())
}

#[tauri::command]
fn get_app_settings(app: AppHandle) -> Result<AppSettings, String> {
    load_app_settings_from_disk(&app)
}

#[tauri::command]
fn save_app_settings(
    app: AppHandle,
    settings: AppSettings,
) -> Result<(), String> {
    let project_root = settings.default_project_root.trim();

    if project_root.is_empty() {
        return Err("Project location cannot be empty".to_string());
    }

    let project_root_path = PathBuf::from(project_root);

    fs::create_dir_all(&project_root_path)
        .map_err(|error| format!("Could not create project directory: {error}"))?;

    let settings_path = app_settings_path(&app)?;

    if let Some(parent) = settings_path.parent() {
        fs::create_dir_all(parent)
            .map_err(|error| format!("Could not create settings directory: {error}"))?;
    }

    let json = serde_json::to_string_pretty(&settings)
        .map_err(|error| format!("Could not serialize application settings: {error}"))?;

    fs::write(&settings_path, json)
        .map_err(|error| format!("Could not save application settings: {error}"))?;

    Ok(())
}

#[tauri::command]
fn list_projects(app: AppHandle) -> Result<Vec<ProjectListItem>, String> {
    let settings = load_app_settings_from_disk(&app)?;
    let root_dir = PathBuf::from(settings.default_project_root);

    if !root_dir.exists() {
        return Ok(Vec::new());
    }

    let entries = fs::read_dir(&root_dir)
        .map_err(|error| format!("Could not read project directory: {error}"))?;

    let mut projects: Vec<ProjectListItem> = Vec::new();

    for entry_result in entries {
        let entry = match entry_result {
            Ok(entry) => entry,
            Err(error) => {
                eprintln!("Could not read project directory entry: {error}");
                continue;
            }
        };

        let project_dir = entry.path();

        if !project_dir.is_dir() {
            continue;
        }

        let is_rawsight_project = project_dir
            .extension()
            .and_then(|extension| extension.to_str())
            .map(|extension| extension.eq_ignore_ascii_case("rawsight"))
            .unwrap_or(false);

        if !is_rawsight_project {
            continue;
        }

        let project_json_path = project_dir.join("project.json");

        if !project_json_path.is_file() {
            continue;
        }

        let contents = match fs::read_to_string(&project_json_path) {
            Ok(contents) => contents,
            Err(error) => {
                eprintln!(
                    "Could not read project {}: {error}",
                    project_json_path.display()
                );
                continue;
            }
        };

        let project_value: serde_json::Value = match serde_json::from_str(&contents) {
            Ok(value) => value,
            Err(error) => {
                eprintln!(
                    "Invalid project JSON in {}: {error}",
                    project_json_path.display()
                );
                continue;
            }
        };

        let id = project_value
            .get("id")
            .and_then(|value| value.as_str())
            .unwrap_or("")
            .to_string();

        let name = project_value
            .get("name")
            .and_then(|value| value.as_str())
            .unwrap_or("Unnamed project")
            .to_string();

        let updated_at = project_value
            .get("updatedAt")
            .and_then(|value| value.as_str())
            .unwrap_or("")
            .to_string();

        if id.is_empty() {
            continue;
        }

        projects.push(ProjectListItem {
            id,
            name,
            path: project_dir.to_string_lossy().into_owned(),
            updated_at,
        });
    }

    projects.sort_by(|a, b| b.updated_at.cmp(&a.updated_at));

    Ok(projects)
}

#[tauri::command]
fn load_project(project_path: String) -> Result<String, String> {
    let project_dir = PathBuf::from(project_path);
    let project_json_path = project_dir.join("project.json");

    if !project_json_path.is_file() {
        return Err("Project file could not be found".to_string());
    }

    let contents = fs::read_to_string(&project_json_path)
        .map_err(|error| format!("Could not read project: {error}"))?;

    serde_json::from_str::<serde_json::Value>(&contents)
        .map_err(|error| format!("Project JSON is invalid: {error}"))?;

    Ok(contents)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_window_state::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_file_info,
            profile_dataset,
            inspect_rows,
			inspect_structure,
			save_project_json,
			get_app_settings,
            save_app_settings,
			list_projects,
			load_project
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
