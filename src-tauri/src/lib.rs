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
fn start_backend(_app_handle: tauri::AppHandle) -> Result<String, String> {
    if backend_healthy() {
        return Ok("Backend already running on 127.0.0.1:8000".into());
    }

    if cfg!(target_os = "windows") {
        // Auto-detect WSL project path by searching for start_backend.sh
        let repo = std::env::var("OWNEX_WSL_REPO")
            .unwrap_or_else(|_| {
                // Try common WSL home paths
                let candidates = vec![
                    "/home/adriel/projects/Rastro",
                    "/home/$USER/projects/Rastro",
                    "/home/$USER/Rastro",
                    "/mnt/c/Users/$USER/projects/Rastro",
                ];
                // For now, use the first candidate - the PowerShell launcher
                // will handle the real auto-detection
                "/home/adriel/projects/Rastro".to_string()
            });
        let script = format!("{repo}/start_backend.sh");
        let child = Command::new("wsl.exe")
            .args(["-d", "Ubuntu", "--", "bash", "-lc", &script])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to start backend via WSL: {e}"))?;
        return Ok(format!("Backend start requested via WSL (PID: {})", child.id()));
    }

    let resource_dir = _app_handle
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?;

    let backend_script = resource_dir.join("binaries").join("start_backend.py");
    if !backend_script.exists() {
        eprintln!(
            "[orion-backend] start_backend.py not found at {} — run the backend manually (uvicorn api.main:app on :8000)",
            backend_script.display()
        );
        return Ok("Backend not bundled — run manually on :8000".into());
    }
    let python = "python3";

    let child = Command::new(python)
        .arg(&backend_script)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start backend: {e}"))?;

    Ok(format!("Backend started (PID: {})", child.id()))
}

fn backend_healthy() -> bool {
    let check = Command::new("curl")
        .args(["-s", "-m", "2", "http://127.0.0.1:8000/api/health"])
        .output();
    match check {
        Ok(out) => out.status.success() && out.stdout.windows(14).any(|w| w == b"\"status\":\"ok\""),
        Err(_) => false,
    }
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
