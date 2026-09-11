"""Personal reward & acceptance probability — bounty niches (HIGH_UPSIDE_90D + HIGH_CONFIDENCE_90 plan).

Four probabilities, properly separated:

1. P_VALID       = technical validity (real, reproducible, in scope)
2. P_UNIQUE      = uniqueness (not duplicate, first to report)
3. P_ACCEPT      = program acceptance probability (if valid+unique, will program accept?)
4. P_REWARD      = rewardability (if accepted, will it pay?)

P_SUCCESSFUL_REWARD = P_VALID × P_UNIQUE × P_ACCEPT × P_REWARD

Two-layer model per probability:

1. PRIOR_EXTERNO — weak external prior, used ONLY when no personal outcomes.
   Always labeled PRIOR_EXTERNO, never presented as personal rate.
2. Personal posterior — (wins + alpha * prior) / (n + alpha) updated
   EXCLUSIVELY from verified real outcomes. Hypotheses never count as wins.

Evidence Gate (P6): minimum sample sizes before quoting a rate.
- n == 0 -> NO_EVIDENCE (external prior only, labeled PRIOR_EXTERNO)
- n < 3  -> THIN_EVIDENCE (prior dominates, show range not point estimate)

Confidence intervals: with sufficient samples, compute lower bound.
If lower_bound < threshold, confidence is downgraded.

P_VALID is technical validity ONLY. Scope verification is separate (scope_verified field).

Priors are configurable via config file/env, not hardcoded facts.

Storage: append-only JSONL under OWNEX_DATA_DIR/learning/ — survives
restarts, no DB migration. All stores are path-injectable for tests.

Rule: opportunity != finding != submission != acceptance != reward != PAID.
Only REWARDED with verified payout counts as a win; duplicates and
rejections are losses for probability purposes (they cost human time).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.revenue.reward_probability")

OUTCOMES_FILENAME = "reward_outcomes.jsonl"
FUNNEL_FILENAME = "reward_funnel.jsonl"
ACCEPTANCE_FILENAME = "acceptance_outcomes.jsonl"
ACCEPTANCE_CALIBRATION_FILENAME = "acceptance_calibration.jsonl"
PRIORS_FILENAME = "priors.json"

# Evidence Gate (P6): minimum verified outcomes before quoting a rate.
# n == 0 -> NO_EVIDENCE (external prior only, labeled PRIOR_EXTERNO)
# n < 3  -> THIN_EVIDENCE (prior dominates, show range not point estimate)
MIN_PERSONAL_SAMPLES = 3
LOW_CONFIDENCE_SAMPLES = 10
MEDIUM_CONFIDENCE_SAMPLES = 50
HIGH_CONFIDENCE_SAMPLES = 100

# Bayesian smoothing strength: with n real outcomes, the prior contributes
# ALPHA pseudo-observations. Small enough that 50+ outcomes are user-driven.
PRIOR_STRENGTH = 4.0

# Confidence intervals: Wilson score interval for binomial proportion
CONFIDENCE_LEVEL = 0.95  # 95% CI

# Minimum effective sample for HIGH_CONFIDENCE_90 mode
HIGH_CONFIDENCE_MIN_EFFECTIVE_N = 15


def _data_dir() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data"))


def _load_priors() -> dict[str, Any]:
    """Load priors from config file. Falls back to defaults if not found."""
    path = _data_dir() / "learning" / PRIORS_FILENAME
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("priors: config unreadable, using defaults")
    return {}


def _save_priors(priors: dict[str, Any]) -> None:
    """Save priors to config file."""
    path = _data_dir() / "learning" / PRIORS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(priors, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("priors: failed to save config: %s", exc)


# ── Niche taxonomy ───────────────────────────────────────────────
# Maps OpportunityCategory values onto bounty niches. Initial priority
# (AI/LLM -> Web3 -> API/Auth -> classic) is a STARTING prior only:
# personal outcomes may reorder it at any time.

NICHE_AI_LLM = "ai_llm"
NICHE_WEB3 = "web3"
NICHE_API_AUTH = "api_auth"
NICHE_WEB_CLASSIC = "web_classic"
NICHE_OTHER = "other"

# Initial priority (lower = investigated first). Personal data overrides.
NICHE_PRIORITY = {
    NICHE_AI_LLM: 1,
    NICHE_WEB3: 2,
    NICHE_API_AUTH: 3,
    NICHE_WEB_CLASSIC: 4,
    NICHE_OTHER: 5,
}

_CATEGORY_TO_NICHE: dict[str, str] = {
    "ai_engineering": NICHE_AI_LLM,
    "ml_engineering": NICHE_AI_LLM,
    "llm_engineering": NICHE_AI_LLM,
    "prompt_engineering": NICHE_AI_LLM,
    "ai_evaluation": NICHE_AI_LLM,
    "blockchain_development": NICHE_WEB3,
    "smart_contracts": NICHE_WEB3,
    "api_development": NICHE_API_AUTH,
    "backend": NICHE_API_AUTH,
    "bug_bounty": NICHE_WEB_CLASSIC,
    "security_research": NICHE_WEB_CLASSIC,
    "frontend": NICHE_WEB_CLASSIC,
    "full_stack": NICHE_WEB_CLASSIC,
    "mobile_development": NICHE_WEB_CLASSIC,
}


def niche_for_category(category: str | None) -> str:
    """Map an OpportunityCategory value onto a bounty niche."""
    if not category:
        return NICHE_OTHER
    key = str(category).strip().lower().replace("opportunitycategory.", "")
    return _CATEGORY_TO_NICHE.get(key, NICHE_OTHER)


# ── P1: PRIOR_EXTERNO (weak external prior, labeled, never personal) ──

# Default external priors — CONFIGURABLE via priors.json
# These are WEAK priors for a hunter with zero history.
# Used ONLY as Bayesian prior weight (PRIOR_STRENGTH pseudo-observations),
# never quoted as the user's rate.
DEFAULT_EXTERNAL_PRIORS = {
    "ai_llm": {
        "p_valid": (0.08, 0.20),
        "p_unique": (0.45, 0.65),
        "p_accept": (0.45, 0.65),
        "p_reward": (0.70, 0.90),
        "label": "PRIOR_EXTERNO",
        "source": "market-average-public-programs-no-history",
    },
    "web3": {
        "p_valid": (0.06, 0.15),
        "p_unique": (0.55, 0.75),
        "p_accept": (0.50, 0.70),
        "p_reward": (0.75, 0.95),
        "label": "PRIOR_EXTERNO",
        "source": "market-average-public-programs-no-history",
    },
    "api_auth": {
        "p_valid": (0.08, 0.18),
        "p_unique": (0.35, 0.55),
        "p_accept": (0.45, 0.65),
        "p_reward": (0.80, 0.95),
        "label": "PRIOR_EXTERNO",
        "source": "market-average-public-programs-no-history",
    },
    "web_classic": {
        "p_valid": (0.05, 0.12),
        "p_unique": (0.25, 0.45),
        "p_accept": (0.40, 0.60),
        "p_reward": (0.75, 0.95),
        "label": "PRIOR_EXTERNO",
        "source": "market-average-public-programs-no-history",
    },
    "other": {
        "p_valid": (0.03, 0.10),
        "p_unique": (0.25, 0.45),
        "p_accept": (0.35, 0.55),
        "p_reward": (0.70, 0.90),
        "label": "PRIOR_EXTERNO",
        "source": "market-average-public-programs-no-history",
    },
}


def _load_external_priors() -> dict[str, dict]:
    """Load external priors from config, fallback to defaults."""
    config = _load_priors()
    return config.get("external_priors", DEFAULT_EXTERNAL_PRIORS)


@dataclass(frozen=True, slots=True)
class ExternalPrior:
    """Weak external prior for a niche. Ranges, not false precision."""

    niche: str
    p_valid: tuple[float, float]
    p_unique: tuple[float, float]
    p_accept: tuple[float, float]
    p_reward: tuple[float, float]
    label: str = "PRIOR_EXTERNO"
    source: str = "market-average-public-programs-no-history"


def get_external_prior(niche: str) -> ExternalPrior:
    """Return the weak external prior for a niche (labeled PRIOR_EXTERNO)."""
    priors = _load_external_priors()
    data = priors.get(niche, DEFAULT_EXTERNAL_PRIORS["other"])
    return ExternalPrior(
        niche=niche,
        p_valid=tuple(data["p_valid"]),
        p_unique=tuple(data["p_unique"]),
        p_accept=tuple(data["p_accept"]),
        p_reward=tuple(data["p_reward"]),
        label=data.get("label", "PRIOR_EXTERNO"),
        source=data.get("source", "market-average-public-programs-no-history"),
    )


def prior_midpoint(prior: ExternalPrior) -> float:
    """Midpoint of the implied end-to-end reward probability (prior only)."""
    v = (prior.p_valid[0] + prior.p_valid[1]) / 2.0
    u = (prior.p_unique[0] + prior.p_unique[1]) / 2.0
    a = (prior.p_accept[0] + prior.p_accept[1]) / 2.0
    r = (prior.p_reward[0] + prior.p_reward[1]) / 2.0
    return round(v * u * a * r, 4)


def prior_midpoints_separate(prior: ExternalPrior) -> dict[str, float]:
    """Separate midpoints for each probability component."""
    return {
        "p_valid": round((prior.p_valid[0] + prior.p_valid[1]) / 2.0, 4),
        "p_unique": round((prior.p_unique[0] + prior.p_unique[1]) / 2.0, 4),
        "p_accept": round((prior.p_accept[0] + prior.p_accept[1]) / 2.0, 4),
        "p_reward": round((prior.p_reward[0] + prior.p_reward[1]) / 2.0, 4),
    }


# ── P2: Personal Acceptance Probability (separate from reward) ───────


@dataclass(frozen=True)
class AcceptanceRecord:
    """One VERIFIED acceptance outcome. Hypotheses/investigations are NOT outcomes."""

    platform: str
    niche: str
    program: str = ""
    vuln_class: str = ""
    surface: str = ""
    result: str = "rejected"  # accepted | rejected | duplicate | invalid | out_of_scope
    evidence_quality: float = 0.0
    hours_invested: float = 0.0
    predicted_p_accept: float | None = None
    reward_usd: float = 0.0
    opportunity_id: str | None = None
    recorded_at: str = ""

    def is_win(self) -> bool:
        return self.result == "accepted"


@dataclass
class PersonalAcceptanceEstimate:
    """Posterior acceptance probability for a segment. Never quote without evidence_label."""

    niche: str
    platform: str = ""
    program: str = ""
    vuln_class: str = ""
    n_outcomes: int = 0
    n_accepted: int = 0
    n_duplicates: int = 0
    n_rejected: int = 0
    n_invalid: int = 0
    total_hours: float = 0.0
    p_accept: float = 0.0
    p_accept_lower: float = 0.0  # Wilson lower bound
    p_accept_upper: float = 0.0  # Wilson upper bound
    evidence_label: str = "NO_EVIDENCE"
    source: str = "PRIOR_EXTERNO"
    confidence: str = "none"


def _wilson_lower_bound(wins: int, total: int, z: float = 1.96) -> float:
    """Wilson score interval lower bound for binomial proportion."""
    if total == 0:
        return 0.0
    p = wins / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    half_width = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5)
    return max(0.0, (center - half_width) / denominator)


def _wilson_upper_bound(wins: int, total: int, z: float = 1.96) -> float:
    """Wilson score interval upper bound for binomial proportion."""
    if total == 0:
        return 0.0
    p = wins / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    half_width = z * ((p * (1 - p) / total + z * z / (4 * total * total)) ** 0.5)
    return min(1.0, (center + half_width) / denominator)


def acceptance_evidence_label(n: int) -> str:
    """Evidence Gate (P6): label for a sample size. Never fake confidence."""
    if n <= 0:
        return "NO_EVIDENCE"
    if n < MIN_PERSONAL_SAMPLES:
        return "THIN_EVIDENCE"
    if n < LOW_CONFIDENCE_SAMPLES:
        return "LOW"
    if n < MEDIUM_CONFIDENCE_SAMPLES:
        return "MEDIUM"
    if n < HIGH_CONFIDENCE_SAMPLES:
        return "HIGH"
    return "VERY_HIGH"


def acceptance_confidence_level(n: int, evidence_quality: float = 1.0) -> str:
    """Confidence level based on effective sample size."""
    effective_n = min(int(n * evidence_quality), 50)
    if effective_n <= 0:
        return "none"
    if effective_n < LOW_CONFIDENCE_SAMPLES:
        return "low"
    if effective_n < MEDIUM_CONFIDENCE_SAMPLES:
        return "medium"
    if effective_n < HIGH_CONFIDENCE_SAMPLES:
        return "high"
    return "very_high"


class PersonalAcceptanceProbability:
    """Bayesian personal acceptance probability per (platform x niche x vuln_class).

    Posterior mean with prior pseudo-observations so small samples stay
    conservative and large samples are user-driven. Append-only JSONL store.
    """

    def __init__(self, store_path: str | Path | None = None) -> None:
        base = Path(store_path) if store_path else _data_dir() / "learning"
        self.store_path = base / ACCEPTANCE_FILENAME if base.is_dir() or not str(base).endswith(".jsonl") else base

    def record_outcome(
        self,
        *,
        platform: str,
        program: str = "",
        niche: str,
        vuln_class: str = "",
        surface: str = "",
        result: str,
        evidence_quality: float = 0.0,
        hours_invested: float = 0.0,
        predicted_p_accept: float | None = None,
        reward_usd: float = 0.0,
        opportunity_id: str | None = None,
    ) -> AcceptanceRecord:
        """Persist one VERIFIED acceptance outcome. Only call with real platform verdicts."""
        if result not in ("accepted", "rejected", "duplicate", "invalid", "out_of_scope"):
            raise ValueError(f"result must be accepted|rejected|duplicate|invalid|out_of_scope, got {result!r}")
        if not 0.0 <= evidence_quality <= 1.0:
            raise ValueError("evidence_quality must be in [0.0, 1.0]")
        rec = AcceptanceRecord(
            platform=str(platform).strip().lower(),
            program=str(program).strip().lower() if program else "",
            niche=niche,
            vuln_class=str(vuln_class).strip().lower(),
            surface=surface,
            result=result,
            evidence_quality=max(0.0, min(1.0, evidence_quality)),
            hours_invested=max(0.0, float(hours_invested)),
            predicted_p_accept=predicted_p_accept,
            reward_usd=reward_usd,
            opportunity_id=opportunity_id,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def _load(self) -> list[AcceptanceRecord]:
        if not self.store_path.exists():
            return []
        records: list[AcceptanceRecord] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(AcceptanceRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("acceptance_probability: corrupt outcome line ignored")
        except OSError as exc:
            logger.warning("acceptance_probability: store unreadable: %s", exc)
        return records

    def estimate(
        self,
        niche: str,
        platform: str = "",
        program: str = "",
        vuln_class: str = "",
    ) -> PersonalAcceptanceEstimate:
        """Posterior acceptance probability for a segment with Wilson CI and evidence labeling."""
        prior = get_external_prior(niche)
        prior_p = (prior.p_accept[0] + prior.p_accept[1]) / 2.0
        recs = [
            r
            for r in self._load()
            if r.niche == niche
            and (not platform or r.platform == platform.strip().lower())
            and (not program or r.program == program.strip().lower())
            and (not vuln_class or r.vuln_class == vuln_class.strip().lower())
        ]
        n = len(recs)
        n_accepted = sum(1 for r in recs if r.result == "accepted")
        n_duplicates = sum(1 for r in recs if r.result == "duplicate")
        n_rejected = sum(1 for r in recs if r.result == "rejected")
        n_invalid = sum(1 for r in recs if r.result == "invalid")
        total_hours = sum(r.hours_invested for r in recs)

        # Bayesian posterior with prior
        p = (n_accepted + PRIOR_STRENGTH * prior_p) / (n + PRIOR_STRENGTH)
        # Wilson confidence interval
        lower = _wilson_lower_bound(n_accepted, n) if n > 0 else 0.0
        upper = _wilson_upper_bound(n_accepted, n) if n > 0 else 0.0

        label = acceptance_evidence_label(n)
        prior_p = (prior.p_accept[0] + prior.p_accept[1]) / 2.0
        source = "PRIOR_EXTERNO" if n == 0 else ("PRIOR_EXTERNO+personal" if n < MIN_PERSONAL_SAMPLES else "personal")
        confidence = acceptance_confidence_level(n, sum(r.evidence_quality for r in recs) / n if n > 0 else 1.0)

        return PersonalAcceptanceEstimate(
            niche=niche,
            platform=platform,
            program=program,
            vuln_class=vuln_class,
            n_outcomes=n,
            n_accepted=n_accepted,
            n_duplicates=n_duplicates,
            n_rejected=n_rejected,
            n_invalid=n_invalid,
            total_hours=round(sum(r.hours_invested for r in recs), 2),
            p_accept=round(p, 4),
            p_accept_lower=round(lower, 4),
            p_accept_upper=round(upper, 4),
            evidence_label=acceptance_evidence_label(n),
            source=source,
            confidence=confidence,
        )


# ── Evidence Gate (P5) ─────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class EvidenceGateState:
    """Result of evidence gate evaluation."""

    status: str  # NOT_READY | NEEDS_EVIDENCE | NEEDS_UNIQUENESS | HIGH_CONFIDENCE | READY_FOR_HUMAN_REVIEW
    checks: dict[str, bool]
    p_valid: float
    p_unique: float
    p_accept: float
    p_reward: float
    p_accept_lower: float
    confidence: str
    notes: list[str]


class EvidenceGate:
    """Evaluates whether an opportunity has sufficient evidence for HIGH_CONFIDENCE_90."""

    def __init__(
        self,
        acceptance_engine: PersonalAcceptanceProbability | None = None,
        store_path: str | Path | None = None,
    ):
        from cores.direct_work_engine.reward_probability import (
            get_personal_acceptance_probability,
        )

        self.acceptance_engine = acceptance_engine or get_personal_acceptance_probability()
        base = Path(store_path) if store_path else _data_dir() / "learning"
        self.store_path = base / ACCEPTANCE_FILENAME if base.is_dir() or not str(base).endswith(".jsonl") else base

    def _load_acceptance_records(self) -> list[AcceptanceRecord]:
        if not self.store_path.exists():
            return []
        records: list[AcceptanceRecord] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(AcceptanceRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("acceptance_probability: corrupt outcome line ignored")
        except OSError as exc:
            logger.warning("acceptance_probability: store unreadable: %s", exc)
        return records

    def evaluate(
        self,
        opportunity: Any,  # Opportunity model
        evidence: Any,  # EvidenceBundle from evidence.composer
        personal_engine: PersonalAcceptanceProbability | None = None,
    ) -> EvidenceGateState:
        """Evaluate evidence gate for an opportunity."""
        engine = personal_engine or self.acceptance_engine
        niche = niche_for_category(
            getattr(getattr(opportunity, "category", None), "value", getattr(opportunity, "category", ""))
        )
        platform = str(getattr(getattr(opportunity, "platform", None), "value", getattr(opportunity, "platform", "")))
        program = str(getattr(opportunity, "program", "")).strip().lower()
        vuln_class = str(getattr(opportunity, "vuln_class", "")).strip().lower()

        # Evidence scores from EvidenceBundle
        validity_score = getattr(evidence, "cvss_score", 0.0) / 10.0  # CVSS is 0-10, normalize to 0-1
        uniqueness_score = getattr(evidence, "evidence_score", 0.0)  # Use evidence_score as uniqueness proxy
        acceptance_score = getattr(evidence, "acceptance_probability", 0.0)
        reward_score = getattr(evidence, "reward_score", 0.0) if hasattr(evidence, "reward_score") else 0.0
        evidence_score = getattr(evidence, "evidence_score", 0.0)

        # Opportunity fields
        opp_p_accept = getattr(opportunity, "acceptance_probability", 0.0)
        opp_evidence_quality = getattr(opportunity, "evidence_quality", 0.0)
        opp_uniqueness_score = getattr(opportunity, "uniqueness_score", 0.0)
        scope_verified = getattr(opportunity, "scope_verified", False)

        # Personal acceptance estimate (with Wilson CI)
        acceptance_est = self.acceptance_engine.estimate(
            niche_for_category(
                getattr(getattr(opportunity, "category", None), "value", getattr(opportunity, "category", ""))
            ),
            platform=platform,
            program=program,
        )

        # Effective personal acceptance: blend personal posterior with opportunity's acceptance_probability
        personal_p_accept = acceptance_est.p_accept
        if acceptance_est.n_outcomes == 0:
            personal_p_accept = max(acceptance_est.p_accept, getattr(opportunity, "acceptance_probability", 0.0))

        # Effective confidence: use evidence quality when no personal outcomes
        effective_confidence = acceptance_est.confidence
        if acceptance_est.n_outcomes == 0:
            # Base confidence on evidence quality when no personal outcomes
            avg_evidence = getattr(evidence, "evidence_score", 0.0)
            if avg_evidence >= 0.8:
                effective_confidence = "HIGH"
            elif avg_evidence >= 0.6:
                effective_confidence = "MEDIUM"
            elif avg_evidence >= 0.4:
                effective_confidence = "LOW"
            else:
                effective_confidence = "none"

        # Checks for HIGH_CONFIDENCE_90
        checks = {
            "validity": validity_score >= 0.7,
            "uniqueness": uniqueness_score >= 0.6 and getattr(opportunity, "uniqueness_score", 0.0) >= 0.6,
            "scope": scope_verified,
            "evidence": evidence_score >= 0.7,
            "acceptance": personal_p_accept >= 0.90,
            "confidence": effective_confidence in ("HIGH", "VERY_HIGH"),
        }

        # Wilson lower bound for acceptance
        p_accept_lower = acceptance_est.p_accept_lower
        # Effective sample size
        n = acceptance_est.n_outcomes
        evidence_quality = sum(r.evidence_quality for r in self._load_acceptance_records()) / n if n > 0 else 0.0

        notes: list[str] = []
        notes.append(f"P_VALID: {validity_score:.0%}")
        notes.append(f"P_UNIQUE: {uniqueness_score:.0%}")
        notes.append(f"P_ACCEPT: {acceptance_est.p_accept:.1%} (lower bound: {acceptance_est.p_accept_lower:.1%})")
        notes.append(f"P_REWARD: {reward_score:.0%}")
        notes.append(f"Evidence: {evidence_score:.0%}")
        notes.append(f"Scope: {'verified' if scope_verified else 'NOT verified'}")
        notes.append(
            f"Personal n={n}, P_ACCEPT={acceptance_est.p_accept:.1%} [{acceptance_est.evidence_label}, {acceptance_est.confidence}]"
        )

        passed = sum(checks.values())
        if passed == 6:
            status = "HIGH_CONFIDENCE"
        elif passed >= 4 and checks["acceptance"] and checks["confidence"]:
            status = "READY_FOR_HUMAN_REVIEW"
        elif passed >= 3:
            status = "NEEDS_EVIDENCE"
        else:
            status = "NOT_READY"

        return EvidenceGateState(
            status=status,
            checks=checks,
            p_valid=validity_score,
            p_unique=uniqueness_score,
            p_accept=acceptance_est.p_accept,
            p_reward=reward_score,
            p_accept_lower=acceptance_est.p_accept_lower,
            confidence=acceptance_est.confidence,
            notes=notes,
        )

    def _load_acceptance_records_evidence_gate(self) -> list[AcceptanceRecord]:
        if not self.store_path.exists():
            return []
        records: list[AcceptanceRecord] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(AcceptanceRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("acceptance_probability: corrupt outcome line ignored")
        except OSError as exc:
            logger.warning("acceptance_probability: store unreadable: %s", exc)
        return records


# ── Funnel Tracker (P4) ───────────────────────────────────────────
# opportunity != finding != submission != acceptance != reward != PAID.

FUNNEL_STAGES = (
    "discovered",
    "selected",
    "investigated",
    "hypothesis",
    "validated",
    "prepared",
    "approved",
    "submitted",
    "accepted",
    "rewarded",
)


@dataclass(frozen=True, slots=True)
class FunnelEvent:
    opportunity_id: str
    stage: str
    platform: str = ""
    niche: str = ""
    vuln_class: str = ""
    hours_spent: float | None = None
    reward_usd: float | None = None
    recorded_at: str = ""


class FunnelTracker:
    """Append-only funnel instrumentation with timestamps and human hours."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        base = Path(store_path) if store_path else _data_dir() / "learning"
        self.store_path = base / FUNNEL_FILENAME if base.is_dir() or not str(base).endswith(".jsonl") else base

    def record(
        self,
        opportunity_id: str,
        stage: str,
        *,
        platform: str = "",
        niche: str = "",
        vuln_class: str = "",
        hours_spent: float | None = None,
        reward_usd: float | None = None,
    ) -> FunnelEvent:
        if stage not in FUNNEL_STAGES:
            raise ValueError(f"unknown funnel stage: {stage!r}")
        ev = FunnelEvent(
            opportunity_id=opportunity_id,
            stage=stage,
            platform=str(platform).strip().lower(),
            niche=niche,
            vuln_class=str(vuln_class).strip().lower(),
            hours_spent=hours_spent,
            reward_usd=reward_usd,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")
        return ev

    def summary(self) -> dict[str, Any]:
        """Stage counts + totals. Missing stages are 0, never invented."""
        counts: dict[str, int] = dict.fromkeys(FUNNEL_STAGES, 0)
        hours = 0.0
        reward = 0.0
        if self.store_path.exists():
            try:
                for line in self.store_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("stage") in counts:
                        counts[d["stage"]] += 1
                    hours += float(d.get("hours_spent") or 0.0)
                    reward += float(d.get("reward_usd") or 0.0)
            except OSError as exc:
                logger.warning("reward_probability: funnel unreadable: %s", exc)
        per_hour = round(reward / hours, 2) if hours > 0 else None
        return {
            "stages": counts,
            "total_human_hours": round(hours, 2),
            "total_reward_usd": round(reward, 2),
            "reward_per_human_hour": per_hour,
        }


# ── Reward Probability (original) ───────────────────────────────────


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    """One VERIFIED bounty outcome. Hypotheses/investigations are NOT outcomes."""

    platform: str
    niche: str
    vuln_class: str = ""
    surface: str = ""
    result: str = "rejected"  # accepted | rejected | duplicate
    reward_usd: float = 0.0
    predicted_probability: float | None = None
    predicted_reward_usd: float | None = None
    actual_hours: float | None = None
    opportunity_id: str | None = None
    recorded_at: str = ""

    def is_win(self) -> bool:
        return self.result == "accepted" and self.reward_usd > 0


@dataclass
class PersonalRewardEstimate:
    """Posterior estimate for a segment. Never quote p_reward without evidence_label."""

    niche: str
    platform: str = ""
    vuln_class: str = ""
    n_outcomes: int = 0
    n_wins: int = 0
    total_reward_usd: float = 0.0
    total_hours: float = 0.0
    p_reward: float = 0.0
    evidence_label: str = "NO_EVIDENCE"
    source: str = "PRIOR_EXTERNO"
    confidence: str = "none"


def evidence_label(n: int) -> str:
    """Evidence Gate (P6): label for a sample size. Never fake confidence."""
    if n <= 0:
        return "NO_EVIDENCE"
    if n < MIN_PERSONAL_SAMPLES:
        return "THIN_EVIDENCE"
    if n < LOW_CONFIDENCE_SAMPLES:
        return "LOW"
    if n < MEDIUM_CONFIDENCE_SAMPLES:
        return "MEDIUM"
    return "HIGH"


class PersonalRewardProbability:
    """Bayesian personal reward rate per (platform x niche x vuln_class).

    Posterior mean with prior pseudo-observations so small samples stay
    conservative and large samples are user-driven. Append-only JSONL store.
    """

    def __init__(self, store_path: str | Path | None = None) -> None:
        base = Path(store_path) if store_path else _data_dir() / "learning"
        self.store_path = base / OUTCOMES_FILENAME if base.is_dir() or not str(base).endswith(".jsonl") else base

    def record_outcome(
        self,
        *,
        platform: str,
        niche: str,
        result: str,
        reward_usd: float = 0.0,
        vuln_class: str = "",
        surface: str = "",
        predicted_probability: float | None = None,
        predicted_reward_usd: float | None = None,
        actual_hours: float | None = None,
        opportunity_id: str | None = None,
    ) -> OutcomeRecord:
        """Persist one VERIFIED outcome. Only call with real platform verdicts."""
        if result not in ("accepted", "rejected", "duplicate"):
            raise ValueError(f"result must be accepted|rejected|duplicate, got {result!r}")
        rec = OutcomeRecord(
            platform=str(platform).strip().lower(),
            niche=niche,
            result=result,
            reward_usd=max(0.0, float(reward_usd)),
            vuln_class=str(vuln_class).strip().lower(),
            surface=surface,
            predicted_probability=predicted_probability,
            predicted_reward_usd=predicted_reward_usd,
            actual_hours=actual_hours,
            opportunity_id=opportunity_id,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def _load(self) -> list[OutcomeRecord]:
        if not self.store_path.exists():
            return []
        records: list[OutcomeRecord] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(OutcomeRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("reward_probability: corrupt outcome line ignored")
        except OSError as exc:
            logger.warning("reward_probability: store unreadable: %s", exc)
        return records

    def estimate(
        self,
        niche: str,
        platform: str = "",
        vuln_class: str = "",
    ) -> PersonalRewardEstimate:
        """Posterior reward probability for a segment with evidence labeling."""
        prior = get_external_prior(niche)
        prior_p = prior_midpoint(prior)
        recs = [
            r
            for r in self._load()
            if r.niche == niche
            and (not platform or r.platform == platform.strip().lower())
            and (not vuln_class or r.vuln_class == vuln_class.strip().lower())
        ]
        n = len(recs)
        wins = sum(1 for r in recs if r.is_win())
        total_reward = sum(r.reward_usd for r in recs)
        total_hours = sum(r.actual_hours or 0.0 for r in recs)
        p = (wins + PRIOR_STRENGTH * prior_p) / (n + PRIOR_STRENGTH)
        label = evidence_label(n)
        return PersonalRewardEstimate(
            niche=niche,
            platform=platform,
            vuln_class=vuln_class,
            n_outcomes=n,
            n_wins=wins,
            total_reward_usd=round(total_reward, 2),
            total_hours=round(total_hours, 2),
            p_reward=round(p, 4),
            evidence_label=label,
            source="PRIOR_EXTERNO"
            if n == 0
            else ("PRIOR_EXTERNO+personal" if n < MIN_PERSONAL_SAMPLES else "personal"),
            confidence="none"
            if n == 0
            else ("low" if n < LOW_CONFIDENCE_SAMPLES else ("medium" if n < MEDIUM_CONFIDENCE_SAMPLES else "high")),
        )


# ── Singletons ────────────────────────────────────────────────────

_singleton_reward: PersonalRewardProbability | None = None
_singleton_acceptance: PersonalAcceptanceProbability | None = None
_singleton_funnel: FunnelTracker | None = None
_singleton_evidence_gate: EvidenceGate | None = None


def get_personal_reward_probability(store_path: str | Path | None = None) -> PersonalRewardProbability:
    global _singleton_reward
    if _singleton_reward is None or store_path is not None:
        _singleton_reward = PersonalRewardProbability(store_path)
    return _singleton_reward


def get_personal_acceptance_probability(store_path: str | Path | None = None) -> PersonalAcceptanceProbability:
    global _singleton_acceptance
    if _singleton_acceptance is None or store_path is not None:
        _singleton_acceptance = PersonalAcceptanceProbability(store_path)
    return _singleton_acceptance


def get_funnel_tracker() -> FunnelTracker:
    global _singleton_funnel
    if _singleton_funnel is None:
        _singleton_funnel = FunnelTracker()
    return _singleton_funnel


def reset_funnel_tracker() -> None:
    """Reset the singleton (for testing)."""
    global _singleton_funnel
    _singleton_funnel = None


def get_evidence_gate() -> EvidenceGate:
    global _singleton_evidence_gate
    if _singleton_evidence_gate is None:
        _singleton_evidence_gate = EvidenceGate()
    return _singleton_evidence_gate


__all__ = [
    "FUNNEL_STAGES",
    "FunnelEvent",
    "FunnelTracker",
    "LOW_CONFIDENCE_SAMPLES",
    "MEDIUM_CONFIDENCE_SAMPLES",
    "MIN_PERSONAL_SAMPLES",
    "HIGH_CONFIDENCE_SAMPLES",
    "NICHE_API_AUTH",
    "NICHE_AI_LLM",
    "NICHE_OTHER",
    "NICHE_PRIORITY",
    "NICHE_WEB3",
    "NICHE_WEB_CLASSIC",
    "EXTERNAL_REWARD_PRIORS",
    "OutcomeRecord",
    "PersonalRewardEstimate",
    "PersonalRewardProbability",
    "PersonalAcceptanceProbability",
    "AcceptanceRecord",
    "PersonalAcceptanceEstimate",
    "ExternalPrior",
    "evidence_label",
    "acceptance_evidence_label",
    "acceptance_confidence_level",
    "get_external_prior",
    "get_funnel_tracker",
    "get_personal_reward_probability",
    "get_personal_acceptance_probability",
    "get_evidence_gate",
    "niche_for_category",
    "prior_midpoint",
    "prior_midpoints_separate",
    "EvidenceGate",
    "EvidenceGateState",
    "AcceptanceRecord",
    "PersonalAcceptanceEstimate",
    "PersonalRewardEstimate",
    "PersonalRewardProbability",
    "PersonalAcceptanceProbability",
    "RewardPrior",
    "FunnelEvent",
    "FunnelTracker",
]
