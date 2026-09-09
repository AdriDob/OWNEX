"""F1 System Assistant — capa principal de comunicación en español."""

from __future__ import annotations

import logging
from typing import Any

from core.f1 import templates  # noqa: N812

logger = logging.getLogger("orion.f1")


class F1Assistant:
    """Asistente principal del sistema. Habla en español, 3 niveles de detalle."""

    def __init__(self, user_name: str = "Adriel") -> None:
        self._user_name = user_name
        self._history: list[dict[str, Any]] = []

    @property
    def user_name(self) -> str:
        return self._user_name

    def greet(self) -> str:
        return templates.saludo(self._user_name)

    def daily_briefing(self, data: dict[str, Any]) -> str:
        lines = [
            templates.saludo(self._user_name),
            "",
            templates.resumen_diario(data),
            "",
            templates.estado_sistema(data),
        ]
        revenue = data.get("revenue_today", 0)
        if revenue and revenue > 0:
            lines.extend(["", templates.revenue_actual(data)])
        acciones = data.get("suggestions", [])
        if acciones:
            lines.extend(["", templates.sugerencias(acciones)])
        lines.extend(["", templates.pie()])
        self._history.append({"type": "daily_briefing", "data": data})
        return "\n".join(lines)

    def status(self, data: dict[str, Any], detail: int = 1) -> str:
        lines = [templates.estado_sistema(data)]
        if detail >= 2:
            lines.extend(["", templates.resumen_diario(data)])
        if detail >= 3:
            lines.append(f"\n📊 Datos completos: {data}")
        self._history.append({"type": "status", "detail": detail})
        return "\n".join(lines)

    def revenue(self, data: dict[str, Any], detail: int = 1) -> str:
        lines = [templates.revenue_actual(data)]
        if detail >= 2:
            metrics = data.get("metrics", {})
            if metrics:
                bounty = metrics.get("bounty", {})
                trading = metrics.get("trading", {})
                lines.append(
                    f"\n📈 Detalle:\n"
                    f"  Hallazgos: {bounty.get('findings_total', 0)} "
                    f"({bounty.get('findings_critical', 0)} críticos, "
                    f"{bounty.get('findings_high', 0)} altos)\n"
                    f"  Trades: {trading.get('total_trades', 0)} "
                    f"(win rate: {trading.get('win_rate', 0)}%)"
                )
        if detail >= 3:
            lines.append(f"\n🔍 Debug:\n{data}")
        self._history.append({"type": "revenue", "detail": detail})
        return "\n".join(lines)

    def alert(self, alert_type: str, title: str, detail: str) -> str:
        if alert_type == "critical":
            msg = templates.alerta_critica(title, detail)
        elif alert_type == "warning":
            msg = templates.alerta_advertencia(title, detail)
        else:
            msg = templates.alerta_info(title, detail)
        self._history.append({"type": "alert", "alert_type": alert_type, "title": title})
        return msg

    def max_revenue_result(self, resultado: dict[str, Any]) -> str:
        msg = templates.max_revenue_resultado(resultado)
        self._history.append({"type": "max_revenue", "data": resultado})
        return msg

    def celebrate(self, message: str) -> str:
        msg = f"🎉 {message}"
        self._history.append({"type": "celebrate", "message": message})
        return msg

    def ask(self, question: str, context: str = "") -> str:
        lines = [f"🤔 {question}"]
        if context:
            lines.insert(0, context)
        lines.append("\n¿Qué querés hacer?")
        return "\n".join(lines)

    def tell(self, message: str, detail: int = 1) -> str:
        self._history.append({"type": "tell", "detail": detail, "message": message[:100]})
        return message

    def get_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def clear_history(self) -> None:
        self._history.clear()


_F1: F1Assistant | None = None


def get_f1() -> F1Assistant:
    global _F1
    if _F1 is None:
        _F1 = F1Assistant()
    return _F1
