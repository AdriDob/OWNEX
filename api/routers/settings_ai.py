from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.ai.provider import PROVIDER_CATALOG, get_registry

router = APIRouter(prefix="/api/settings/ai", tags=["settings-ai"])


@router.get("/providers")
def list_providers():
    registry = get_registry()
    return {"providers": registry.list_providers()}


@router.get("/config")
def get_config():
    registry = get_registry()
    provider = registry.get_provider()
    cfg = registry._load_config()
    return {
        "provider_type": cfg.get("provider_type", "ollama"),
        "host": cfg.get("host", ""),
        "model": cfg.get("model", "") or cfg.get("llm_model", ""),
        "api_base": cfg.get("api_base", ""),
        "active_provider": provider.name,
        "available": provider.is_available(),
    }


class AIConfigUpdate(BaseModel):
    provider_type: str = "ollama"
    host: str = ""
    model: str = ""
    api_key: str = ""
    api_base: str = ""


@router.put("/config")
def update_config(body: AIConfigUpdate):
    valid_ids = {s.id for s in PROVIDER_CATALOG}
    if body.provider_type not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Invalid provider. Choose from: {', '.join(valid_ids)}")

    updates = {"provider_type": body.provider_type}
    if body.provider_type == "ollama":
        updates["host"] = body.host or "http://localhost:11434"
        updates["model"] = body.model or "freehuntx/qwen3-coder:8b"
    elif body.provider_type == "openai":
        updates["api_base"] = body.api_base or "https://api.openai.com/v1"
        updates["llm_model"] = body.model or "gpt-4o-mini"
        if body.api_key:
            updates["api_key"] = body.api_key
    elif body.provider_type == "gemini":
        # build_provider: gemini usa gemini_api_key/gemini_model y cae a Ollama local.
        if body.api_key:
            updates["gemini_api_key"] = body.api_key
        if body.model:
            updates["gemini_model"] = body.model
        if body.host:
            updates["ollama_host"] = body.host
    elif body.provider_type == "openrouter":
        updates["openrouter_model"] = body.model or "openai/gpt-4o-mini"
        if body.api_key:
            updates["openrouter_api_key"] = body.api_key
        if body.api_base:
            updates["api_base"] = body.api_base
    elif body.provider_type == "devin":
        # Agent CLI free: path al binario + modelo.
        if body.host:
            updates["devin_path"] = body.host
        if body.model:
            updates["devin_model"] = body.model
    elif body.provider_type == "freebuff":
        # Agente free: ruta al config yaml.
        if body.host:
            updates["freebuff_config_path"] = body.host

    registry = get_registry()
    provider = registry.set_config(updates)
    return {
        "status": "ok",
        "active_provider": provider.name,
        "available": provider.is_available(),
    }
