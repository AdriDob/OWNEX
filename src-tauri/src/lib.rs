use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            // Set app icon font for tray if needed
            #[cfg(desktop)]
            app.handle().plugin(tauri_plugin_notification::init())?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running ORION desktop");
}
