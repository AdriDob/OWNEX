from __future__ import annotations

import logging
from typing import Any

from core.financial_intelligence.models import F1Message, Opportunity, RiskPolicy

logger = logging.getLogger("orion.financial_intelligence.f1")


PHRASES: dict[str, list[str]] = {
    "greeting": [
        "¡Bienvenido, capitán! F1 en línea.",
        "Sistema listo. ¿Qué exploramos hoy?",
        "F1 reportándose. Todo en orden.",
    ],
    "opportunity_high": [
        "¡Oportunidad de alto valor detectada!",
        "Esto luce prometedor. ¿Lo revisamos?",
        "Señal fuerte detectada en el radar.",
    ],
    "risk_warning": [
        "¡Cuidado con ese drawdown!",
        "Riesgo elevado. Sugiero precaución.",
        "Los números no mienten: esto es riesgoso.",
    ],
    "success": [
        "¡Buen trabajo! Otra operación exitosa.",
        "Resultado positivo. El sistema funciona.",
        "Bien hecho. Esto suma al patrimonio.",
    ],
    "confirmation": [
        "Operación requiere confirmación.",
        "¿Confirmás esta acción?",
        "Necesito tu OK antes de continuar.",
    ],
    "daily_briefing": [
        "Resumen diario listo. Acá va.",
        "Tu briefing financiero del día.",
    ],
}


class F1Assistant:
    """F1 — friendly retro robot assistant for financial intelligence.

    F1 explains recommendations, warns about risks, celebrates wins,
    and requests user confirmation for high-risk operations.
    """

    def __init__(self, risk_policy: RiskPolicy | None = None):
        self._messages: list[F1Message] = []
        self._risk_policy = risk_policy or RiskPolicy()
        self._persona = {
            "name": "F1",
            "style": "retro_robot",
            "tone": "friendly_cautious",
        }

    def greet(self) -> F1Message:
        return self._say("info", "F1 Online", self._pick("greeting"), "🤖")

    def explain_opportunity(self, opp: Opportunity, rank: int = 1) -> F1Message:
        template = self._pick("opportunity_high") if opp.priority_score > 0.6 else self._pick("daily_briefing")
        body = (
            f"{template}\n\n"
            f"**{opp.label}** (fuente: {opp.source})\n"
            f"- Valor esperado: ${opp.expected_value:,.2f}\n"
            f"- Score: {opp.priority_score:.2f}\n"
            f"- Riesgo: {opp.risk_score:.2f}\n"
            f"- Confianza del modelo: {opp.model_confidence:.0%}\n"
            f"- Ventana estimada: {opp.estimated_time_to_payout_days:.0f} días\n"
        )
        if opp.reasoning:
            body += f"\n{opp.reasoning}\n"
        if opp.rejected_reasons:
            body += "\n⚠️ Motivos de rechazo:\n" + "\n".join(f"- {r}" for r in opp.rejected_reasons)
        return self._say("info", f"Oportunidad #{rank}: {opp.label}", body, "📈")

    def warn_risk(self, title: str, details: str) -> F1Message:
        return self._say("risk", title, f"{self._pick('risk_warning')}\n\n{details}", "⚠️")

    def celebrate_success(self, label: str, amount: float) -> F1Message:
        return self._say(
            "success", "Operación Exitosa", f"{self._pick('success')}\n\n**{label}**: +${amount:,.2f}", "🎉"
        )

    def request_confirmation(self, title: str, body: str, action_payload: dict[str, Any] | None = None) -> F1Message:
        return self._say(
            "confirmation",
            title,
            f"{self._pick('confirmation')}\n\n{body}",
            "🤔",
            requires_action=True,
            action_label="Confirmar",
            action_payload=action_payload or {},
        )

    def daily_briefing(
        self, opportunities: list[Opportunity], portfolio_value: float, risk_status: dict[str, Any]
    ) -> F1Message:
        lines = [self._pick("daily_briefing"), ""]
        lines.append(f"**Portfolio**: ${portfolio_value:,.2f}")
        lines.append(f"**Drawdown**: {risk_status.get('drawdown', 0):.1%}")
        lines.append(f"**Daily loss**: {risk_status.get('daily_loss', 0):.1%}")
        if opportunities:
            lines.append("")
            lines.append("**Top opportunities:**")
            for i, opp in enumerate(opportunities[:3], 1):
                lines.append(f"{i}. {opp.label} — ${opp.expected_value:,.0f} (score: {opp.priority_score:.2f})")
        return self._say("info", "Briefing Diario", "\n".join(lines), "📋")

    def get_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        return [m.to_dict() for m in self._messages[-limit:]]

    def _say(
        self,
        category: str,
        title: str,
        body: str,
        emoji: str = "",
        requires_action: bool = False,
        action_label: str = "",
        action_payload: dict[str, Any] | None = None,
    ) -> F1Message:
        msg = F1Message(
            category=category,
            title=title,
            body=body,
            emoji=emoji,
            requires_action=requires_action,
            action_label=action_label,
            action_payload=action_payload or {},
        )
        self._messages.append(msg)
        logger.info("[F1] %s — %s", category.upper(), title)
        return msg

    @staticmethod
    def _pick(key: str) -> str:
        import random

        return random.choice(PHRASES.get(key, [""]))
