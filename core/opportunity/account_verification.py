"""Account Verification Flow — per-platform reusable verification state machine.

Guided Earning Fase 1.1. One verified account unlocks every opportunity on
that platform, so verification state is keyed by PLATFORM, not by item.

Stages (append-only events, never overwritten):
  REQUIREMENTS_CHECK → REGISTRATION_READY → REGISTRATION_STARTED →
  ACCOUNT_CREATED → EMAIL_VERIFICATION → IDENTITY_VERIFICATION →
  ACCESS_CHECK → ACCOUNT_ACCESS_CONFIRMED → PAYOUT_CHECK →
  FULLY_CONFIGURED | PARTIALLY_CONFIGURED | BLOCKED

Honesty rules:
- OWNER_CONFIRMED is not API verification — the method is recorded.
- UNKNOWN never becomes PASS.
- No credentials, MFA codes, or KYC documents are stored here.
- Research fields are populated from the source registry / payment docs,
  labeled with their evidence; gaps stay UNKNOWN.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STAGES = [
    "REQUIREMENTS_CHECK",
    "REGISTRATION_READY",
    "REGISTRATION_STARTED",
    "ACCOUNT_CREATED",
    "EMAIL_VERIFICATION",
    "IDENTITY_VERIFICATION",
    "ACCESS_CHECK",
    "ACCOUNT_ACCESS_CONFIRMED",
    "PAYOUT_CHECK",
]

TERMINAL_STATES = {"FULLY_CONFIGURED", "PARTIALLY_CONFIGURED", "BLOCKED"}

# Fields the owner (or an authorized integration) can confirm.
CONFIRMABLE = {
    "registration_status",
    "email_status",
    "identity_status",
    "access_status",
    "payout_status",
}

# Canonical vocabularies per field (spec §5-9)
FIELD_VALUES = {
    "registration_status": {
        "REGISTRATION_SUPPORTED",
        "REGISTRATION_CONDITIONAL",
        "REGISTRATION_UNKNOWN",
        "REGISTRATION_UNAVAILABLE",
        "REGISTRATION_READY",
        "REGISTRATION_STARTED",
    },
    "email_status": {
        "EMAIL_NOT_VERIFIED",
        "EMAIL_USER_CONFIRMED",
        "EMAIL_VERIFIED",
        "EMAIL_VERIFICATION_FAILED",
    },
    "identity_status": {
        "KYC_NOT_REQUIRED",
        "KYC_REQUIRED",
        "KYC_IN_PROGRESS",
        "KYC_USER_CONFIRMED",
        "KYC_VERIFIED",
        "KYC_REJECTED",
        "KYC_UNKNOWN",
    },
    "access_status": {
        "ACCOUNT_CREATED",
        "ACCOUNT_VERIFIED",
        "ACCOUNT_ACTIVE",
        "DASHBOARD_ACCESS_CONFIRMED",
        "TASK_ACCESS_CONFIRMED",
        "ACCESS_RESTRICTED",
        "ACCESS_UNKNOWN",
    },
    "payout_status": {
        "PAYOUT_METHOD_UNKNOWN",
        "PAYOUT_METHOD_CONFIGURED",
        "PAYOUT_COMPATIBLE_AR",
        "PAYOUT_INCOMPATIBLE",
        "PAYOUT_UNVERIFIED",
    },
}

# Which confirmations count as "done enough" per field for the checklist.
_DONE_VALUES = {
    "registration_status": {"REGISTRATION_STARTED"},
    "email_status": {"EMAIL_USER_CONFIRMED", "EMAIL_VERIFIED"},
    "identity_status": {"KYC_NOT_REQUIRED", "KYC_USER_CONFIRMED", "KYC_VERIFIED"},
    "access_status": {"ACCOUNT_ACTIVE", "DASHBOARD_ACCESS_CONFIRMED", "TASK_ACCESS_CONFIRMED", "ACCOUNT_VERIFIED"},
    "payout_status": {"PAYOUT_METHOD_CONFIGURED", "PAYOUT_COMPATIBLE_AR"},
}

# Stage each field belongs to, for progress display.
_FIELD_STAGE = {
    "registration_status": "REGISTRATION_READY",
    "email_status": "EMAIL_VERIFICATION",
    "identity_status": "IDENTITY_VERIFICATION",
    "access_status": "ACCESS_CHECK",
    "payout_status": "PAYOUT_CHECK",
}


def _norm(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def _store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "account_verifications.json"


def _load() -> dict[str, Any]:
    path = _store_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _blank(platform: str) -> dict[str, Any]:
    return {
        "platform": platform,
        "stage": "REQUIREMENTS_CHECK",
        "account_status": "ACCOUNT_UNKNOWN",
        "registration_status": "REGISTRATION_UNKNOWN",
        "email_status": "EMAIL_NOT_VERIFIED",
        "identity_status": "KYC_UNKNOWN",
        "access_status": "ACCESS_UNKNOWN",
        "payout_status": "PAYOUT_UNVERIFIED",
        "paused": False,
        "last_checked_at": None,
        "verification_method": "OWNER_CONFIRMED",
        "evidence_refs": [],
        "next_action_id": None,
        "events": [],
        "created_at": _now(),
        "updated_at": _now(),
    }


def _event(rec: dict[str, Any], event_type: str, actor: str, notes: str = "", evidence_ref: str = "") -> None:
    rec["events"].append(
        {
            "id": f"evt-{len(rec['events']) + 1:04d}",
            "verification_id": rec["platform"],
            "event_type": event_type,
            "actor": actor,
            "timestamp": _now(),
            "notes": notes,
            "evidence_ref": evidence_ref,
        }
    )


def get_verification(platform: str) -> dict[str, Any]:
    """Return the verification record for a platform (created on demand)."""
    data = _load()
    key = _norm(platform)
    rec = data.get(key)
    if rec is None:
        rec = _blank(platform)
        data[key] = rec
        _save(data)
    return rec


def _research(platform: str) -> dict[str, Any]:
    """Pre-registration research from real registry data — never invented."""
    research: dict[str, Any] = {
        "argentina_compatible": "unknown",
        "requires_account": "unknown",
        "requires_assessment": "unknown",
        "payment_methods_documented": [],
        "payment_note": None,
        "payment_owner_note": None,
        "source_url": "",
        "evidence": "UNKNOWN",
    }
    try:
        from cores.opportunity.global_sources import get_base_sources, get_sources

        for s in list(get_sources()) + list(get_base_sources()):
            if _norm(s.name) == _norm(platform) or _norm(platform) in _norm(s.name) or _norm(s.name) in _norm(platform):
                research["source_url"] = s.url or ""
                research["requires_account"] = "yes" if s.requires_account else "no"
                research["requires_assessment"] = "yes" if s.requires_assessment else "no"
                research["argentina_compatible"] = "yes" if s.argentina_ok else "no" if s.argentina_ok is False else "unknown"
                research["evidence"] = "VERIFIED_BY_OWNEX"
                break
    except Exception:
        pass
    try:
        from cores.opportunity.source_payment_docs import KNOWN_PAYMENT_METHODS

        for name, doc in KNOWN_PAYMENT_METHODS.items():
            n = _norm(name)
            if n == _norm(platform) or (n and (n in _norm(platform) or _norm(platform) in n)):
                research["payment_methods_documented"] = doc.get("methods") or []
                research["payment_note"] = doc.get("note")
                research["payment_owner_note"] = doc.get("owner_note")
                break
    except Exception:
        pass
    return research


def _derive_stage(rec: dict[str, Any]) -> str:
    """Compute the effective stage from field statuses (events stay append-only)."""
    if rec.get("payout_status") in ("PAYOUT_COMPATIBLE_AR", "PAYOUT_METHOD_CONFIGURED") and rec.get("access_status") in _DONE_VALUES["access_status"]:
        return "FULLY_CONFIGURED"
    if rec.get("access_status") in ("ACCESS_RESTRICTED",):
        return "BLOCKED"
    if rec.get("access_status") in _DONE_VALUES["access_status"]:
        return "PARTIALLY_CONFIGURED"
    if rec.get("account_status") in ("ACCOUNT_CREATED", "ACCOUNT_VERIFIED", "ACCOUNT_ACTIVE") or rec.get("email_status") in _DONE_VALUES["email_status"]:
        return "ACCOUNT_CREATED"
    if rec.get("registration_status") == "REGISTRATION_STARTED":
        return "REGISTRATION_STARTED"
    return "REQUIREMENTS_CHECK"


def verification_view(platform: str) -> dict[str, Any]:
    """Full view: record + derived research + checklist + stage."""
    rec = get_verification(platform)
    research = _research(platform)

    # Checklist: the 6 config areas from the spec.
    checklist = [
        {"key": "eligibility", "label": "País y elegibilidad", "status": research["argentina_compatible"].upper(), "evidence": research["evidence"]},
        {
            "key": "registration_reqs",
            "label": "Requisitos de registro",
            "status": rec["registration_status"],
            "evidence": "VERIFIED_BY_OWNEX" if research["source_url"] else "UNKNOWN",
        },
        {
            "key": "account",
            "label": "Creación de cuenta",
            "status": rec["registration_status"] if rec["registration_status"] == "REGISTRATION_STARTED" else "PENDING",
            "evidence": "OWNER_CONFIRMED" if rec["registration_status"] == "REGISTRATION_STARTED" else "UNKNOWN",
        },
        {"key": "email_identity", "label": "Correo e identidad", "status": rec["email_status"], "sub": rec["identity_status"], "evidence": "OWNER_CONFIRMED"},
        {"key": "task_access", "label": "Acceso a oportunidades", "status": rec["access_status"], "evidence": "OWNER_CONFIRMED"},
        {
            "key": "payout",
            "label": "Método de cobro",
            "status": rec["payout_status"],
            "evidence": "VERIFIED_BY_OWNEX" if research["payment_methods_documented"] else "UNKNOWN",
        },
    ]

    stage = _derive_stage(rec)
    rec["stage"] = stage
    return {
        "platform": platform,
        "stage": stage,
        "paused": rec["paused"],
        "checklist": checklist,
        "research": research,
        "statuses": {k: rec[k] for k in CONFIRMABLE},
        "account_status": rec["account_status"],
        "last_checked_at": rec["last_checked_at"],
        "verification_method": rec["verification_method"],
        "evidence_refs": rec["evidence_refs"],
        "events": rec["events"],
        "created_at": rec["created_at"],
        "updated_at": rec["updated_at"],
        "guide": _platform_guide(platform),
    }


def _platform_guide(platform: str) -> dict[str, Any] | None:
    try:
        from core.opportunity.guides.platform_guides import get_platform_guide

        g = get_platform_guide(platform)
        if g is None:
            return None
        return {
            "name": g.name,
            "url": g.url,
            "account_steps": [{"title": s.title, "description": s.description, "url": s.url} for s in g.account_creation],
            "evidence": "AI_GENERATED_GUIDANCE",
        }
    except Exception:
        return None


def confirm(
    platform: str, field: str, value: str, *, actor: str = "OWNER", method: str = "OWNER_CONFIRMED", evidence_ref: str = "", notes: str = ""
) -> dict[str, Any]:
    """Record a status confirmation. Validates field/value vocabularies."""
    if field not in CONFIRMABLE:
        raise ValueError(f"unknown field {field!r}; expected one of {sorted(CONFIRMABLE)}")
    allowed = FIELD_VALUES[field]
    if value not in allowed:
        raise ValueError(f"invalid value {value!r} for {field}; allowed: {sorted(allowed)}")

    data = _load()
    key = _norm(platform)
    rec = data.setdefault(key, _blank(platform))
    previous = rec.get(field)
    rec[field] = value
    rec["last_checked_at"] = _now()
    rec["verification_method"] = method
    if evidence_ref and evidence_ref not in rec["evidence_refs"]:
        rec["evidence_refs"].append(evidence_ref)
    rec["stage"] = _derive_stage(rec)
    rec["updated_at"] = _now()
    _event(
        rec,
        "STATUS_CONFIRMED",
        actor,
        notes=notes or f"{field}: {previous} -> {value}",
        evidence_ref=evidence_ref,
    )
    _event(rec, f"{field.upper()}_SET", actor, notes=f"now {value}")
    _save(data)
    return rec


def set_paused(platform: str, paused: bool, actor: str = "OWNER") -> dict[str, Any]:
    data = _load()
    key = _norm(platform)
    rec = data.setdefault(key, _blank(platform))
    rec["paused"] = paused
    rec["updated_at"] = _now()
    _event(rec, "PAUSED" if paused else "RESUMED", actor)
    _save(data)
    return rec


def is_platform_verified(platform: str) -> bool:
    """True when account access is confirmed well enough to unblock work.

    OWNER_CONFIRMED counts (it is recorded as such, not as API-verified);
    UNKNOWN/RESTRICTED never count.
    """
    rec = get_verification(platform)
    return rec.get("access_status") in _DONE_VALUES["access_status"] and not rec.get("paused", False)


def list_verifications() -> list[dict[str, Any]]:
    data = _load()
    return [verification_view(_display_name(k, v)) for k, v in data.items()]


def _display_name(key: str, rec: dict[str, Any]) -> str:
    return rec.get("platform") or key
