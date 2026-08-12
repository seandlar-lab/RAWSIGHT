use std::path::Path;

#[derive(serde::Serialize)]
struct FileInfo {
    name: String,
    path: String,
    extension: String,
    size: u64,
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![get_file_info])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}