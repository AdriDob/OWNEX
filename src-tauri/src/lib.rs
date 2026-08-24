#[allow(unused_imports)]
use std::net::TcpListener;
#[allow(unused_imports)]
use std::sync::atomic::{AtomicBool, Ordering};
#[allow(unused_imports)]
use std::sync::{Arc, Mutex};
#[allow(unused_imports)]
use std::thread;
use std::time::Duration;

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Emitter, Manager,
};
mod remote_control;

#[allow(unused_imports)]
use tauri_plugin_shell::ShellExt;

/// Port the backend is listening on (set after successful start).
static BACKEND_READY: AtomicBool = AtomicBool::new(false);

/// Tauri command: check if backend is healthy.
#[tauri::command]
fn is_backend_ready() -> bool {
    BACKEND_READY.load(Ordering::Relaxed)
}

/// Tauri command: get the backend port (for frontend dynamic discovery).
#[tauri::command]
fn get_backend_port() -> u16 {
    // Read from env var set during startup
    std::env::var("OWNEX_BACKEND_PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(8000)
}

#[allow(dead_code)]
/// Scan for an available TCP port in [start, start+100).
fn find_available_port(start: u16) -> Option<u16> {
    for port in start..start + 100 {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return Some(port);
        }
    }
    None
}

#[allow(dead_code)]
/// Check if the backend health endpoint responds.
fn backend_healthy(port: u16) -> bool {
    let url = format!("http://127.0.0.1:{port}/api/health");
    reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .and_then(|c| c.get(&url).send())
        .map(|r| r.status().is_success())
        .unwrap_or(false)
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
            is_backend_ready,
            get_backend_port,
            remote_control::remote_create_session,
            remote_control::remote_chat,
            remote_control::remote_approve,
            remote_control::remote_get_session,
            remote_control::remote_get_history,
            remote_control::remote_health,
        ])
        .setup(|app| {
            // ── System tray ──
            #[cfg(desktop)]
            {
                use tauri::menu::PredefinedMenuItem;
                let show = MenuItem::with_id(app, "show", "Mostrar OWNEX Alpha", true, None::<&str>)?;
                let separator = PredefinedMenuItem::separator(app)?;
                let quit = MenuItem::with_id(app, "quit", "Salir", true, Some("CmdOrCtrl+Q"))?;
                let menu = Menu::with_items(app, &[&show, &separator, &quit])?;

                let _tray = TrayIconBuilder::new()
                    .icon(app.default_window_icon().unwrap().clone())
                    .menu(&menu)
                    .tooltip("OWNEX Alpha — Security Intelligence OS")
                    .on_menu_event(move |app, event| match event.id.as_ref() {
                        "show" => {
                            if let Some(w) = app.get_webview_window("main") {
                                let _ = w.show();
                                let _ = w.set_focus();
                            }
                        }
                        "quit" => app.exit(0),
                        _ => {}
                    })
                    .build(app)?;
            }

            // ── Backend lifecycle (release builds) ──
            #[cfg(not(debug_assertions))]
            {
                let handle = app.handle().clone();
                thread::spawn(move || launch_backend(handle));
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running OWNEX Alpha");
}

#[cfg(not(debug_assertions))]
fn launch_backend(app: tauri::AppHandle) {
    use tauri_plugin_shell::process::CommandChild;

    // 1. Find available port
    let port = find_available_port(8000).unwrap_or_else(|| {
        emit_log(&app, "error", "No available port found in 8000-8099");
        8000
    });
    std::env::set_var("OWNEX_BACKEND_PORT", port.to_string());
    eprintln!("[ownex-tauri] Selected port: {port}");

    // 2. Check if already running (e.g. from external process)
    if backend_healthy(port) {
        eprintln!("[ownex-tauri] Backend already running on :{port}");
        BACKEND_READY.store(true, Ordering::Relaxed);
        emit_log(&app, "info", &format!("Backend already running on :{port}"));
        let _ = app.emit("backend-ready", serde_json::json!({"port": port}));
        return;
    }

    // 3. Spawn sidecar with --port arg
    let sidecar = match app.shell().sidecar("ownex-backend") {
        Ok(s) => s,
        Err(e) => {
            let msg = format!("Failed to resolve sidecar: {e}");
            eprintln!("[ownex-tauri] ERROR: {msg}");
            emit_log(&app, "error", &msg);
            let _ = app.emit("backend-error", serde_json::json!({"message": msg}));
            return;
        }
    };

    let child: CommandChild = match sidecar.args(["--port", &port.to_string()]).spawn() {
        Ok((_rx, child)) => {
            eprintln!("[ownex-tauri] Sidecar spawned (PID: {}), waiting for health on :{port}...", child.pid());
            child
        }
        Err(e) => {
            let msg = format!("Failed to spawn backend: {e}");
            eprintln!("[ownex-tauri] ERROR: {msg}");
            emit_log(&app, "error", &msg);
            let _ = app.emit("backend-error", serde_json::json!({"message": msg}));
            return;
        }
    };

    // Store child handle for graceful shutdown
    let child_arc = Arc::new(Mutex::new(Some(child)));
    let child_for_shutdown = child_arc.clone();
    app.manage(child_arc);

    // 4. Health check loop (max 60s, exponential backoff)
    let mut delay = 1u64;
    for i in 0..60 {
        thread::sleep(Duration::from_secs(delay.min(5)));
        if backend_healthy(port) {
            BACKEND_READY.store(true, Ordering::Relaxed);
            let msg = format!("Backend ready on :{port} after {i}s");
            eprintln!("[ownex-tauri] {msg}");
            emit_log(&app, "info", &msg);
            let _ = app.emit("backend-ready", serde_json::json!({"port": port}));
            return;
        }
        delay = (delay * 2).min(5);
    }

    // 5. Timeout — kill child, emit error
    let msg = format!("Backend failed to start on :{port} within 60s");
    eprintln!("[ownex-tauri] ERROR: {msg}");
    emit_log(&app, "error", &msg);
    let _ = app.emit("backend-error", serde_json::json!({"message": msg}));

    // Attempt to kill the stuck child
    if let Some(mut c) = child_for_shutdown.lock().ok().and_then(|mut g| g.take()) {
        let _ = c.kill();
    }
}

#[allow(dead_code)]
fn emit_log(app: &tauri::AppHandle, level: &str, msg: &str) {
    let _ = app.emit("log-message", serde_json::json!({"level": level, "message": msg}));
}

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
