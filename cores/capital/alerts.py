"""Capital Alert Engine — intelligent alerts for capital events."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.capital.alerts")


class AlertSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertCategory(StrEnum):
    RUNWAY = "runway"
    RISK = "risk"
    CASH_FLOW = "cash_flow"
    INCOME = "income"
    PAYOUT = "payout"
    DIVERSIFICATION = "diversification"
    GOAL = "goal"
    SECURITY = "security"


@dataclass
class CapitalAlert:
    id: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    action_required: bool = False
    action_url: str | None = None
    action_label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    acknowledged_at: str | None = None
    dismissed_at: str | None = None


@dataclass
class AlertRule:
    id: str
    name: str
    category: AlertCategory
    severity: AlertSeverity
    condition: str  # expression to evaluate
    cooldown_seconds: int = 3600  # minimum time between same alert
    enabled: bool = True


class CapitalAlertEngine:
    """Generates and manages capital-related alerts."""

    def __init__(self) -> None:
        self._alerts: dict[str, CapitalAlert] = {}
        self._rules: dict[str, AlertRule] = {}
        self._last_triggered: dict[str, datetime] = {}
        self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load default alert rules."""
        rules = [
            AlertRule(
                id="runway_critical",
                name="Runway Crítico (<1 mes)",
                category=AlertCategory.RUNWAY,
                severity=AlertSeverity.CRITICAL,
                condition="runway_months < 1",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="runway_warning",
                name="Runway Bajo (<3 meses)",
                category=AlertCategory.RUNWAY,
                severity=AlertSeverity.HIGH,
                condition="runway_months < 3 and runway_months >= 1",
                cooldown_seconds=43200,  # 12 hours
            ),
            AlertRule(
                id="runway_healthy",
                name="Runway Saludable (>6 meses)",
                category=AlertCategory.RUNWAY,
                severity=AlertSeverity.INFO,
                condition="runway_months >= 6",
                cooldown_seconds=604800,  # weekly
            ),
            AlertRule(
                id="risk_critical",
                name="Riesgo Crítico",
                category=AlertCategory.RISK,
                severity=AlertSeverity.CRITICAL,
                condition="risk_score >= 70",
                cooldown_seconds=21600,  # 6 hours
            ),
            AlertRule(
                id="risk_high",
                name="Riesgo Alto",
                category=AlertCategory.RISK,
                severity=AlertSeverity.HIGH,
                condition="risk_score >= 50 and risk_score < 70",
                cooldown_seconds=43200,  # 12 hours
            ),
            AlertRule(
                id="cash_flow_negative",
                name="Flujo de Caja Negativo",
                category=AlertCategory.CASH_FLOW,
                severity=AlertSeverity.HIGH,
                condition="net_monthly_cashflow < 0",
                cooldown_seconds=21600,  # 6 hours
            ),
            AlertRule(
                id="income_drop",
                name="Caída de Ingresos >30%",
                category=AlertCategory.INCOME,
                severity=AlertSeverity.HIGH,
                condition="income_30d_change < -30",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="payout_delayed",
                name="Payout Retrasado",
                category=AlertCategory.PAYOUT,
                severity=AlertSeverity.MEDIUM,
                condition="pending_payout_age_days > 60",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="payout_received",
                name="Payout Recibido",
                category=AlertCategory.PAYOUT,
                severity=AlertSeverity.INFO,
                condition="new_payout_received",
                cooldown_seconds=3600,  # hourly
            ),
            AlertRule(
                id="concentration_critical",
                name="Concentración Crítica >60%",
                category=AlertCategory.DIVERSIFICATION,
                severity=AlertSeverity.CRITICAL,
                condition="top_source_pct > 60",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="concentration_high",
                name="Concentración Alta >30%",
                category=AlertCategory.DIVERSIFICATION,
                severity=AlertSeverity.HIGH,
                condition="top_source_pct > 30",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="goal_milestone",
                name="Meta Financiera Alcanzada",
                category=AlertCategory.GOAL,
                severity=AlertSeverity.INFO,
                condition="goal_progress >= 100",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="goal_behind",
                name="Meta Financiera Atrasada",
                category=AlertCategory.GOAL,
                severity=AlertSeverity.HIGH,
                condition="goal_progress < expected_progress and goal_progress < 100",
                cooldown_seconds=86400,  # daily
            ),
            AlertRule(
                id="payout_sync_failed",
                name="Fallo de Sincronización de Payouts",
                category=AlertCategory.SECURITY,
                severity=AlertSeverity.HIGH,
                condition="payout_sync_consecutive_failures >= 3",
                cooldown_seconds=21600,  # 6 hours
            ),
            AlertRule(
                id="crypto_exposure_high",
                name="Exposición Crypto Alta >30%",
                category=AlertCategory.RISK,
                severity=AlertSeverity.HIGH,
                condition="crypto_exposure_pct > 30",
                cooldown_seconds=43200,  # 12 hours
            ),
            AlertRule(
                id="platform_down",
                name="Plataforma Caída (Sync Fallido)",
                category=AlertCategory.SECURITY,
                severity=AlertSeverity.HIGH,
                condition="platform_sync_health == 'failed'",
                cooldown_seconds=21600,  # 6 hours
            ),
        ]
        for rule in rules:
            self._rules[rule.id] = rule

    def evaluate(self, context: dict[str, Any]) -> list[CapitalAlert]:
        """Evaluate all rules against context and return triggered alerts."""
        triggered = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if self._evaluate_condition(rule.condition, context):
                if self._should_trigger(rule):
                    alert = self._create_alert(rule, context)
                    triggered.append(alert)
        return triggered

    def _evaluate_condition(self, condition: str, context: dict[str, Any]) -> bool:
        """Safely evaluate a condition expression."""
        try:
            # Simple expression evaluator for basic comparisons
            # In production, use a proper expression evaluator
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

    def _should_trigger(self, rule: AlertRule) -> bool:
        """Check if rule should trigger based on cooldown."""
        last = self._last_triggered.get(rule.id)
        if not last:
            return True
        elapsed = (datetime.now(UTC) - last).total_seconds()
        return elapsed >= rule.cooldown_seconds

    def _create_alert(self, rule: AlertRule, context: dict[str, Any]) -> CapitalAlert:
        alert = CapitalAlert(
            id=f"{rule.id}_{int(datetime.now(UTC).timestamp())}",
            category=rule.category,
            severity=rule.severity,
            title=rule.name,
            message=self._format_message(rule, context),
            action_required=rule.severity in (AlertSeverity.CRITICAL, AlertSeverity.HIGH),
            action_url=self._get_action_url(rule.category),
            action_label=self._get_action_label(rule.category),
            metadata={"rule_id": rule.id, "context": context},
        )
        self._alerts[alert.id] = alert
        self._last_triggered[rule.id] = datetime.now(UTC)
        return alert

    def _format_message(self, rule: AlertRule, context: dict[str, Any]) -> str:
        """Format alert message with context values."""
        messages = {
            "runway_critical": f"Runway crítico: {context.get('runway_months', 0):.1f} meses restantes",
            "runway_warning": f"Runway bajo: {context.get('runway_months', 0):.1f} meses restantes",
            "runway_healthy": f"Runway saludable: {context.get('runway_months', 0):.1f} meses",
            "risk_critical": f"Score de riesgo crítico: {context.get('risk_score', 0)}/100",
            "risk_high": f"Score de riesgo alto: {context.get('risk_score', 0)}/100",
            "cash_flow_negative": f"Flujo de caja negativo: ${context.get('net_monthly_cashflow', 0):,.0f}/mes",
            "income_drop": f"Ingresos cayeron {context.get('income_30d_change', 0):.1f}% en 30 días",
            "payout_delayed": f"Payout pendiente por {context.get('pending_payout_age_days', 0)} días",
            "payout_received": f"Nuevo payout recibido: ${context.get('payout_amount', 0):,.2f}",
            "concentration_critical": f"Concentración crítica: {context.get('top_source_pct', 0):.1f}% en una fuente",
            "concentration_high": f"Concentración alta: {context.get('top_source_pct', 0):.1f}% en una fuente",
            "goal_milestone": f"Meta financiera alcanzada: {context.get('goal_name', 'Meta')}",
            "goal_behind": f"Meta atrasada: {context.get('goal_name', 'Meta')} al {context.get('goal_progress', 0):.1f}%",
            "payout_sync_failed": f"Sincronización de payouts fallida {context.get('payout_sync_consecutive_failures', 0)} veces consecutivas",
            "crypto_exposure_high": f"Exposición crypto alta: {context.get('crypto_exposure_pct', 0):.1f}%",
            "platform_down": f"Plataforma {context.get('platform_name', 'desconocida')} con sync fallido",
        }
        return messages.get(f"{rule.category.value}_{rule.severity.value}", rule.name)

    def _get_action_url(self, category: AlertCategory) -> str:
        urls = {
            AlertCategory.RUNWAY: "/capital?tab=runway",
            AlertCategory.RISK: "/capital?tab=risk",
            AlertCategory.CASH_FLOW: "/capital?tab=overview",
            AlertCategory.INCOME: "/capital?tab=overview",
            AlertCategory.PAYOUT: "/capital?tab=overview",
            AlertCategory.DIVERSIFICATION: "/capital?tab=diversification",
            AlertCategory.GOAL: "/capital?tab=goals",
            AlertCategory.SECURITY: "/settings?tab=security",
        }
        return urls.get(category, "/capital")

    def _get_action_label(self, category: AlertCategory) -> str:
        labels = {
            AlertCategory.RUNWAY: "Ver Runway",
            AlertCategory.RISK: "Ver Riesgo",
            AlertCategory.CASH_FLOW: "Ver Flujo de Caja",
            AlertCategory.INCOME: "Ver Ingresos",
            AlertCategory.PAYOUT: "Ver Payouts",
            AlertCategory.DIVERSIFICATION: "Ver Diversificación",
            AlertCategory.GOAL: "Ver Metas",
            AlertCategory.SECURITY: "Ver Seguridad",
        }
        return labels.get(category, "Ver Detalles")

    # Public API
    def get_alerts(
        self,
        severity: AlertSeverity | None = None,
        category: AlertCategory | None = None,
        unacknowledged_only: bool = True,
        limit: int = 50,
    ) -> list[CapitalAlert]:
        """Get filtered alerts."""
        alerts = list(self._alerts.values())
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged_at]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if category:
            alerts = [a for a in alerts if a.category == category]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].acknowledged_at = datetime.now(UTC).isoformat()
            return True
        return False

    def dismiss(self, alert_id: str) -> bool:
        """Dismiss an alert."""
        if alert_id in self._alerts:
            self._alerts[alert_id].dismissed_at = datetime.now(UTC).isoformat()
            return True
        return False

    def get_unread_count(self) -> int:
        """Get count of unread alerts."""
        return len([a for a in self._alerts.values() if not a.acknowledged_at and not a.dismissed_at])

    def get_alert(self, alert_id: str) -> CapitalAlert | None:
        return self._alerts.get(alert_id)

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            return True
        return False

    def get_rules(self) -> list[AlertRule]:
        return list(self._rules.values())


_alert_engine: CapitalAlertEngine | None = None


def get_alert_engine() -> CapitalAlertEngine:
    global _alert_engine
    if _alert_engine is None:
        _alert_engine = CapitalAlertEngine()
    return _alert_engine
