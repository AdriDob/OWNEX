use serde::{Deserialize, Serialize};
use tauri::command;

fn backend_url(path: &str) -> String {
    let port = std::env::var("OWNEX_BACKEND_PORT")
        .ok()
        .and_then(|s| s.parse::<u16>().ok())
        .unwrap_or(8000);
    format!("http://127.0.0.1:{port}{path}")
}

#[derive(Debug, Serialize, Deserialize)]
pub struct CreateSessionRequest {
    pub device_id: String,
    pub user_id: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SessionResponse {
    pub session_id: String,
    pub device_id: String,
    pub user_id: String,
    pub created_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatRequest {
    pub session_id: String,
    pub message: String,
    pub auto_approve: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ChatResponse {
    pub r#type: String,
    pub command_id: Option<String>,
    pub success: Option<bool>,
    pub output: Option<String>,
    pub error: Option<String>,
    pub message: String,
    pub reasoning: Option<String>,
    pub alternatives: Option<Vec<String>>,
    pub preconditions: Option<Vec<String>>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApproveRequest {
    pub session_id: String,
    pub command_id: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SessionInfo {
    pub session_id: String,
    pub device_id: String,
    pub user_id: String,
    pub created_at: String,
    pub last_activity: String,
    pub active_commands: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HistoryResponse {
    pub session_id: String,
    pub commands: Vec<HistoryCommand>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct HistoryCommand {
    pub id: String,
    pub user_input: String,
    pub status: String,
    pub risk_level: String,
    pub created_at: String,
    pub completed_at: Option<String>,
}

#[command]
pub async fn remote_create_session(
    request: CreateSessionRequest,
) -> Result<SessionResponse, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(backend_url("/remote/session"))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("API error: {}", resp.status()));
    }

    let data: SessionResponse = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data)
}

#[command]
pub async fn remote_chat(request: ChatRequest) -> Result<ChatResponse, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(backend_url("/remote/chat"))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("API error: {}", resp.status()));
    }

    let data: ChatResponse = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data)
}

#[command]
pub async fn remote_approve(request: ApproveRequest) -> Result<ChatResponse, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post(backend_url("/remote/approve"))
        .json(&request)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("API error: {}", resp.status()));
    }

    let data: ChatResponse = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data)
}

#[command]
pub async fn remote_get_session(session_id: String) -> Result<SessionInfo, String> {
    let client = reqwest::Client::new();
    let resp = client
        .get(backend_url(&format!("/remote/session/{session_id}")))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("API error: {}", resp.status()));
    }

    let data: SessionInfo = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data)
}

#[command]
pub async fn remote_get_history(
    session_id: String,
    limit: Option<i32>,
) -> Result<HistoryResponse, String> {
    let client = reqwest::Client::new();
    let url = backend_url(&format!(
        "/remote/history/{session_id}?limit={}",
        limit.unwrap_or(50)
    ));
    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("API error: {}", resp.status()));
    }

    let data: HistoryResponse = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data)
}

#[command]
pub async fn remote_health() -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let resp = client
        .get(backend_url("/api/health"))
        .send()
        .await
        .map_err(|e| format!("Request failed: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("API error: {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| e.to_string())?;
    Ok(data)
}
