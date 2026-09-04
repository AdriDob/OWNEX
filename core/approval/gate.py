"""Approval Gate — Configurable autonomy policies for OWNEX.

LITE:    Todo externo requiere aprobación explícita (usuario novato / máximo control)
FULL:    Auto-aprueba si trust_level >= HIGH Y amount <= $100 Y platform allowed
CAPITAL: Solo acciones de bajo riesgo auto-aprueban; financieras/alto impacto siempre requieren aprobación
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.approval.gate")


class AutonomyPolicy(StrEnum):
    """Niveles de autonomía configurables."""

    LITE = "lite"  # Todo requiere aprobación
    FULL = "full"  # Auto-aprueba bajo riesgo
    CAPITAL = "capital"  # Solo bajo riesgo; financiero siempre aprueba


class RiskLevel(StrEnum):
    """Nivel de riesgo de una acción."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionType(StrEnum):
    """Tipos de acción que pueden requerir aprobación."""

    SUBMIT_BOUNTY = "submit_bounty"
    SUBMIT_REPORT = "submit_report"
    ACCEPT_WORK = "accept_work"
    CREATE_PR = "create_pr"
    DEPLOY_CODE = "deploy_code"
    FINANCIAL_TRANSACTION = "financial_transaction"
    CREDENTIAL_CHANGE = "credential_change"
    PLATFORM_AUTH = "platform_auth"
    EXTERNAL_API_CALL = "external_api_call"
    WORK_SUBMISSION = "work_submission"


@dataclass
class ApprovalRule:
    """Regla de aprobación para un tipo de acción."""

    action_type: ActionType
    risk_level: RiskLevel
    max_auto_amount_usd: float = 0.0
    required_trust_level: str = "HIGH"  # UNKNOWN, LOW, MEDIUM, HIGH, CRITICAL
    allowed_platforms: list[str] = field(default_factory=list)
    blocked_platforms: list[str] = field(default_factory=list)
    requires_human_review: bool = True


@dataclass
class ApprovalPolicyConfig:
    """Configuración completa de una política de autonomía."""

    policy: AutonomyPolicy
    name: str
    description: str
    rules: dict[ActionType, ApprovalRule] = field(default_factory=dict)
    default_max_auto_amount_usd: float = 0.0
    default_required_trust_level: str = "HIGH"
    global_requires_human_review: bool = True
    allowed_platforms: list[str] = field(default_factory=list)
    blocked_platforms: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy.value,
            "name": self.name,
            "description": self.description,
            "rules": {k.value: asdict(v) for k, v in self.rules.items()},
            "default_max_auto_amount_usd": self.default_max_auto_amount_usd,
            "default_required_trust_level": self.default_required_trust_level,
            "global_requires_human_review": self.global_requires_human_review,
            "allowed_platforms": self.allowed_platforms,
            "blocked_platforms": self.blocked_platforms,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalPolicyConfig:
        rules = {}
        for k, v in data.get("rules", {}).items():
            rules[ActionType(k)] = ApprovalRule(**v)
        return cls(
            policy=AutonomyPolicy(data["policy"]),
            name=data["name"],
            description=data["description"],
            rules=rules,
            default_max_auto_amount_usd=data.get("default_max_auto_amount_usd", 0.0),
            default_required_trust_level=data.get("default_required_trust_level", "HIGH"),
            global_requires_human_review=data.get("global_requires_human_review", True),
            allowed_platforms=data.get("allowed_platforms", []),
            blocked_platforms=data.get("blocked_platforms", []),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )


@dataclass
class ApprovalDecision:
    """Resultado de una decisión de aprobación."""

    approved: bool
    reason: str
    policy: AutonomyPolicy
    action_type: ActionType
    platform: str
    amount_usd: float
    risk_level: RiskLevel
    trust_level: str
    requires_human_review: bool
    auto_approval_allowed: bool
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


# ── Default Policy Configurations ────────────────────────────────

DEFAULT_LITE_POLICY = ApprovalPolicyConfig(
    policy=AutonomyPolicy.LITE,
    name="LITE - Maximum Control",
    description="Todo requiere aprobación explícita. Para usuarios que quieren control total.",
    global_requires_human_review=True,
    default_max_auto_amount_usd=0.0,
    default_required_trust_level="CRITICAL",
    rules={
        ActionType.SUBMIT_BOUNTY: ApprovalRule(
            action_type=ActionType.SUBMIT_BOUNTY,
            risk_level=RiskLevel.HIGH,
            max_auto_amount_usd=0.0,
            required_trust_level="CRITICAL",
            requires_human_review=True,
        ),
        ActionType.SUBMIT_REPORT: ApprovalRule(
            action_type=ActionType.SUBMIT_REPORT,
            risk_level=RiskLevel.HIGH,
            max_auto_amount_usd=0.0,
            required_trust_level="CRITICAL",
            requires_human_review=True,
        ),
        ActionType.ACCEPT_WORK: ApprovalRule(
            action_type=ActionType.ACCEPT_WORK,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.CREATE_PR: ApprovalRule(
            action_type=ActionType.CREATE_PR,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.WORK_SUBMISSION: ApprovalRule(
            action_type=ActionType.WORK_SUBMISSION,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
    },
)

DEFAULT_FULL_POLICY = ApprovalPolicyConfig(
    policy=AutonomyPolicy.FULL,
    name="FULL - Balanced Autonomy",
    description="Auto-aprueba acciones de bajo riesgo con trust alto. Balance entre control y velocidad.",
    global_requires_human_review=False,
    default_max_auto_amount_usd=100.0,
    default_required_trust_level="HIGH",
    allowed_platforms=["hackerone", "bugcrowd", "intigriti", "yeswehack", "opire", "issuehunt", "freelancer", "algora"],
    rules={
        ActionType.SUBMIT_BOUNTY: ApprovalRule(
            action_type=ActionType.SUBMIT_BOUNTY,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=200.0,
            required_trust_level="HIGH",
            allowed_platforms=["hackerone", "bugcrowd", "intigriti", "yeswehack"],
            requires_human_review=False,
        ),
        ActionType.SUBMIT_REPORT: ApprovalRule(
            action_type=ActionType.SUBMIT_REPORT,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=False,
        ),
        ActionType.ACCEPT_WORK: ApprovalRule(
            action_type=ActionType.ACCEPT_WORK,
            risk_level=RiskLevel.LOW,
            max_auto_amount_usd=100.0,
            required_trust_level="MEDIUM",
            requires_human_review=False,
        ),
        ActionType.CREATE_PR: ApprovalRule(
            action_type=ActionType.CREATE_PR,
            risk_level=RiskLevel.LOW,
            max_auto_amount_usd=0.0,
            required_trust_level="MEDIUM",
            requires_human_review=False,
        ),
        ActionType.WORK_SUBMISSION: ApprovalRule(
            action_type=ActionType.WORK_SUBMISSION,
            risk_level=RiskLevel.LOW,
            max_auto_amount_usd=100.0,
            required_trust_level="MEDIUM",
            requires_human_review=False,
        ),
        ActionType.FINANCIAL_TRANSACTION: ApprovalRule(
            action_type=ActionType.FINANCIAL_TRANSACTION,
            risk_level=RiskLevel.HIGH,
            max_auto_amount_usd=50.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
    },
)

DEFAULT_CAPITAL_POLICY = ApprovalPolicyConfig(
    policy=AutonomyPolicy.CAPITAL,
    name="CAPITAL - Revenue-First Autonomy",
    description="Solo acciones de bajo riesgo auto-aprueban. Acciones financieras/de alto impacto siempre requieren aprobación.",
    global_requires_human_review=True,
    default_max_auto_amount_usd=50.0,
    default_required_trust_level="HIGH",
    blocked_platforms=[],
    rules={
        ActionType.SUBMIT_BOUNTY: ApprovalRule(
            action_type=ActionType.SUBMIT_BOUNTY,
            risk_level=RiskLevel.HIGH,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.SUBMIT_REPORT: ApprovalRule(
            action_type=ActionType.SUBMIT_REPORT,
            risk_level=RiskLevel.HIGH,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.ACCEPT_WORK: ApprovalRule(
            action_type=ActionType.ACCEPT_WORK,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=100.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.CREATE_PR: ApprovalRule(
            action_type=ActionType.CREATE_PR,
            risk_level=RiskLevel.LOW,
            max_auto_amount_usd=0.0,
            required_trust_level="MEDIUM",
            requires_human_review=False,
        ),
        ActionType.DEPLOY_CODE: ApprovalRule(
            action_type=ActionType.DEPLOY_CODE,
            risk_level=RiskLevel.HIGH,
            max_auto_amount_usd=0.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.WORK_SUBMISSION: ApprovalRule(
            action_type=ActionType.WORK_SUBMISSION,
            risk_level=RiskLevel.MEDIUM,
            max_auto_amount_usd=50.0,
            required_trust_level="HIGH",
            requires_human_review=True,
        ),
        ActionType.FINANCIAL_TRANSACTION: ApprovalRule(
            action_type=ActionType.FINANCIAL_TRANSACTION,
            risk_level=RiskLevel.CRITICAL,
            max_auto_amount_usd=0.0,
            required_trust_level="CRITICAL",
            requires_human_review=True,
        ),
    },
)


POLICY_PRESETS: dict[AutonomyPolicy, ApprovalPolicyConfig] = {
    AutonomyPolicy.LITE: DEFAULT_LITE_POLICY,
    AutonomyPolicy.FULL: DEFAULT_FULL_POLICY,
    AutonomyPolicy.CAPITAL: DEFAULT_CAPITAL_POLICY,
}


def _trust_level_order(trust: str) -> int:
    """Orden de niveles de trust para comparación."""
    order = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    return order.get(trust.upper(), 0)


def _risk_level_order(risk: RiskLevel | str) -> int:
    """Orden de niveles de riesgo para comparación."""
    if isinstance(risk, str):
        risk = RiskLevel(risk.lower())
    order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
    return order.get(risk, 0)


# ── Approval Gate Engine ───────────────────────────────────────


class ApprovalGate:
    """Motor de decisiones de aprobación basado en política configurable."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_path = Path(config_path or os.path.expanduser("~/.ownex/approval_policy.json"))
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config: ApprovalPolicyConfig = self._load_config()

    def _load_config(self) -> ApprovalPolicyConfig:
        """Carga configuración desde archivo o usa preset por defecto (FULL)."""
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"[APPROVAL_GATE] Loaded policy: {data['policy']}")
                return ApprovalPolicyConfig.from_dict(data)
            except Exception as e:
                logger.warning(f"[APPROVAL_GATE] Failed to load config: {e}, using FULL default")
        return POLICY_PRESETS[AutonomyPolicy.FULL]

    def _save_config(self) -> None:
        """Guarda configuración actual a archivo."""
        try:
            self._config.updated_at = datetime.now(UTC).isoformat()
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"[APPROVAL_GATE] Saved policy: {self._config.policy.value}")
        except Exception as e:
            logger.error(f"[APPROVAL_GATE] Failed to save config: {e}")

    def set_policy(self, policy: AutonomyPolicy) -> None:
        """Cambia a una política predefinida (LITE/FULL/CAPITAL)."""
        self._config = POLICY_PRESETS[policy]
        self._save_config()
        logger.info(f"[APPROVAL_GATE] Switched to policy: {policy.value}")

    def get_policy(self) -> AutonomyPolicy:
        return self._config.policy

    def get_config(self) -> ApprovalPolicyConfig:
        return self._config

    def update_config(self, **kwargs: Any) -> None:
        """Actualiza configuración de la política actual."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                if key == "policy" and isinstance(value, str):
                    self.set_policy(AutonomyPolicy(value))
                    return
                setattr(self._config, key, value)
        self._save_config()
        logger.info(f"[APPROVAL_GATE] Updated config: {kwargs}")

    def _get_rule(self, action_type: ActionType) -> ApprovalRule:
        """Obtiene la regla para un tipo de acción, o default."""
        return self._config.rules.get(
            action_type,
            ApprovalRule(
                action_type=action_type,
                risk_level=RiskLevel.MEDIUM,
                max_auto_amount_usd=self._config.default_max_auto_amount_usd,
                required_trust_level=self._config.default_required_trust_level,
                allowed_platforms=self._config.allowed_platforms,
                blocked_platforms=self._config.blocked_platforms,
                requires_human_review=self._config.global_requires_human_review,
            ),
        )

    def can_auto_approve(
        self,
        action_type: ActionType | str,
        platform: str,
        amount_usd: float = 0.0,
        trust_level: str = "UNKNOWN",
        risk_level: RiskLevel | str = RiskLevel.MEDIUM,
    ) -> ApprovalDecision:
        """Determina si una acción puede auto-aprobarse según la política actual."""
        if isinstance(action_type, str):
            action_type = ActionType(action_type)
        if isinstance(risk_level, str):
            risk_level = RiskLevel(risk_level.lower())

        rule = self._get_rule(action_type)
        trust_order = _trust_level_order(trust_level)
        required_order = _trust_level_order(rule.required_trust_level)
        risk_order = _risk_level_order(risk_level)

        # Verificaciones de política
        if self._config.policy == AutonomyPolicy.LITE:
            return ApprovalDecision(
                approved=False,
                reason="LITE policy: all actions require explicit human approval",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Verificar plataforma bloqueada
        if platform in self._config.blocked_platforms:
            return ApprovalDecision(
                approved=False,
                reason=f"Platform {platform} is blocked in {self._config.policy.value} policy",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Verificar plataforma permitida (si lista no vacía)
        if self._config.allowed_platforms and platform not in self._config.allowed_platforms:
            return ApprovalDecision(
                approved=False,
                reason=f"Platform {platform} not in allowed list for {self._config.policy.value} policy",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Verificar trust level
        trust_order = _trust_level_order(trust_level)
        required_order = _trust_level_order(rule.required_trust_level)
        if trust_order < required_order:
            return ApprovalDecision(
                approved=False,
                reason=f"Trust level {trust_level} below required {rule.required_trust_level}",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Verificar monto
        max_amount = min(rule.max_auto_amount_usd, self._config.default_max_auto_amount_usd)
        if amount_usd > max_amount and max_amount > 0:
            return ApprovalDecision(
                approved=False,
                reason=f"Amount ${amount_usd:.2f} exceeds auto-approval limit ${max_amount:.2f}",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Verificar riesgo
        if risk_order > _risk_level_order(RiskLevel.MEDIUM):
            return ApprovalDecision(
                approved=False,
                reason=f"Risk level {risk_level.value} exceeds auto-approval threshold",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Verificar si la regla requiere revisión humana
        if rule.requires_human_review or self._config.global_requires_human_review:
            return ApprovalDecision(
                approved=False,
                reason="Action requires human review per policy rules",
                policy=self._config.policy,
                action_type=action_type,
                platform=platform,
                amount_usd=amount_usd,
                risk_level=risk_level,
                trust_level=trust_level,
                requires_human_review=True,
                auto_approval_allowed=False,
            )

        # Todas las verificaciones pasadas → auto-aprobar
        return ApprovalDecision(
            approved=True,
            reason="All policy checks passed",
            policy=self._config.policy,
            action_type=action_type,
            platform=platform,
            amount_usd=amount_usd,
            risk_level=risk_level,
            trust_level=trust_level,
            requires_human_review=False,
            auto_approval_allowed=True,
        )

    def request_approval(
        self,
        action_type: ActionType | str,
        platform: str,
        amount_usd: float = 0.0,
        trust_level: str = "UNKNOWN",
        risk_level: RiskLevel | str = RiskLevel.MEDIUM,
        context: dict[str, Any] | None = None,
    ) -> ApprovalDecision:
        """Solicita decisión de aprobación (para uso en drivers/executors)."""
        decision = self.can_auto_approve(action_type, platform, amount_usd, trust_level, risk_level)

        # Log de la decisión
        logger.info(
            f"[APPROVAL_GATE] {self._config.policy.value} | "
            f"{action_type} | {platform} | ${amount_usd:.2f} | "
            f"trust={trust_level} | risk={risk_level} | "
            f"approved={decision.approved} | reason={decision.reason}"
        )

        return decision


# ── Singleton ───────────────────────────────────────────────────

_approval_gate: ApprovalGate | None = None


def get_approval_gate(config_path: str | Path | None = None) -> ApprovalGate:
    global _approval_gate
    if _approval_gate is None:
        _approval_gate = ApprovalGate(config_path)
    return _approval_gate
