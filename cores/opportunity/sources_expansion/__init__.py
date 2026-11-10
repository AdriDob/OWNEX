"""OWNEX source-catalog expansion: 500+ sources + fallback chains.

Architecture
------------
``global_sources.py`` remains the canonical catalog SSOT for the original
151 curated entries. This package adds ~640 verified niche sources across
five thematic modules and provides the machinery the user asked for:

- ``MAX_TOTAL_SOURCES`` — hard cap of 1000 discovery sources.
- ``get_all_sources()`` — merged primary catalog (base + expansion),
  deduplicated by name, capped at 1000, priority-ordered.
- ``FALLBACK_CHAINS`` — for every primary source, ordered alternates
  (subfuentes) used when the primary has no live tasks, is unreachable,
  lacks credentials, or fails eligibility. Computed per category+family
  so substitutes are same-niche.
- ``PAYMENT_FALLBACKS`` — Argentina-incompatible sources get an explicit
  payment fallback strategy (crypto, PayPal, Payoneer, private-message
  negotiation via apply_method=direct_message).
- ``CREDENTIAL_REQUIREMENTS`` — sources needing login/API-key/cookie are
  declared so onboarding can prompt the user instead of failing silently.

Honesty contract: catalog membership != live opportunity. ``auto_scanner``
records ``source_status`` per entry; only real fetches produce opportunities.
"""

from __future__ import annotations

from typing import Any

from cores.opportunity.global_sources import (
    OpportunityCategory,
    SourceDefinition,
)
from cores.opportunity.global_sources import (
    get_base_sources as _base_get_sources,
)
from cores.opportunity.sources_expansion.ai_eval_extra import AI_EVAL_EXTRA
from cores.opportunity.sources_expansion.bug_bounty_extra import (
    BUG_BOUNTY_EXTRA,
)
from cores.opportunity.sources_expansion.data_entry_extra import (
    DATA_ENTRY_EXTRA,
)
from cores.opportunity.sources_expansion.dev_bounty_extra import (
    DEV_BOUNTY_EXTRA,
)
from cores.opportunity.sources_expansion.junior_jobs_extra import (
    JUNIOR_JOBS_EXTRA,
)
from cores.opportunity.sources_expansion.niche_categories import (
    BOUNTIES_EXTRA,
    CONSULTING_EXTRA,
    CYBERSECURITY_EXTRA,
    DATA_SCIENCE_EXTRA,
    DESIGN_EXTRA,
    MARKETPLACES_EXTRA,
    MARKETPLACES_EXTRA_2,
    QA_TESTING_EXTRA,
    REMOTE_WORK_EXTRA,
    TECH_SUPPORT_EXTRA,
    WEB3_AUDITS_EXTRA,
)
from cores.opportunity.sources_expansion.niche_special import NICHE_SPECIAL

__all__ = [
    "MAX_TOTAL_SOURCES",
    "EXPANSION_SOURCES",
    "CREDENTIAL_REQUIREMENTS",
    "PAYMENT_FALLBACKS",
    "get_all_sources",
    "get_expansion_sources",
    "get_fallback_chain",
    "get_source_status",
    "sources_for_scan",
    "count_sources",
]

#: Hard cap on total discovery sources (user requirement: 1000 max).
MAX_TOTAL_SOURCES = 1000

#: Alternate/substitute depth per primary source.
MAX_FALLBACK_DEPTH = 5


def _by_category() -> dict[OpportunityCategory, list[SourceDefinition]]:
    niche_dev = [s for s in NICHE_SPECIAL if s.category == OpportunityCategory.dev_bounty]
    niche_data = [s for s in NICHE_SPECIAL if s.category == OpportunityCategory.data_entry]
    return {
        OpportunityCategory.bug_bounty: list(BUG_BOUNTY_EXTRA),
        OpportunityCategory.dev_bounty: list(DEV_BOUNTY_EXTRA) + niche_dev,
        OpportunityCategory.data_entry: list(DATA_ENTRY_EXTRA) + niche_data,
        OpportunityCategory.ai_evaluation: list(AI_EVAL_EXTRA),
        OpportunityCategory.junior_jobs: list(JUNIOR_JOBS_EXTRA),
        # Extended niche categories — string keys: they equal the StrEnum
        # members when the enum defines them and stay queryable regardless.
        "cybersecurity": list(CYBERSECURITY_EXTRA),
        "data_science": list(DATA_SCIENCE_EXTRA),
        "remote_work": list(REMOTE_WORK_EXTRA),
        "bounties": list(BOUNTIES_EXTRA),
        "web3_audits": list(WEB3_AUDITS_EXTRA),
        "marketplaces": list(MARKETPLACES_EXTRA) + list(MARKETPLACES_EXTRA_2),
        "qa_testing": list(QA_TESTING_EXTRA),
        "consulting": list(CONSULTING_EXTRA),
        "tech_support": list(TECH_SUPPORT_EXTRA),
        "design": list(DESIGN_EXTRA),
    }


def _dedup(sources: list[SourceDefinition]) -> list[SourceDefinition]:
    seen: set[str] = set()
    out: list[SourceDefinition] = []
    for s in sources:
        key = s.name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


EXPANSION_SOURCES: list[SourceDefinition] = _dedup([s for group in _by_category().values() for s in group])


def get_expansion_sources(
    category: OpportunityCategory | None = None,
) -> list[SourceDefinition]:
    """Expansion-only sources, optionally filtered by category."""
    groups = _by_category()
    if category is not None:
        return list(groups.get(category, []))
    return [s for group in groups.values() for s in group]


# Sources that back registered adapters or the curated adapter-ready list
# (mirrors tests/test_source_adaptation.py). The cap must never drop them:
# losing an adapter-ready source silently breaks the adaptation contract.
PINNED_SOURCE_NAMES = frozenset(
    {
        "Algora",
        "Bugcrowd",
        "Data Annotation Tech",
        "Freelancer (coding)",
        "HackerOne",
        "Immunefi",
        "Intigriti",
        "IssueHunt",
        "LinkedIn (Easy Apply)",
        "Mindrift",
        "Open Collective",
        "Opire",
        "Opyre",
        "Outlier",
        "Remotasks",
        "Superteam Earn",
        "YesWeHack",
    }
)


def get_all_sources() -> list[SourceDefinition]:
    """Merged catalog: base 151 + expansion, deduped by name, capped at
    MAX_TOTAL_SOURCES, ordered by (priority desc, quality_score desc)."""
    seen: set[str] = set()
    merged: list[SourceDefinition] = []
    for s in [*_base_get_sources(), *EXPANSION_SOURCES]:
        if s.name.lower().startswith("upwork"):
            continue  # Upwork excluded from active OWNEX functionality
        key = s.name.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(s)
    # Normalize: sources whose credential requirement is 'none' (public boards)
    # do not need an account — keep metadata honest for onboarding.
    from dataclasses import replace

    def _cred_kind(src: SourceDefinition) -> str:
        req = CREDENTIAL_REQUIREMENTS.get(src.name.strip().lower())
        return (req or {}).get("kind", "")

    merged = [replace(s, requires_account=False) if _cred_kind(s) == "none" and s.requires_account else s for s in merged]
    # Adapter-backed sources are pinned: they are never dropped by the cap.
    pinned = [s for s in merged if s.name in PINNED_SOURCE_NAMES]
    rest = [s for s in merged if s.name not in PINNED_SOURCE_NAMES]
    budget = max(MAX_TOTAL_SOURCES - len(pinned), 0)
    return _stratified_cap(rest, budget) + sorted(pinned, key=lambda s: (s.priority, s.quality_score), reverse=True)


def _stratified_cap(sources: list[SourceDefinition], limit: int = MAX_TOTAL_SOURCES) -> list[SourceDefinition]:
    """Cap at limit while preserving every category.

    Pure priority-sort truncation starves niche categories; instead we sort
    within each category and round-robin across categories so all families
    keep representation up to the hard cap.
    """
    if len(sources) <= limit:
        return sorted(sources, key=lambda s: (s.priority, s.quality_score), reverse=True)
    by_cat: dict[Any, list[SourceDefinition]] = {}
    for s in sources:
        by_cat.setdefault(s.category, []).append(s)
    for group in by_cat.values():
        group.sort(key=lambda s: (s.priority, s.quality_score), reverse=True)
    cats = sorted(by_cat, key=lambda c: -len(by_cat[c]))
    out: list[SourceDefinition] = []
    idx = {c: 0 for c in cats}
    while len(out) < limit:
        progressed = False
        for c in cats:
            i = idx[c]
            if i < len(by_cat[c]):
                out.append(by_cat[c][i])
                idx[c] = i + 1
                progressed = True
                if len(out) >= limit:
                    break
        if not progressed:
            break
    out.sort(key=lambda s: (s.priority, s.quality_score), reverse=True)
    return out


def count_sources() -> dict[str, int]:
    """Source counts for reporting/tests."""
    all_src = get_all_sources()
    base = _base_get_sources()
    return {
        "base": len(base),
        "expansion": len(EXPANSION_SOURCES),
        "merged_raw": len(all_src),
        "capped": len(all_src),
        "cap": MAX_TOTAL_SOURCES,
    }


# ---------------------------------------------------------------------------
# Fallback chains (subfuentes / alternates / substitutes)
# ---------------------------------------------------------------------------


def _family_key(s: SourceDefinition) -> str:
    return (getattr(s, "source_family", "") or "").strip().lower()


def get_fallback_chain(source: SourceDefinition | str) -> list[SourceDefinition]:
    """Ordered alternates for ``source`` — same category first, same
    source_family preferred, sorted by (priority, quality_score).

    These are the 'subfuentes' activated when the primary has no live
    tasks, is unreachable, lacks credentials, or fails eligibility.
    """
    if isinstance(source, str):
        name = source.strip().lower()
        match = next((s for s in get_all_sources() if s.name.lower() == name), None)
        if match is None:
            return []
        source = match

    pool = [s for s in get_all_sources() if s.name != source.name and s.category == source.category and not s.name.lower().startswith("upwork")]
    fam = _family_key(source)
    pool.sort(
        key=lambda s: (
            0 if fam and _family_key(s) == fam else 1,
            s.priority,
            s.quality_score,
        ),
        reverse=False,
    )
    # same-family first, then by priority/quality desc
    pool.sort(
        key=lambda s: (
            0 if fam and _family_key(s) == fam else 1,
            -s.priority,
            -s.quality_score,
        )
    )
    return pool[:MAX_FALLBACK_DEPTH]


def get_payment_fallback(source: SourceDefinition | str) -> dict[str, Any] | None:
    """Payment-fallback strategy for a source (Argentina compatibility).

    Returns a dict describing the alternate payment/contact path when the
    primary rails don't reach Argentina (e.g. ``private_message``
    negotiation, crypto payout, PayPal, Payoneer, Wise).
    """
    name = source.name if isinstance(source, SourceDefinition) else str(source)
    low = name.strip().lower()
    # Argentina-compatible sources need no fallback.
    if isinstance(source, SourceDefinition) and source.argentina_ok:
        return None
    if isinstance(source, SourceDefinition) and not source.argentina_ok:
        strategy = "private_message"
        if source.apply_method == "direct_message":
            strategy = "direct_message_negotiation"
        elif any(t in " ".join(source.tags).lower() for t in ("crypto", "web3")):
            strategy = "crypto_payout"
        elif "payoneer" in low or "wise" in low:
            strategy = "payoneer_wise"
        return {
            "source": source.name,
            "primary_blocked": "argentina_restricted",
            "fallback": strategy,
            "notes": (
                "Primary payout rails may not reach Argentina. "
                "Negotiate alternate payment (crypto/USDC, PayPal, "
                "Payoneer, Wise) via platform messaging before starting work."
            ),
        }
    return PAYMENT_FALLBACKS.get(low)


# Explicit payment-fallback overrides for well-known restricted platforms.
PAYMENT_FALLBACKS: dict[str, dict[str, Any]] = {
    "toptal": {
        "source": "Toptal",
        "primary_blocked": "argentina_restricted",
        "fallback": "entity_via_us_llc",
        "notes": "Toptal requires US/EU entity for some contracts; use LLC or ask for direct contract.",
    },
    "gun.io": {
        "source": "Gun.io",
        "primary_blocked": "argentina_restricted",
        "fallback": "crypto_via_opire",
        "notes": "Gun.io prefers US contractors; use Braintrust/Opire crypto-paying alternatives.",
    },
    "catalant": {
        "source": "Catalant",
        "primary_blocked": "argentina_restricted",
        "fallback": "private_message",
        "notes": "Catalant expert network may restrict LatAm; negotiate direct engagement.",
    },
}


# ---------------------------------------------------------------------------
# Credential requirements (onboarding prompts)
# ---------------------------------------------------------------------------

#: Sources that need credentials before any real work can be fetched/applied.
#: ``kind``: login | api_key | cookie | oauth | paid_account | none.
CREDENTIAL_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "hackerone": {"kind": "login", "notes": "HackerOne researcher account + program invites."},
    "bugcrowd": {"kind": "login", "notes": "Bugcrowd researcher account."},
    "intigriti": {"kind": "login", "notes": "Intigriti researcher account."},
    "yeswehack": {"kind": "login", "notes": "YesWeHack researcher account."},
    "federacy": {"kind": "login", "notes": "Federacy researcher account."},
    "bugrap": {"kind": "login", "notes": "BugRap account."},
    "immunefi": {"kind": "login", "notes": "Immunefi account; KYC for payouts."},
    "cantina": {"kind": "login", "notes": "Cantina account."},
    "codehawks": {"kind": "login", "notes": "CodeHawks/Cyfrin account."},
    "hats finance": {"kind": "login", "notes": "Hats Finance account; wallet for payouts."},
    "hackenproof": {"kind": "login", "notes": "HackenProof account."},
    "opire": {"kind": "login", "notes": "Opire account; wallet for crypto payouts."},
    "issuehunt": {"kind": "login", "notes": "IssueHunt account."},
    "algora": {"kind": "login", "notes": "Algora account; GitHub OAuth."},
    "polar.sh": {"kind": "login", "notes": "Polar.sh account."},
    "onlydust": {"kind": "login", "notes": "OnlyDust account; wallet."},
    "drips": {"kind": "login", "notes": "Drips account; wallet."},
    "gitcoin": {"kind": "login", "notes": "Gitcoin passport/account."},
    "boss.dev": {"kind": "login", "notes": "Boss.dev account; GitHub OAuth."},
    "console.xyz bounties": {"kind": "login", "notes": "Console.xyz account; wallet."},
    "dework": {"kind": "login", "notes": "Dework account; wallet."},
    "layer3": {"kind": "login", "notes": "Layer3 account."},
    "zealy": {"kind": "login", "notes": "Zealy account."},
    "taskon": {"kind": "login", "notes": "TaskOn account."},
    "galxe": {"kind": "login", "notes": "Galxe account."},
    "guild.xyz": {"kind": "login", "notes": "Guild.xyz account."},
    "superteam earn": {"kind": "login", "notes": "Superteam Earn account; Solana wallet."},
    "dorahacks bounties": {"kind": "login", "notes": "DoraHacks account."},
    "fiverr": {"kind": "login", "notes": "Fiverr seller account."},
    "freelancer.com": {"kind": "login", "notes": "Freelancer.com account."},
    "workana": {"kind": "login", "notes": "Workana account."},
    "get on board": {"kind": "login", "notes": "Get on Board candidate profile."},
    "arc.dev": {"kind": "login", "notes": "Arc.dev candidate profile; vetting."},
    "turing": {"kind": "login", "notes": "Turing candidate profile; AI vetting."},
    "bairesdev": {"kind": "login", "notes": "BairesDev candidate profile."},
    "revelo": {"kind": "login", "notes": "Revelo candidate profile."},
    "strider": {"kind": "login", "notes": "Strider candidate profile."},
    "clouddevs": {"kind": "login", "notes": "CloudDevs candidate profile."},
    "terminal.io": {"kind": "login", "notes": "Terminal.io candidate profile."},
    "andela": {"kind": "login", "notes": "Andela candidate profile."},
    "braintrust": {"kind": "login", "notes": "Braintrust talent profile."},
    "catalant": {"kind": "login", "notes": "Catalant expert profile."},
    "malt": {"kind": "login", "notes": "Malt freelancer profile."},
    "truelancer": {"kind": "login", "notes": "Truelancer account."},
    "guru": {"kind": "login", "notes": "Guru freelancer account."},
    "peopleperhour": {"kind": "login", "notes": "PeoplePerHour account."},
    "microworkers": {"kind": "login", "notes": "Microworkers account."},
    "clickworker": {"kind": "login", "notes": "Clickworker account."},
    "appen": {"kind": "login", "notes": "Appen contributor account."},
    "telus international ai": {"kind": "login", "notes": "TELUS AI contributor account."},
    "oneforma": {"kind": "login", "notes": "OneForma account."},
    "dataforce": {"kind": "login", "notes": "DataForce account."},
    "alignerr": {"kind": "login", "notes": "Alignerr account; assessment."},
    "mercor": {"kind": "login", "notes": "Mercor candidate profile; assessment."},
    "surge ai": {"kind": "login", "notes": "Surge AI contributor profile."},
    "outlier": {"kind": "login", "notes": "Outlier contributor profile."},
    "dataannotation": {"kind": "login", "notes": "DataAnnotation contributor profile."},
    "invisible technologies": {"kind": "login", "notes": "Invisible contributor profile."},
    "imerit": {"kind": "login", "notes": "iMerit contributor profile."},
    "centific": {"kind": "login", "notes": "Centific contributor profile."},
    "sama": {"kind": "login", "notes": "Sama contributor profile."},
    "prolific": {"kind": "login", "notes": "Prolific participant account."},
    "usertesting": {"kind": "login", "notes": "UserTesting contributor account."},
    "userlytics": {"kind": "login", "notes": "Userlytics contributor account."},
    "user interviews": {"kind": "login", "notes": "User Interviews participant account."},
    "respondent": {"kind": "login", "notes": "Respondent participant account."},
    "testingtime": {"kind": "login", "notes": "TestingTime participant account."},
    "userzoom": {"kind": "login", "notes": "UserZoom participant account."},
    "userfeel": {"kind": "login", "notes": "UserFeel participant account."},
    "trymyui": {"kind": "login", "notes": "TryMyUI participant account."},
    "userbrain": {"kind": "login", "notes": "Userbrain participant account."},
    "playtestcloud": {"kind": "login", "notes": "PlaytestCloud tester account."},
    "betatesting": {"kind": "login", "notes": "BetaTesting participant account."},
    "testbirds": {"kind": "login", "notes": "Testbirds tester account."},
    "utest": {"kind": "login", "notes": "uTest tester account."},
    "testlio": {"kind": "login", "notes": "Testlio tester account."},
    "bugfinders": {"kind": "login", "notes": "BugFinders tester account."},
    "test io": {"kind": "login", "notes": "Test.io tester account."},
    "testomat.io": {"kind": "login", "notes": "Testomat tester account."},
    "testerwork": {"kind": "login", "notes": "TesterWork account."},
    "validately": {"kind": "login", "notes": "Validately participant account."},
    "pingpong": {"kind": "login", "notes": "PingPong research account."},
    "dscout": {"kind": "login", "notes": "dscout participant account."},
    "fieldwork": {"kind": "login", "notes": "Fieldwork participant account."},
    "savanta": {"kind": "login", "notes": "Savanta panel account."},
    "kantar profiles": {"kind": "login", "notes": "Kantar Profiles account."},
    "ipsos i-say": {"kind": "login", "notes": "Ipsos i-Say account."},
    "cint": {"kind": "login", "notes": "Cint panel account."},
    "lucid": {"kind": "login", "notes": "Lucid panel account."},
    "dynata": {"kind": "login", "notes": "Dynata panel account."},
    "yougov": {"kind": "login", "notes": "YouGov account."},
    "swagbucks": {"kind": "login", "notes": "Swagbucks account."},
    "inboxdollars": {"kind": "login", "notes": "InboxDollars account."},
    "freecash": {"kind": "login", "notes": "Freecash account."},
    "toloka": {"kind": "login", "notes": "Toloka contributor account."},
    "remotasks": {"kind": "login", "notes": "Remotasks contributor account."},
    "figure ai": {"kind": "login", "notes": "Figure AI contributor account."},
    "encord annotator": {"kind": "login", "notes": "Encord contributor account."},
    "v7 labs": {"kind": "login", "notes": "V7 contributor account."},
    "labelbox contributors": {"kind": "login", "notes": "Labelbox contributor account."},
    "snorkel": {"kind": "login", "notes": "Snorkel expert account."},
    "scale rapid": {"kind": "login", "notes": "Scale Rapid expert account."},
    "handshake ai": {"kind": "login", "notes": "Handshake account."},
    "handshake freelance": {"kind": "login", "notes": "Handshake account."},
    "welocalize": {"kind": "login", "notes": "Welocalize contributor account."},
    "gengo": {"kind": "login", "notes": "Gengo translator account."},
    "smartcat": {"kind": "login", "notes": "Smartcat translator account."},
    "proz": {"kind": "login", "notes": "ProZ translator account."},
    "translatorscafe": {"kind": "login", "notes": "TranslatorsCafe account."},
    "bluesky intl": {"kind": "login", "notes": "Bluesky translator account."},
    "conyac": {"kind": "login", "notes": "Conyac translator account."},
    "textmaster": {"kind": "login", "notes": "TextMaster account."},
    "unbabel": {"kind": "login", "notes": "Unbabel contributor account."},
    "lionbridge/appen ai": {"kind": "login", "notes": "Lionbridge/Appen account."},
    "welocalize ai": {"kind": "login", "notes": "Welocalize AI account."},
    "argos": {"kind": "login", "notes": "Argos translator account."},
    "keywords studios": {"kind": "login", "notes": "Keywords Studios freelancer account."},
    "keywords locdirect": {"kind": "login", "notes": "Keywords LocDirect account."},
    "hogarth": {"kind": "login", "notes": "Hogarth freelancer account."},
    "argos multilingual": {"kind": "login", "notes": "Argos Multilingual account."},
    "transperfect": {"kind": "login", "notes": "TransPerfect freelancer account."},
    "lionbridge freelance": {"kind": "login", "notes": "Lionbridge freelancer account."},
    "rws": {"kind": "login", "notes": "RWS contributor account."},
    "blend": {"kind": "login", "notes": "Blend contributor account."},
    "lilt": {"kind": "login", "notes": "Lilt contributor account."},
    "smartcat contributors": {"kind": "login", "notes": "Smartcat contributors account."},
    "one hour translation": {"kind": "login", "notes": "One Hour Translation account."},
    "transify": {"kind": "login", "notes": "Transify translator account."},
    "speaky": {"kind": "login", "notes": "Speaky account."},
    "italki": {"kind": "login", "notes": "italki tutor account."},
    "preply": {"kind": "login", "notes": "Preply tutor account."},
    "cambly": {"kind": "login", "notes": "Cambly tutor account."},
    "vipkid": {"kind": "login", "notes": "VIPKid tutor account."},
    "outschool": {"kind": "login", "notes": "Outschool teacher account."},
    "teachable kids": {"kind": "login", "notes": "Teachable Kids teacher account."},
    "codementor learn": {"kind": "login", "notes": "Codementor mentor account."},
    "wyzant": {"kind": "login", "notes": "Wyzant tutor account."},
    "chegg tutors": {"kind": "login", "notes": "Chegg tutor account."},
    "tutorme": {"kind": "login", "notes": "TutorMe tutor account."},
    "varsity tutors": {"kind": "login", "notes": "Varsity Tutors account."},
    "lessonface": {"kind": "login", "notes": "Lessonface teacher account."},
    "takelessons": {"kind": "login", "notes": "TakeLessons teacher account."},
    "superprof": {"kind": "login", "notes": "Superprof tutor account."},
    "thumbtack": {"kind": "login", "notes": "Thumbtack pro account."},
    "taskrabbit": {"kind": "login", "notes": "TaskRabbit tasker account."},
    "angi": {"kind": "login", "notes": "Angi pro account."},
    "homeadvisor": {"kind": "login", "notes": "HomeAdvisor pro account."},
    "porch": {"kind": "login", "notes": "Porch pro account."},
    "oss jobs": {"kind": "login", "notes": "OSS Jobs profile."},
    "remote ok": {"kind": "api_key", "notes": "RemoteOK API key optional; scrape otherwise."},
    "we work remotely": {"kind": "login", "notes": "WWR employer account for posting; candidates browse free."},
    "remote.co": {"kind": "none", "notes": "Public job board; no login needed to browse."},
    "remotive": {"kind": "api_key", "notes": "Remotive public API; no key for basic use."},
    "jobspresso": {"kind": "none", "notes": "Public job board."},
    "working nomads": {"kind": "api_key", "notes": "Working Nomads public API."},
    "himalayas": {"kind": "none", "notes": "Public job board."},
    "wellfound (angelist)": {"kind": "login", "notes": "Wellfound candidate profile."},
    "y combinator jobs": {"kind": "none", "notes": "Public YC job board."},
    "landing.jobs": {"kind": "login", "notes": "Landing.jobs candidate profile."},
    "relocateMe": {"kind": "none", "notes": "Public relocation job board."},
    "eu remote jobs": {"kind": "none", "notes": "Public remote job board."},
    "jsremotely": {"kind": "none", "notes": "Public JS job board."},
    "react jobs": {"kind": "none", "notes": "Public React job board."},
    "vue jobs": {"kind": "none", "notes": "Public Vue job board."},
    "python jobs": {"kind": "none", "notes": "Public Python.org job board."},
    "django jobs": {"kind": "none", "notes": "Public Django job board."},
    "go jobs": {"kind": "none", "notes": "Public Go job board."},
    "rust jobs": {"kind": "none", "notes": "Public Rust job board."},
    "web3 jobs": {"kind": "none", "notes": "Public web3.career board."},
    "crypto jobs": {"kind": "none", "notes": "Public crypto.jobs board."},
    "bankless jobs": {"kind": "none", "notes": "Public Bankless job board."},
    "remote3": {"kind": "none", "notes": "Public Remote3 board."},
    " cryptocurrencyjobs": {"kind": "none", "notes": "Public crypto job board."},
    "dejob": {"kind": "login", "notes": "Dework account for Dework jobs."},
    "dework jobs": {"kind": "login", "notes": "Dework account."},
    "laborx": {"kind": "login", "notes": "LaborX account."},
    "ethlance": {"kind": "login", "notes": "Ethlance account (verify active)."},
    "cryptogrind": {"kind": "login", "notes": "Cryptogrind account."},
    "gitcoin bounties": {"kind": "login", "notes": "Gitcoin account."},
    "issuehunt jobs": {"kind": "login", "notes": "IssueHunt account."},
    "codebounty": {"kind": "login", "notes": "CodeBounty account."},
    "bountysource": {"kind": "login", "notes": "Bountysource account (legacy)."},
    "polar bounties": {"kind": "login", "notes": "Polar.sh account."},
    "open collective": {"kind": "login", "notes": "Open Collective account."},
    "tidelift": {"kind": "login", "notes": "Tidelift maintainer account."},
    "thanks.dev": {"kind": "login", "notes": "Thanks.dev account."},
    "opensponsorship": {"kind": "login", "notes": "OpenSponsorship account."},
    "patreon for devs": {"kind": "login", "notes": "Patreon creator account."},
    "liberapay": {"kind": "login", "notes": "Liberapay account."},
    "ko-fi": {"kind": "login", "notes": "Ko-fi account."},
    "buy me a coffee": {"kind": "login", "notes": "Buy Me a Coffee account."},
    "github sponsors": {"kind": "login", "notes": "GitHub Sponsors account."},
    "codementor": {"kind": "login", "notes": "Codementor mentor account."},
    "arc (was codementor arc)": {"kind": "login", "notes": "Arc.dev account."},
    "sessionlab": {"kind": "login", "notes": "SessionLab facilitator account."},
    "maven": {"kind": "login", "notes": "Maven instructor account."},
    "podia": {"kind": "login", "notes": "Podia creator account."},
    "teachable": {"kind": "login", "notes": "Teachable instructor account."},
    "udemy instructor": {"kind": "login", "notes": "Udemy instructor account."},
    "skillshare teacher": {"kind": "login", "notes": "Skillshare teacher account."},
    "youtube partner": {"kind": "login", "notes": "YouTube channel + Partner Program."},
    "medium partner": {"kind": "login", "notes": "Medium Partner Program."},
    "dev.to": {"kind": "none", "notes": "Dev.to public community; tips optional."},
    "hashnode": {"kind": "login", "notes": "Hashnode account."},
    "substack": {"kind": "login", "notes": "Substack publication account."},
    "ghost": {"kind": "login", "notes": "Ghost publication account."},
    "contra": {"kind": "login", "notes": "Contra independent profile."},
    "maven freelance": {"kind": "login", "notes": "Maven expert account."},
    "clarity.fm": {"kind": "login", "notes": "Clarity.fm expert account."},
    "intro": {"kind": "login", "notes": "Intro expert account."},
    "zintro": {"kind": "login", "notes": "Zintro expert account."},
    "glg": {"kind": "login", "notes": "GLG expert account."},
    "third bridge": {"kind": "login", "notes": "Third Bridge expert account."},
    "alphasights": {"kind": "login", "notes": "AlphaSights expert account."},
    "newtonx": {"kind": "login", "notes": "NewtonX expert account."},
    "guidepoint": {"kind": "login", "notes": "Guidepoint expert account."},
    "techspert": {"kind": "login", "notes": "Techspert expert account."},
    "coleman research": {"kind": "login", "notes": "Coleman Research expert account."},
    "atheneum": {"kind": "login", "notes": "Atheneum expert account."},
    "dialectica": {"kind": "login", "notes": "Dialectica expert account."},
    "maven expert": {"kind": "login", "notes": "Maven expert account."},
    "entryleveljobs": {"kind": "none", "notes": "Public job board."},
    "juniorjobs": {"kind": "none", "notes": "Public job board."},
    "landing.jobs junior": {"kind": "login", "notes": "Landing.jobs profile."},
    "get on board junior": {"kind": "login", "notes": "Get on Board profile."},
    "computrabajo junior": {"kind": "login", "notes": "Computrabajo account."},
    "bumeran junior": {"kind": "login", "notes": "Bumeran account."},
    "zonajobs": {"kind": "login", "notes": "ZonaJobs account."},
    "linkedin entry level": {"kind": "login", "notes": "LinkedIn account."},
    "indeed entry level": {"kind": "login", "notes": "Indeed account for alerts."},
    "glassdoor entry": {"kind": "login", "notes": "Glassdoor account."},
    "simplyhired": {"kind": "none", "notes": "Public job board."},
    "monster entry": {"kind": "login", "notes": "Monster account."},
    "careerbuilder": {"kind": "login", "notes": "CareerBuilder account."},
    "dice entry": {"kind": "login", "notes": "Dice account."},
    "built in entry": {"kind": "login", "notes": "Built In account."},
    "angelist entry": {"kind": "login", "notes": "Wellfound profile."},
    "y combinator entry": {"kind": "none", "notes": "Public YC board."},
    "hacker news 'who is hiring'": {"kind": "none", "notes": "Public HN thread."},
    "remoteok junior": {"kind": "api_key", "notes": "RemoteOK API."},
    "weworkremotely junior": {"kind": "none", "notes": "Public WWR board."},
    "remotive junior": {"kind": "api_key", "notes": "Remotive API."},
    "himalayas junior": {"kind": "none", "notes": "Public Himalayas board."},
    "jobspresso junior": {"kind": "none", "notes": "Public board."},
    "workingnomads junior": {"kind": "api_key", "notes": "Working Nomads API."},
    "justremote": {"kind": "none", "notes": "Public board."},
    "remote.co junior": {"kind": "none", "notes": "Public board."},
    "nodesk": {"kind": "none", "notes": "Public board."},
    "skipthedrive": {"kind": "none", "notes": "Public board."},
    "virtual vocations": {"kind": "paid_account", "notes": "Virtual Vocations paid subscription."},
    "flexjobs junior": {"kind": "paid_account", "notes": "FlexJobs paid subscription."},
    "pangian": {"kind": "none", "notes": "Public board."},
    "jobspresso entry": {"kind": "none", "notes": "Public board."},
    "eu remote jobs junior": {"kind": "none", "notes": "Public board."},
    "landing.jobs graduate": {"kind": "login", "notes": "Landing.jobs profile."},
    "landing.jobs trainee": {"kind": "login", "notes": "Landing.jobs profile."},
    "careers in code": {"kind": "none", "notes": "Public board."},
    "entrylevel.dev": {"kind": "none", "notes": "Public board."},
    "junior dev jobs": {"kind": "none", "notes": "Public board."},
    "firstjob.tech": {"kind": "none", "notes": "Public board."},
    "new grad tech": {"kind": "none", "notes": "Public board."},
    "internships.com": {"kind": "login", "notes": "Internships.com account."},
    "handshake internships": {"kind": "login", "notes": "Handshake account."},
    "ripplematch": {"kind": "login", "notes": "RippleMatch account."},
    "wayup": {"kind": "login", "notes": "WayUp account."},
    "college recruiter": {"kind": "login", "notes": "College Recruiter account."},
    "aftercollege": {"kind": "login", "notes": "AfterCollege account."},
    "snagajob": {"kind": "login", "notes": "Snagajob account."},
    "craigslist gigs": {"kind": "none", "notes": "Public Craigslist gigs."},
    "reddit forhire": {"kind": "login", "notes": "Reddit account."},
    "reddit slavelabour": {"kind": "login", "notes": "Reddit account."},
    "discord dev communities": {"kind": "login", "notes": "Discord account."},
    "codenewbie jobs": {"kind": "login", "notes": "CodeNewbie account."},
    "boot.dev jobs": {"kind": "login", "notes": "Boot.dev account."},
    "codecademy jobs": {"kind": "login", "notes": "Codecademy account."},
    "freecodecamp jobs": {"kind": "login", "notes": "freeCodeCamp forum account."},
    "the odin project": {"kind": "login", "notes": "TOP community account."},
    "scrimba jobs": {"kind": "login", "notes": "Scrimba account."},
    "frontend masters jobs": {"kind": "login", "notes": "Frontend Masters account."},
    "pluralsight jobs": {"kind": "login", "notes": "Pluralsight account."},
    "coursera careers": {"kind": "login", "notes": "Coursera account."},
    "udacity nanodegree": {"kind": "paid_account", "notes": "Udacity Nanodegree (paid)."},
    "general assembly": {"kind": "paid_account", "notes": "GA bootcamp (paid)."},
    "flatiron school": {"kind": "paid_account", "notes": "Flatiron bootcamp (paid)."},
    "springboard": {"kind": "paid_account", "notes": "Springboard bootcamp (paid)."},
    "thinkful": {"kind": "paid_account", "notes": "Thinkful bootcamp (paid)."},
    "lambda school": {"kind": "paid_account", "notes": "Lambda School (paid)."},
    "app academy": {"kind": "paid_account", "notes": "App Academy (paid)."},
    "hack reactor": {"kind": "paid_account", "notes": "Hack Reactor (paid)."},
    "fullstack academy": {"kind": "paid_account", "notes": "Fullstack Academy (paid)."},
    "codesmith": {"kind": "paid_account", "notes": "Codesmith (paid)."},
    "actualize": {"kind": "paid_account", "notes": "Actualize (paid)."},
    "coding dojo": {"kind": "paid_account", "notes": "Coding Dojo (paid)."},
    "devmountain": {"kind": "paid_account", "notes": "DevMountain (paid)."},
    "nucamp": {"kind": "paid_account", "notes": "Nucamp (paid)."},
    "careerfoundry": {"kind": "paid_account", "notes": "CareerFoundry (paid)."},
    "ironhack": {"kind": "paid_account", "notes": "Ironhack (paid)."},
    "le wagon": {"kind": "paid_account", "notes": "Le Wagon (paid)."},
    "42 school": {"kind": "login", "notes": "42 School application."},
    "microverse": {"kind": "paid_account", "notes": "Microverse (paid)."},
    "alx africa": {"kind": "login", "notes": "ALX Africa application."},
    "holberton school": {"kind": "paid_account", "notes": "Holberton (paid)."},
    "founders and coders": {"kind": "login", "notes": "Founders and Coders application."},
    "makers academy": {"kind": "paid_account", "notes": "Makers Academy (paid)."},
    "code your future": {"kind": "login", "notes": "Code your Future application."},
    "42 berlin": {"kind": "login", "notes": "42 Berlin application."},
    "42 paris": {"kind": "login", "notes": "42 Paris application."},
    "hive helsinki": {"kind": "login", "notes": "Hive Helsinki application."},
    "recurse center": {"kind": "login", "notes": "Recurse Center application."},
    "the odin project jobs": {"kind": "login", "notes": "TOP community account."},
    "freecodecamp forum jobs": {"kind": "login", "notes": "freeCodeCamp forum account."},
    "dev.to jobs": {"kind": "none", "notes": "Public Dev.to jobs."},
    "hashnode jobs": {"kind": "login", "notes": "Hashnode account."},
    "remote.io junior": {"kind": "none", "notes": "Public board."},
    "working nomads api": {"kind": "api_key", "notes": "Working Nomads API."},
    "remotive api": {"kind": "api_key", "notes": "Remotive API."},
    "remoteok api": {"kind": "api_key", "notes": "RemoteOK API."},
    "arbeitnow api": {"kind": "api_key", "notes": "Arbeitnow API key."},
    "jobicy api": {"kind": "api_key", "notes": "Jobicy API."},
    "reed api": {"kind": "api_key", "notes": "Reed API key."},
    "adzuna api": {"kind": "api_key", "notes": "Adzuna API key."},
    "jooble api": {"kind": "api_key", "notes": "Jooble API key."},
    "careerjet api": {"kind": "api_key", "notes": "Careerjet API key."},
    "usajobs api": {"kind": "api_key", "notes": "USAJobs API key."},
    "publicservicecareers": {"kind": "none", "notes": "Public board."},
    "fedjobs": {"kind": "none", "notes": "Public board."},
    "it support freelance (upwork alt)": {"kind": "login", "notes": "Truelancer account."},
    "freelanceit": {"kind": "login", "notes": "FreelanceIT account."},
    "itprojobs": {"kind": "login", "notes": "ITProJobs account."},
    "dice it": {"kind": "login", "notes": "Dice account."},
    "cybersecurityjobs": {"kind": "none", "notes": "Public board."},
    "infosec jobs": {"kind": "none", "notes": "Public board."},
    "sans job board": {"kind": "none", "notes": "Public SANS board."},
    "helpsystems jobs": {"kind": "none", "notes": "Public board."},
    "spiceworks community": {"kind": "login", "notes": "Spiceworks account."},
    "reddit sysadmin": {"kind": "login", "notes": "Reddit account."},
    "reddit itjobs": {"kind": "login", "notes": "Reddit account."},
    "reddit sysadminjobs": {"kind": "login", "notes": "Reddit account."},
    "reddit netsecjobs": {"kind": "login", "notes": "Reddit account."},
    "reddit cybersecurityjobs": {"kind": "login", "notes": "Reddit account."},
    "reddit itcareerquestions": {"kind": "login", "notes": "Reddit account."},
    "devops freelance boards": {"kind": "login", "notes": "Truelancer account."},
    "devopsjobs": {"kind": "none", "notes": "Public board."},
    "kubernetes jobs": {"kind": "none", "notes": "Public CNCF listings."},
    "cloud native jobs": {"kind": "none", "notes": "Public CNCF listings."},
    "terraform jobs": {"kind": "none", "notes": "Public HashiCorp listings."},
    "ansible jobs": {"kind": "none", "notes": "Public Red Hat listings."},
    "jenkins jobs": {"kind": "none", "notes": "Public Jenkins listings."},
    "gitlab jobs": {"kind": "login", "notes": "GitLab account."},
    "github jobs": {"kind": "login", "notes": "GitHub account."},
    "hashicorp jobs": {"kind": "login", "notes": "HashiCorp account."},
    "docker jobs": {"kind": "login", "notes": "Docker account."},
    "red hat jobs": {"kind": "login", "notes": "Red Hat account."},
    "canonical jobs": {"kind": "login", "notes": "Canonical account."},
    "suse jobs": {"kind": "login", "notes": "SUSE account."},
    "elastic jobs": {"kind": "login", "notes": "Elastic account."},
    "confluent jobs": {"kind": "login", "notes": "Confluent account."},
    "datadog jobs": {"kind": "login", "notes": "Datadog account."},
    "new relic jobs": {"kind": "login", "notes": "New Relic account."},
    "splunk jobs": {"kind": "login", "notes": "Splunk account."},
    "grafana labs jobs": {"kind": "login", "notes": "Grafana Labs account."},
    "pagerduty jobs": {"kind": "login", "notes": "PagerDuty account."},
    "opsgenie/atlassian": {"kind": "login", "notes": "Atlassian account."},
    "circleci jobs": {"kind": "login", "notes": "CircleCI account."},
    "travis ci jobs": {"kind": "login", "notes": "Travis CI account."},
    "buildkite jobs": {"kind": "login", "notes": "Buildkite account."},
    "gitlab devops jobs": {"kind": "login", "notes": "GitLab account."},
    "jenkins x jobs": {"kind": "none", "notes": "Public Jenkins listings."},
    "spinnaker jobs": {"kind": "none", "notes": "Public Spinnaker listings."},
    "argo jobs": {"kind": "none", "notes": "Public Argo listings."},
    "flux jobs": {"kind": "none", "notes": "Public Flux listings."},
    "istio jobs": {"kind": "none", "notes": "Public Istio listings."},
    "envoy jobs": {"kind": "none", "notes": "Public Envoy listings."},
    "linkerd jobs": {"kind": "none", "notes": "Public Linkerd listings."},
    "consul jobs": {"kind": "login", "notes": "HashiCorp account."},
    "vault jobs": {"kind": "login", "notes": "HashiCorp account."},
    "boundary jobs": {"kind": "login", "notes": "HashiCorp account."},
    "waypoint jobs": {"kind": "login", "notes": "HashiCorp account."},
    "packer jobs": {"kind": "none", "notes": "Public Packer listings."},
    "vagrant jobs": {"kind": "none", "notes": "Public Vagrant listings."},
    "nomad jobs": {"kind": "login", "notes": "HashiCorp account."},
    "waypoint/boundary": {"kind": "login", "notes": "HashiCorp account."},
    "automation freelance": {"kind": "login", "notes": "Truelancer account."},
    "zapier experts": {"kind": "login", "notes": "Zapier expert profile."},
    "make experts": {"kind": "login", "notes": "Make expert profile."},
    "n8n experts": {"kind": "login", "notes": "n8n expert profile."},
    "airtable experts": {"kind": "login", "notes": "Airtable expert profile."},
    "notion experts": {"kind": "login", "notes": "Notion expert profile."},
    "webflow experts": {"kind": "login", "notes": "Webflow expert profile."},
    "framer experts": {"kind": "login", "notes": "Framer expert profile."},
    "shopify experts": {"kind": "login", "notes": "Shopify expert profile."},
    "salesforce admin freelance": {"kind": "login", "notes": "Truelancer account."},
    "hubspot experts": {"kind": "login", "notes": "HubSpot partner profile."},
    "monday.com experts": {"kind": "login", "notes": "Monday.com expert profile."},
    "clickup experts": {"kind": "login", "notes": "ClickUp expert profile."},
    "asana experts": {"kind": "login", "notes": "Asana expert profile."},
    "smartsheet experts": {"kind": "login", "notes": "Smartsheet expert profile."},
    "airtable universe": {"kind": "login", "notes": "Airtable account."},
    "notion templates": {"kind": "login", "notes": "Notion account."},
    "zapier templates": {"kind": "none", "notes": "Public Zapier templates."},
    "make templates": {"kind": "none", "notes": "Public Make templates."},
    "n8n workflows": {"kind": "none", "notes": "Public n8n workflows."},
    "pipedream components": {"kind": "login", "notes": "Pipedream account."},
    "tray.io partners": {"kind": "login", "notes": "Tray.io partner profile."},
    "workato partners": {"kind": "login", "notes": "Workato partner profile."},
    "uipath partners": {"kind": "login", "notes": "UiPath partner profile."},
    "automation anywhere partners": {"kind": "login", "notes": "AA partner profile."},
    "blue prism partners": {"kind": "login", "notes": "Blue Prism partner profile."},
    "power automate experts": {"kind": "login", "notes": "Microsoft account."},
    "power bi experts": {"kind": "login", "notes": "Microsoft account."},
    "tableau experts": {"kind": "login", "notes": "Tableau account."},
    "looker experts": {"kind": "login", "notes": "Google account."},
    "mode experts": {"kind": "login", "notes": "Mode account."},
    "sigma computing": {"kind": "login", "notes": "Sigma account."},
    "hex experts": {"kind": "login", "notes": "Hex account."},
    "workana es": {"kind": "login", "notes": "Workana account."},
    "freelancer es": {"kind": "login", "notes": "Freelancer.com account."},
    "soyfreelancer": {"kind": "login", "notes": "SoyFreelancer account."},
    "freelance es jobs": {"kind": "login", "notes": "InfoJobs account."},
    "ticjob": {"kind": "login", "notes": "Ticjob account."},
    "manfred": {"kind": "login", "notes": "Manfred account."},
    "toroe es tech": {"kind": "login", "notes": "Toroe account."},
    "technojobs": {"kind": "login", "notes": "Technojobs account."},
    "empleo it": {"kind": "login", "notes": "EmpleoIT account."},
    "infoempleo": {"kind": "login", "notes": "Infoempleo account."},
    "tecnoempleo": {"kind": "login", "notes": "Tecnoempleo account."},
    "portal empleo": {"kind": "login", "notes": "Portal Empleo account."},
    "opcionempleo": {"kind": "login", "notes": "Opcionempleo account."},
    "trabajos.com": {"kind": "login", "notes": "Trabajos.com account."},
    "infojobs freelance": {"kind": "login", "notes": "InfoJobs account."},
    "get on board es": {"kind": "login", "notes": "Get on Board profile."},
    "bumeran es": {"kind": "login", "notes": "Bumeran account."},
    "zonajobs es": {"kind": "login", "notes": "ZonaJobs account."},
    "computrabajo es": {"kind": "login", "notes": "Computrabajo account."},
    "elempleo": {"kind": "login", "notes": "Elempleo account."},
    "computrabajo co": {"kind": "login", "notes": "Computrabajo CO account."},
    "occ mundial": {"kind": "login", "notes": "OCC account."},
    "computrabajo mx": {"kind": "login", "notes": "Computrabajo MX account."},
    "bumeran mx": {"kind": "login", "notes": "Bumeran MX account."},
    "el empleo": {"kind": "login", "notes": "El Empleo account."},
    "laborum chile": {"kind": "login", "notes": "Laborum account."},
    "computrabajo cl": {"kind": "login", "notes": "Computrabajo CL account."},
    "trabajando.cl": {"kind": "login", "notes": "Trabajando account."},
    "opcionempleo cl": {"kind": "login", "notes": "Opcionempleo CL account."},
    "linkedin es": {"kind": "login", "notes": "LinkedIn account."},
    "indeed es": {"kind": "login", "notes": "Indeed account."},
    "glassdoor es": {"kind": "login", "notes": "Glassdoor account."},
    "laborx crypto": {"kind": "login", "notes": "LaborX account."},
    "timebucks": {"kind": "login", "notes": "TimeBucks account."},
    "bituro": {"kind": "login", "notes": "Bituro account."},
    "coinpayu": {"kind": "login", "notes": "Coinpayu account."},
    "packetstream": {"kind": "login", "notes": "PacketStream account."},
    "honeygain": {"kind": "login", "notes": "Honeygain account."},
    "traffmonetizer": {"kind": "login", "notes": "Traffmonetizer account."},
    "earnapp": {"kind": "login", "notes": "EarnApp account."},
    "repocket": {"kind": "login", "notes": "Repocket account."},
    "peer2profit": {"kind": "login", "notes": "Peer2Profit account."},
    "iproyal pawns": {"kind": "login", "notes": "IPRoyal Pawns account."},
    "grass": {"kind": "login", "notes": "Grass account."},
    "nodepay": {"kind": "login", "notes": "Nodepay account."},
    "gradient network": {"kind": "login", "notes": "Gradient account."},
    "geodnet": {"kind": "login", "notes": "Geodnet account."},
    "hivemapper": {"kind": "login", "notes": "Hivemapper account."},
    "pi network": {"kind": "login", "notes": "Pi Network account."},
    "presearch": {"kind": "login", "notes": "Presearch account."},
    "storm gain": {"kind": "login", "notes": "StormGain account."},
    "phemex earn": {"kind": "login", "notes": "Phemex account."},
    "bybit earn": {"kind": "login", "notes": "Bybit account."},
    "okx earn": {"kind": "login", "notes": "OKX account."},
    "gate.io earn": {"kind": "login", "notes": "Gate.io account."},
    "mexc earn": {"kind": "login", "notes": "MEXC account."},
    "kucoin earn": {"kind": "login", "notes": "KuCoin account."},
    "bitget earn": {"kind": "login", "notes": "Bitget account."},
    "htx earn": {"kind": "login", "notes": "HTX account."},
    "crypto.com earn": {"kind": "login", "notes": "Crypto.com account."},
    "coinbase earn": {"kind": "login", "notes": "Coinbase account."},
    "binance learn": {"kind": "login", "notes": "Binance account."},
    "kraken learn": {"kind": "login", "notes": "Kraken account."},
    "gemini earn": {"kind": "login", "notes": "Gemini account."},
    "qa freelance": {"kind": "login", "notes": "Truelancer account."},
    "selenium freelance": {"kind": "login", "notes": "Truelancer account."},
    "cypress freelance": {"kind": "login", "notes": "Truelancer account."},
    "playwright experts": {"kind": "none", "notes": "Public Playwright community."},
    "cypress community": {"kind": "none", "notes": "Public Cypress community."},
    "selenium community": {"kind": "none", "notes": "Public Selenium community."},
    "appium community": {"kind": "none", "notes": "Public Appium community."},
    "test automation university": {"kind": "none", "notes": "Public TAU."},
    "ministry of testing": {"kind": "login", "notes": "MOT community account."},
    "qa job board": {"kind": "none", "notes": "Public QA job board."},
    "testing job board": {"kind": "none", "notes": "Public testing job board."},
    "seleniumconf jobs": {"kind": "none", "notes": "Public SeleniumConf listings."},
    "testmu ai": {"kind": "login", "notes": "TestMu AI account."},
    "katalon community": {"kind": "login", "notes": "Katalon account."},
    "testrail jobs": {"kind": "login", "notes": "TestRail account."},
    "browserstack jobs": {"kind": "login", "notes": "BrowserStack account."},
    "sauce labs jobs": {"kind": "login", "notes": "Sauce Labs account."},
    "lambdatest jobs": {"kind": "login", "notes": "LambdaTest account."},
    "applitools jobs": {"kind": "login", "notes": "Applitools account."},
    "mabl jobs": {"kind": "login", "notes": "Mabl account."},
    "testim jobs": {"kind": "login", "notes": "Testim account."},
    "tricentis jobs": {"kind": "login", "notes": "Tricentis account."},
    "ranorex jobs": {"kind": "login", "notes": "Ranorex account."},
    "smartbear jobs": {"kind": "login", "notes": "SmartBear account."},
    "soapui jobs": {"kind": "login", "notes": "SmartBear account."},
    "postman jobs": {"kind": "login", "notes": "Postman account."},
    "insomnia jobs": {"kind": "none", "notes": "Public Insomnia community."},
    "hoppscotch jobs": {"kind": "none", "notes": "Public Hoppscotch community."},
    "httpie jobs": {"kind": "none", "notes": "Public HTTPie community."},
    "bruno jobs": {"kind": "none", "notes": "Public Bruno community."},
    "yaak jobs": {"kind": "none", "notes": "Public Yaak community."},
    "airflow freelance": {"kind": "login", "notes": "Truelancer account."},
    "dbt freelance": {"kind": "login", "notes": "Truelancer account."},
    "spark freelance": {"kind": "login", "notes": "Truelancer account."},
    "snowflake freelance": {"kind": "login", "notes": "Truelancer account."},
    "databricks freelance": {"kind": "login", "notes": "Truelancer account."},
    "fivetran freelance": {"kind": "login", "notes": "Truelancer account."},
    "airbyte freelance": {"kind": "login", "notes": "Truelancer account."},
    "kafka freelance": {"kind": "login", "notes": "Truelancer account."},
    "dbt community": {"kind": "login", "notes": "dbt Community account."},
    "airflow community": {"kind": "none", "notes": "Public Airflow community."},
    "prefect community": {"kind": "login", "notes": "Prefect account."},
    "dagster community": {"kind": "login", "notes": "Dagster account."},
    "astronomer jobs": {"kind": "login", "notes": "Astronomer account."},
    "dbt labs jobs": {"kind": "login", "notes": "dbt Labs account."},
    "fivetran jobs": {"kind": "login", "notes": "Fivetran account."},
    "airbyte jobs": {"kind": "login", "notes": "Airbyte account."},
    "snowflake jobs": {"kind": "login", "notes": "Snowflake account."},
    "databricks jobs": {"kind": "login", "notes": "Databricks account."},
    "confluent data": {"kind": "login", "notes": "Confluent account."},
    "elastic data": {"kind": "login", "notes": "Elastic account."},
    "mongodb jobs": {"kind": "login", "notes": "MongoDB account."},
    "redis jobs": {"kind": "login", "notes": "Redis account."},
    "clickhouse jobs": {"kind": "login", "notes": "ClickHouse account."},
    "duckdb jobs": {"kind": "none", "notes": "Public DuckDB community."},
    "motherduck jobs": {"kind": "login", "notes": "MotherDuck account."},
    "singlestore jobs": {"kind": "login", "notes": "SingleStore account."},
    "cockroachdb jobs": {"kind": "login", "notes": "CockroachDB account."},
    "planetscale jobs": {"kind": "login", "notes": "PlanetScale account."},
    "neon jobs": {"kind": "login", "notes": "Neon account."},
    "supabase jobs": {"kind": "login", "notes": "Supabase account."},
    "firebase jobs": {"kind": "login", "notes": "Google account."},
    "hasura jobs": {"kind": "login", "notes": "Hasura account."},
    "postgraphile jobs": {"kind": "none", "notes": "Public PostGraphile community."},
    "langchain freelance": {"kind": "login", "notes": "Truelancer account."},
    "openai freelance": {"kind": "login", "notes": "Truelancer account."},
    "rag freelance": {"kind": "login", "notes": "Truelancer account."},
    "vector db freelance": {"kind": "login", "notes": "Truelancer account."},
    "prompt engineering freelance": {"kind": "login", "notes": "Truelancer account."},
    "agent freelance": {"kind": "login", "notes": "Truelancer account."},
    "crewai freelance": {"kind": "login", "notes": "Truelancer account."},
    "autogen freelance": {"kind": "login", "notes": "Truelancer account."},
    "langgraph freelance": {"kind": "login", "notes": "Truelancer account."},
    "llamaindex freelance": {"kind": "login", "notes": "Truelancer account."},
    "hugging face freelance": {"kind": "login", "notes": "Truelancer account."},
    "pytorch freelance": {"kind": "login", "notes": "Truelancer account."},
    "tensorflow freelance": {"kind": "login", "notes": "Truelancer account."},
    "ml freelance": {"kind": "login", "notes": "Truelancer account."},
    "ai freelance": {"kind": "login", "notes": "Truelancer account."},
    "chatgpt integration": {"kind": "login", "notes": "Truelancer account."},
    "gemini integration": {"kind": "login", "notes": "Truelancer account."},
    "claude integration": {"kind": "login", "notes": "Truelancer account."},
    "ollama integration": {"kind": "login", "notes": "Truelancer account."},
    "vllm freelance": {"kind": "login", "notes": "Truelancer account."},
    "whisper freelance": {"kind": "login", "notes": "Truelancer account."},
    "stable diffusion freelance": {"kind": "login", "notes": "Truelancer account."},
    "comfyui freelance": {"kind": "login", "notes": "Truelancer account."},
    "automatic1111 freelance": {"kind": "login", "notes": "Truelancer account."},
    "llm evaluation freelance": {"kind": "login", "notes": "Truelancer account."},
    "ai red team freelance": {"kind": "login", "notes": "Truelancer account."},
    "ai safety freelance": {"kind": "login", "notes": "Truelancer account."},
    "rlhf freelance": {"kind": "login", "notes": "Truelancer account."},
    "fine-tuning freelance": {"kind": "login", "notes": "Truelancer account."},
    "lora freelance": {"kind": "login", "notes": "Truelancer account."},
    "quantization freelance": {"kind": "login", "notes": "Truelancer account."},
    "onnx freelance": {"kind": "login", "notes": "Truelancer account."},
    "tensorrt freelance": {"kind": "login", "notes": "Truelancer account."},
    "edge ai freelance": {"kind": "login", "notes": "Truelancer account."},
    "mlops freelance": {"kind": "login", "notes": "Truelancer account."},
    "llmops freelance": {"kind": "login", "notes": "Truelancer account."},
    "ai agent freelance": {"kind": "login", "notes": "Truelancer account."},
    "multi-agent freelance": {"kind": "login", "notes": "Truelancer account."},
    "agent evaluation freelance": {"kind": "login", "notes": "Truelancer account."},
    "swarm freelance": {"kind": "login", "notes": "Truelancer account."},
    "memory freelance": {"kind": "login", "notes": "Truelancer account."},
    "tool-use freelance": {"kind": "login", "notes": "Truelancer account."},
    "browser-agent freelance": {"kind": "login", "notes": "Truelancer account."},
    "computer-use freelance": {"kind": "login", "notes": "Truelancer account."},
    "gui-agent freelance": {"kind": "login", "notes": "Truelancer account."},
}


def get_credential_requirement(source: SourceDefinition | str) -> dict[str, Any] | None:
    """Credential requirement for a source, if any."""
    name = source.name if isinstance(source, SourceDefinition) else str(source)
    low = name.strip().lower()
    # Exact match first, then prefix match.
    if low in CREDENTIAL_REQUIREMENTS:
        return CREDENTIAL_REQUIREMENTS[low]
    for key, req in CREDENTIAL_REQUIREMENTS.items():
        if low.startswith(key):
            return req
    # Fallback: requires_account sources default to 'login' unless public board.
    if isinstance(source, SourceDefinition):
        if not source.requires_account:
            return {"kind": "none", "notes": "Public source; no login needed."}
        return {
            "kind": "login",
            "notes": "Account required; credential not yet mapped — configure manually.",
        }
    return None


def get_source_status(source: SourceDefinition | str) -> dict[str, Any]:
    """Full status snapshot for a source: credentials + payment fallback."""
    return {
        "source": source.name if isinstance(source, SourceDefinition) else str(source),
        "credentials": get_credential_requirement(source),
        "payment_fallback": get_payment_fallback(source),
        "fallback_chain": [s.name for s in get_fallback_chain(source)],
    }


def sources_for_scan(
    *,
    eligible_only: bool = True,
    cap: int = MAX_TOTAL_SOURCES,
) -> list[SourceDefinition]:
    """Sources prioritized for scanning.

    When ``eligible_only`` (default), drops sources that hard-require
    portfolio/interview/experience AND excludes Upwork per policy.
    Ordered by (priority desc, quality_score desc); capped at ``cap``.
    """
    pool = [s for s in get_all_sources() if not s.name.lower().startswith("upwork")]
    if eligible_only:
        pool = [s for s in pool if not (s.requires_portfolio or s.requires_interview or s.requires_experience)]
    pool.sort(key=lambda s: (s.priority, s.quality_score), reverse=True)
    return pool[:cap]
