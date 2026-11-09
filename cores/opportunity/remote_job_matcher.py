"""Remote Job Matcher — explainable scoring for remote jobs in Spanish (v12 Phase 4).

Pure scoring module: consumes normalized job dicts (from adapters, imports, or
manual entry) and the user's profile/preferences, returns an explainable
MatchResult. No fetching here — adapters/feeds stay separate.

Honesty rules:
- UNKNOWN fields score neutrally, never as compatible.
- Score never overrides hard disqualifiers (e.g. Argentina not admitted).
- No invented data: every reason cites the field it came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Default weights (sum = 1.0), configurable via JobPreferences.weights.
DEFAULT_WEIGHTS = {
    "geo": 0.20,  # Argentina / Latin America admitted
    "requirements": 0.25,  # experience/portfolio barriers vs profile
    "language": 0.15,  # Spanish-language job, no advanced English required
    "modality": 0.10,  # 100% remote
    "compensation": 0.15,  # published salary vs floor
    "selection": 0.10,  # training included, <=1 tech test, no camera/mic required
    "payout": 0.05,  # payout method compatible with Argentina
}

HARD_FAILS = ("argentina_ok",)  # False => INELIGIBLE regardless of score


@dataclass
class JobPreferences:
    """User-configurable matching rules (editable from frontend later)."""

    remote_only: bool = True
    language: str = "es"
    require_argentina: bool = True
    no_experience_preferred: bool = True
    no_portfolio_preferred: bool = True
    max_tech_tests: int = 1
    training_included_preferred: bool = True
    no_signup_fee: bool = True
    salary_min_usd: float = 0.0
    camera_or_mic_required_ok: bool = False
    payment_methods: tuple[str, ...] = ()  # e.g. ("payoneer", "wise", "crypto_usdt")
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


@dataclass
class MatchResult:
    score: float  # 0..100
    eligible: bool
    reasons_positive: list[str] = field(default_factory=list)
    requirements_missing: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 1),
            "eligible": self.eligible,
            "reasons_positive": self.reasons_positive,
            "requirements_missing": self.requirements_missing,
            "risks": self.risks,
            "evidence": self.evidence,
        }


def _truthy(v: Any) -> bool | None:
    """Tri-state: True/False/None(unknown)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "yes", "si", "sí", "1"):
        return True
    if s in ("false", "no", "0"):
        return False
    return None


def match_job(job: dict[str, Any], profile: dict[str, Any] | None = None, prefs: JobPreferences | None = None) -> MatchResult:
    """Score one normalized job dict against preferences.

    Expected job keys (all optional — missing => UNKNOWN, neutral score):
      title, company, url, salary_min, salary_max, currency, remote,
      language, countries_ok/argentina_ok, experience_years_required,
      portfolio_required, tech_tests_required, training_included,
      signup_fee, camera_or_mic_required, english_required,
      payment_methods, published_at, source, evidence.
    """
    prefs = prefs or JobPreferences()
    profile = profile or {}
    res = MatchResult(score=0.0, eligible=True)
    w = prefs.weights or DEFAULT_WEIGHTS
    parts: dict[str, float] = {}

    def add(key: str, value: float) -> None:
        parts[key] = max(0.0, min(1.0, value))

    # ── Hard disqualifiers ──
    argentina = _truthy(job.get("argentina_ok", job.get("countries_ok")))
    if prefs.require_argentina and argentina is False:
        res.eligible = False
        res.risks.append("Argentina explicitly not admitted (argentina_ok=false)")
    if argentina is True:
        res.reasons_positive.append("Argentina admitted")
    elif argentina is None:
        res.requirements_missing.append("Country eligibility not stated")

    # ── Geo (20%) ──
    geo = 1.0 if argentina is True else (0.5 if argentina is None else 0.0)
    add("geo", geo)

    # ── Requirements vs profile (25%) ──
    exp_req = job.get("experience_years_required")
    exp_have = profile.get("experience_years", 0)
    req_score = 1.0
    if exp_req is not None:
        try:
            req = float(exp_req)
            have = float(exp_have or 0)
            if req <= 0:
                req_score = 1.0
                res.reasons_positive.append("No professional experience required")
            elif have >= req:
                req_score = 0.9
            elif have >= req * 0.5:
                req_score = 0.5
                res.requirements_missing.append(f"Requires ~{req:g}y experience, profile has {have:g}y")
            else:
                req_score = 0.2
                res.risks.append(f"Experience gap: requires {req:g}y, profile {have:g}y")
        except (TypeError, ValueError):
            res.requirements_missing.append("experience_years_required unparsable")
    else:
        res.requirements_missing.append("Experience requirement unknown")
    if _truthy(job.get("portfolio_required")) is True:
        req_score *= 0.6
        res.requirements_missing.append("Portfolio required")
    elif _truthy(job.get("portfolio_required")) is False and prefs.no_portfolio_preferred:
        res.reasons_positive.append("No portfolio required")
    if exp_req is None and _truthy(job.get("portfolio_required")) is None:
        req_score = 0.5  # requirements unknown → neutral, not perfect
    add("requirements", req_score)

    # ── Language (15%) ──
    lang = str(job.get("language") or "").lower()
    eng_req = _truthy(job.get("english_required"))
    lang_score = 0.5
    if lang.startswith("es"):
        lang_score = 0.9
        res.reasons_positive.append("Job posted in Spanish")
    if eng_req is False:
        lang_score = min(1.0, lang_score + 0.1)
        res.reasons_positive.append("No advanced English required")
    elif eng_req is True:
        lang_score *= 0.5
        res.risks.append("Advanced English required")
    add("language", lang_score)

    # ── Modality (10%) ──
    remote = _truthy(job.get("remote"))
    if prefs.remote_only and remote is False:
        res.eligible = False
        res.risks.append("Not remote (remote=false)")
    add("modality", 1.0 if remote is True else (0.4 if remote is None else 0.0))
    if remote is True:
        res.reasons_positive.append("100% remote")

    # ── Compensation (15%) ──
    sal_min = job.get("salary_min") or job.get("estimated_payout")
    comp_score = 0.5
    if sal_min is not None:
        try:
            val = float(sal_min)
            if prefs.salary_min_usd and val >= prefs.salary_min_usd:
                comp_score = 1.0
                res.reasons_positive.append(f"Salary {val:g} meets floor {prefs.salary_min_usd:g}")
            elif prefs.salary_min_usd:
                comp_score = val / prefs.salary_min_usd if prefs.salary_min_usd else 0.5
                res.requirements_missing.append(f"Salary {val:g} below floor {prefs.salary_min_usd:g}")
            else:
                comp_score = 0.8
                res.reasons_positive.append("Salary published")
        except (TypeError, ValueError):
            res.requirements_missing.append("Salary unparsable")
    else:
        res.requirements_missing.append("Salary not published")
    add("compensation", comp_score)

    # ── Selection & training (10%) ──
    sel = 0.5
    tests = job.get("tech_tests_required")
    try:
        n_tests = int(tests) if tests is not None else None
    except (TypeError, ValueError):
        n_tests = None
    if n_tests is not None:
        if n_tests <= prefs.max_tech_tests:
            sel += 0.2
            res.reasons_positive.append(f"Tech tests within limit ({n_tests}<={prefs.max_tech_tests})")
        else:
            sel -= 0.3
            res.risks.append(f"{n_tests} tech tests exceed limit {prefs.max_tech_tests}")
    if _truthy(job.get("training_included")) is True:
        sel += 0.15
        res.reasons_positive.append("Training included")
    if _truthy(job.get("camera_or_mic_required")) is True and not prefs.camera_or_mic_required_ok:
        sel -= 0.25
        res.risks.append("Camera/microphone recording required")
    if _truthy(job.get("signup_fee")) is True:
        sel -= 0.4
        res.risks.append("Signup fee required")
    elif _truthy(job.get("signup_fee")) is False:
        sel += 0.1
        res.reasons_positive.append("No signup fee")
    add("selection", max(0.0, min(1.0, sel)))

    # ── Payout method (5%) ──
    payout = job.get("payment_methods") or []
    if isinstance(payout, str):
        payout = [payout]
    if prefs.payment_methods and payout:
        overlap = set(str(p).lower() for p in payout) & set(p.lower() for p in prefs.payment_methods)
        add("payout", 1.0 if overlap else 0.2)
        if overlap:
            res.reasons_positive.append(f"Payout compatible: {sorted(overlap)}")
        else:
            res.risks.append("Payout method not in user preferences")
    else:
        res.requirements_missing.append("Payout method unknown")
        add("payout", 0.5)

    # ── Weighted score ──
    total_w = sum(w.get(k, 0.0) for k in parts) or 1.0
    res.score = 100.0 * sum(parts.get(k, 0.0) * w.get(k, 0.0) for k in parts) / total_w
    res.evidence = {
        "weights": {k: w.get(k, 0.0) for k in parts},
        "components": {k: round(v, 3) for k, v in parts.items()},
        "source": job.get("source"),
        "published_at": job.get("published_at"),
        "url": job.get("url"),
        "title": job.get("title"),
    }
    return res


def rank_jobs(jobs: list[dict[str, Any]], profile: dict[str, Any] | None = None, prefs: JobPreferences | None = None) -> list[dict[str, Any]]:
    """Score + sort jobs descending; eligible first."""
    out = []
    for job in jobs:
        r = match_job(job, profile, prefs)
        out.append({**job, "match": r.as_dict()})
    out.sort(key=lambda j: (j["match"]["eligible"], j["match"]["score"]), reverse=True)
    return out
