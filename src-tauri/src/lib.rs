use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};
mod remote_control;

#[tauri::command]
fn get_platform() -> String {
    if cfg!(target_os = "macos") {
        "macos".into()
    } else if cfg!(target_os = "windows") {
        "windows".into()
    } else {
        "linux".into()
    }
}

#[tauri::command]
fn start_backend(app_handle: tauri::AppHandle) -> Result<String, String> {
    let resource_dir = app_handle
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?;

    let backend_script = resource_dir.join("binaries").join("start_backend.py");
    let python = if cfg!(target_os = "windows") {
        "python.exe"
    } else {
        "python3"
    };

    let child = Command::new(python)
        .arg(&backend_script)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {e}"))?;

    Ok(format!("Backend started (PID: {})", child.id()))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_http::init())
        .invoke_handler(tauri::generate_handler![
            get_platform,
            start_backend,
            remote_control::remote_create_session,
            remote_control::remote_chat,
            remote_control::remote_approve,
            remote_control::remote_get_session,
            remote_control::remote_get_history,
            remote_control::remote_health,
        ])
        .setup(|app| {
            #[cfg(desktop)]
            {
                use tauri::menu::PredefinedMenuItem;

                let show = MenuItem::with_id(app, "show", "Mostrar OWNEX", true, None::<&str>)?;
                let separator = PredefinedMenuItem::separator(app)?;
                let quit = MenuItem::with_id(app, "quit", "Salir", true, Some("CmdOrCtrl+Q"))?;

                let menu = Menu::with_items(app, &[&show, &separator, &quit])?;

                let _tray = TrayIconBuilder::new()
                    .icon(app.default_window_icon().unwrap().clone())
                    .menu(&menu)
                    .tooltip("OWNEX — Security Intelligence OS")
                    .on_menu_event(move |app, event| match event.id.as_ref() {
                        "show" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "quit" => {
                            app.exit(0);
                        }
                        _ => {}
                    })
                    .build(app)?;
            }

            #[cfg(not(debug_assertions))]
            {
                let app_handle = app.handle().clone();
                thread::spawn(move || {
                    thread::sleep(Duration::from_secs(2));
                    let _ = start_backend(app_handle);
                });
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running OWNEX desktop");
}
