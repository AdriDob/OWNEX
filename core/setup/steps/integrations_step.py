from __future__ import annotations

from typing import Any

from core.setup.steps import define_step

INTEGRATIONS_SCHEMA: dict[str, Any] = {
    "type": "integration_list",
    "categories": [
        {
            "id": "platform",
            "label": "Plataformas Bug Bounty",
            "integrations": ["hackerone", "bugcrowd", "intigriti", "immunefi"],
        },
        {
            "id": "ai",
            "label": "Inteligencia Artificial",
            "integrations": ["openai", "gemini", "ollama"],
        },
        {
            "id": "messaging",
            "label": "Mensajería",
            "integrations": ["telegram", "discord", "gmail", "outlook"],
        },
        {
            "id": "exchange",
            "label": "Exchanges",
            "integrations": ["binance", "coinbase", "kraken"],
        },
    ],
}


@define_step(
    step_id="integrations",
    label="Integraciones",
    description="Conectar servicios externos (APIs, exchanges, mensajería)",
    icon="plug",
    order=4,
    required=False,
    schema=INTEGRATIONS_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    integrations = state.get("integrations", {})
    if not isinstance(integrations, dict):
        integrations = {}

    try:
        from core.integrations.registry import init_integration_registry

        registry = init_integration_registry()
        registry.refresh()
        summary = registry.summary()
        by_status = summary.get("by_status", {})

        pending_manual = _check_pending(registry, summary)

        return {
            "status": "ok",
            "message": f"{summary['total']} integraciones — {by_status.get('connected', 0)} conectadas, {len(pending_manual)} pendientes manual",
            "data": {
                "total": summary["total"],
                "connected": by_status.get("connected", 0),
                "disconnected": by_status.get("disconnected", 0),
                "error": by_status.get("error", 0),
                "pending_manual": pending_manual,
                "integrations": integrations,
                "registry_summary": summary,
            },
        }
    except Exception as exc:
        return {
            "status": "warning",
            "message": f"No se pudieron verificar integraciones: {exc}",
            "data": {"integrations": integrations, "error": str(exc)},
        }


def _check_pending(registry: object, summary: dict[str, Any]) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    targets: list[tuple[str, str, str, list[str]]] = [
        ("hackerone", "HackerOne API", "platform", ["HACKERONE_API_USERNAME", "HACKERONE_API_TOKEN"]),
        ("telegram", "Telegram Bot", "messaging", ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]),
    ]
    for name, label, category, env_vars in targets:
        for integ in summary.get("integrations", []):
            if integ.get("name") == name and integ.get("status") == "disconnected":
                pending.append(
                    {
                        "integration": name,
                        "label": label,
                        "category": category,
                        "status": "pendiente manual",
                        "required_env": env_vars,
                    }
                )
                break
    return pending
