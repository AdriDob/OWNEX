"""Risk Engine — assesses financial risk across multiple dimensions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.capital.risk")


@dataclass
class RiskFactor:
    name: str
    score: float  # 0-100, higher = riskier
    description: str
    weight: float = 1.0


@dataclass
class RiskAssessment:
    score: float  # 0-100 overall risk score
    level: str  # critical, high, medium, low
    factors: dict[str, RiskFactor] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    timestamp: str = ""


class RiskEngine:
    """Assesses financial risk across multiple dimensions."""

    def __init__(self) -> None:
        self._weights = {
            "concentration": 0.25,
            "liquidity": 0.20,
            "platform": 0.20,
            "counterparty": 0.15,
            "currency": 0.10,
            "crypto_exposure": 0.05,
            "income_concentration": 0.05,
        }

    def assess_risk(
        self,
        capital_usd: float = 0,
        income_sources: list[dict] | None = None,
        platform_exposure: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Assess overall financial risk."""
        income_sources = income_sources or []
        platform_exposure = platform_exposure or {}

        factors = {}

        # Concentration risk
        conc_score, conc_desc = self._assess_concentration(platform_exposure, capital_usd)
        factors["concentration"] = RiskFactor("concentration", conc_score, conc_desc, 0.25)

        # Liquidity risk
        liq_score, liq_desc = self._assess_liquidity(capital_usd)
        factors["liquidity"] = RiskFactor("liquidity", liq_score, liq_desc, 0.20)

        # Platform risk
        plat_score, plat_desc = self._assess_platform_risk(platform_exposure)
        factors["platform"] = RiskFactor("platform", plat_score, plat_desc, 0.20)

        # Counterparty risk
        cp_score, cp_desc = self._assess_counterparty(platform_exposure)
        factors["counterparty"] = RiskFactor("counterparty", cp_score, cp_desc, 0.15)

        # Currency risk
        curr_score, curr_desc = self._assess_currency_risk()
        factors["currency"] = RiskFactor("currency", curr_score, curr_desc, 0.10)

        # Crypto exposure
        crypto_score, crypto_desc = self._assess_crypto_exposure()
        factors["crypto_exposure"] = RiskFactor("crypto_exposure", crypto_score, crypto_desc, 0.05)

        # Income concentration
        inc_score, inc_desc = self._assess_income_concentration(income_sources)
        factors["income_concentration"] = RiskFactor("income_concentration", inc_score, inc_desc, 0.05)

        # Calculate weighted score
        total_score = sum(f.score * f.weight for f in factors.values())
        total_weight = sum(f.weight for f in factors.values())
        overall_score = round(total_score / total_weight if total_weight > 0 else 0, 1)

        # Determine level
        if overall_score >= 70:
            level = "critical"
        elif overall_score >= 50:
            level = "high"
        elif overall_score >= 30:
            level = "medium"
        else:
            level = "low"

        # Generate recommendations
        recommendations = self._generate_recommendations(factors, overall_score)

        assessment = RiskAssessment(
            score=overall_score,
            level=level,
            factors={k: v for k, v in factors.items()},
            recommendations=recommendations,
            timestamp=datetime.now(UTC).isoformat(),
        )

        return assessment.__dict__

    def _assess_concentration(self, exposure: dict[str, float], capital: float) -> tuple[float, str]:
        if not exposure or capital <= 0:
            return 0.0, "Sin exposición significativa"
        max_single = max(exposure.values()) if exposure else 0
        pct = (max_single / capital * 100) if capital > 0 else 0
        if pct > 50:
            return 90.0, f"Concentración crítica: {pct:.1f}% en una sola plataforma"
        elif pct > 30:
            return 60.0, f"Concentración alta: {pct:.1f}% en una sola plataforma"
        elif pct > 15:
            return 30.0, f"Concentración moderada: {pct:.1f}%"
        return 10.0, f"Concentración baja: {pct:.1f}%"

    def _assess_liquidity(self, capital: float) -> tuple[float, str]:
        if capital <= 0:
            return 80.0, "Sin capital líquido"
        elif capital < 1000:
            return 70.0, "Liquidez muy baja (<$1k)"
        elif capital < 5000:
            return 40.0, "Liquidez baja (<$5k)"
        elif capital < 20000:
            return 20.0, "Liquidez moderada (<$20k)"
        return 5.0, "Buena liquidez"

    def _assess_platform_risk(self, exposure: dict[str, float]) -> tuple[float, str]:
        if not exposure:
            return 10.0, "Sin exposición a plataformas"
        # Risk based on platform types
        risky_platforms = {"crypto_exchange", "defi", "p2p", "unregulated"}
        risk_score = 0.0
        for platform, _amount in exposure.items():
            if any(rp in platform.lower() for rp in risky_platforms):
                risk_score += 20
        risk_score = min(risk_score, 100)
        return risk_score, f"Exposición a {len(exposure)} plataformas"

    def _assess_counterparty(self, exposure: dict[str, float]) -> tuple[float, str]:
        if not exposure:
            return 5.0, "Sin contrapartes"
        return 15.0, f"{len(exposure)} contrapartes activas"

    def _assess_currency_risk(self) -> tuple[float, str]:
        return 15.0, "Exposición mixta USD/ARS/crypto"

    def _assess_crypto_exposure(self) -> tuple[float, str]:
        return 20.0, "Exposición moderada a crypto"

    def _assess_income_concentration(self, sources: list[dict]) -> tuple[float, str]:
        if not sources:
            return 10.0, "Sin fuentes de ingreso registradas"
        total = sum(s.get("amount", 0) for s in sources)
        if total <= 0:
            return 10.0, "Ingresos cero"
        max_pct = max(s.get("amount", 0) / total * 100 for s in sources)
        if max_pct > 80:
            return 80.0, f"Concentración extrema: {max_pct:.1f}% en una fuente"
        elif max_pct > 50:
            return 50.0, f"Concentración alta: {max_pct:.1f}%"
        return 20.0, f"Diversificación aceptable: top={max_pct:.1f}%"

    def _generate_recommendations(self, factors: dict[str, RiskFactor], overall_score: float) -> list[str]:
        recs = []
        if factors.get("concentration", RiskFactor("", 0, "")).score > 50:
            recs.append("Diversificar exposición: reducir concentración en plataforma principal")
        if factors.get("liquidity", RiskFactor("", 0, "")).score > 50:
            recs.append("Aumentar reserva de liquidez: mantener >3 meses de gastos")
        if factors.get("platform", RiskFactor("", 0, "")).score > 50:
            recs.append("Reducir exposición a plataformas de alto riesgo")
        if factors.get("crypto_exposure", RiskFactor("", 0, "")).score > 40:
            recs.append("Limitar exposición crypto a <20% del capital")
        if factors.get("income_concentration", RiskFactor("", 0, "")).score > 50:
            recs.append("Diversificar fuentes de ingreso: buscar al menos 3 streams")
        if not recs:
            recs.append("Perfil de riesgo dentro de parámetros aceptables")
        return recs


_risk_engine: RiskEngine | None = None


def get_risk_engine() -> RiskEngine:
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine
