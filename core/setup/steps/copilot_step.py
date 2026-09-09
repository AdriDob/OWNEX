from __future__ import annotations

from typing import Any

from core.setup.steps import define_step

COPILOT_SCHEMA: dict[str, Any] = {
    "type": "form",
    "fields": [
        {
            "key": "authority_level",
            "label": "Nivel de autoridad COPILOT",
            "type": "select",
            "required": True,
            "default": "senior_hunter",
            "options": [
                {"value": "observer", "label": "Observer — solo recomendar"},
                {"value": "assistant", "label": "Assistant — actuar con aprobación"},
                {"value": "operator", "label": "Operator — ejecución supervisada"},
                {"value": "senior_hunter", "label": "Senior Hunter — autónomo"},
                {"value": "administrator", "label": "Administrator — control total"},
            ],
        },
        {
            "key": "auto_execute",
            "label": "Ejecución automática",
            "type": "switch",
            "required": False,
            "default": True,
            "description": "COPILOT ejecuta acciones sin esperar confirmación",
        },
        {
            "key": "llm_provider",
            "label": "Proveedor LLM",
            "type": "select",
            "required": True,
            "default": "ollama",
            "options": [
                {"value": "ollama", "label": "Ollama (local)"},
                {"value": "openai", "label": "OpenAI"},
                {"value": "gemini", "label": "Gemini"},
            ],
        },
        {
            "key": "model",
            "label": "Modelo",
            "type": "text",
            "required": False,
            "default": "mistral",
            "placeholder": "mistral, gpt-4, gemini-pro...",
        },
    ],
}


@define_step(
    step_id="copilot",
    label="COPILOT",
    description="Configurar el nivel de autonomía del asistente de inteligencia",
    icon="bot",
    order=3,
    required=True,
    schema=COPILOT_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    authority = state.get("authority_level", "senior_hunter")
    auto_execute = state.get("auto_execute", True)
    provider = state.get("llm_provider", "ollama")
    model = state.get("model", "")

    if provider == "ollama" and not model:
        model = "mistral"
    elif provider == "openai" and not model:
        model = "gpt-4"
    elif provider == "gemini" and not model:
        model = "gemini-pro"

    return {
        "status": "ok",
        "message": f"COPILOT configurado: {authority}, {provider}/{model}",
        "data": {
            "authority_level": authority,
            "auto_execute": auto_execute,
            "llm_provider": provider,
            "model": model,
            "policy_engine": {"auto_close_threshold": 0.85 if auto_execute else 0.95},
        },
    }
