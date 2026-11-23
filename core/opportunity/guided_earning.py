"""Guided Earning System — turn an opportunity into an executable procedure.

This module is an ORIENTATION LAYER over existing infrastructure (Work Bank,
platform guides, payment docs, execution queue). It never invents URLs,
credentials, or payment methods: every link comes from the source registry,
the platform guide registry, or the opportunity record itself. Steps that
cannot be backed by evidence are labeled accordingly.

Actors:
  HUMAN_REQUIRED      — only the owner can do it (signup, KYC, submit, approve)
  OWNEX_AUTOMATED     — OWNEX can do it inside an authorized environment
  OWNEX_ASSISTED      — OWNEX prepares, owner confirms/executes the final act
  EXTERNAL_WAITING    — waiting on the platform (review, acceptance, payout)
  BLOCKED             — cannot proceed until a dependency is resolved
  VERIFIED_COMPLETED  — done with recorded evidence

Evidence labels:
  VERIFIED_OFFICIAL / VERIFIED_BY_API / VERIFIED_BY_OWNEX / OWNER_CONFIRMED /
  AI_GENERATED_GUIDANCE / ESTIMATED / UNKNOWN / EXPIRED
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.direct_work_engine.workbank import WorkItem, get_workbank


class Actor(StrEnum):
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    OWNEX_AUTOMATED = "OWNEX_AUTOMATED"
    OWNEX_ASSISTED = "OWNEX_ASSISTED"
    EXTERNAL_WAITING = "EXTERNAL_WAITING"
    BLOCKED = "BLOCKED"
    VERIFIED_COMPLETED = "VERIFIED_COMPLETED"


class Evidence(StrEnum):
    VERIFIED_OFFICIAL = "VERIFIED_OFFICIAL"
    VERIFIED_BY_API = "VERIFIED_BY_API"
    VERIFIED_BY_OWNEX = "VERIFIED_BY_OWNEX"
    OWNER_CONFIRMED = "OWNER_CONFIRMED"
    AI_GENERATED_GUIDANCE = "AI_GENERATED_GUIDANCE"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"
    EXPIRED = "EXPIRED"


# Canonical execution stages, in dependency order. The builder fills each
# with real data; stages that do not apply are marked SKIPPED with a reason.
STAGE_ORDER = [
    "verify-availability",
    "platform-access",
    "prepare-work",
    "review-deliverables",
    "submit-work",
    "track-acceptance",
    "verify-payment",
]

_TERMINAL_ITEM_STATES = {"delivered"}


def _store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[2] / "data"
    return root / "guided_earning.json"


def _load_progress() -> dict[str, Any]:
    path = _store_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_progress(data: dict[str, Any]) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _norm(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


_PLATFORM_GUIDE_CACHE: dict[str, Any] | None = None


def _platform_guide(platform: str) -> Any | None:
    """Look up the curated step-by-step guide for a platform, if one exists."""
    global _PLATFORM_GUIDE_CACHE
    if _PLATFORM_GUIDE_CACHE is None:
        from core.opportunity.guides.platform_guides import PLATFORM_GUIDES

        _PLATFORM_GUIDE_CACHE = {_norm(k): v for k, v in PLATFORM_GUIDES.items()}
    return _PLATFORM_GUIDE_CACHE.get(_norm(platform))


_SOURCE_URL_CACHE: dict[str, str] | None = None


def _source_url(platform: str) -> str:
    """Official base URL for a platform from the curated source registry."""
    global _SOURCE_URL_CACHE
    if _SOURCE_URL_CACHE is None:
        try:
            from cores.opportunity.global_sources import get_base_sources, get_sources

            sources = list(get_sources()) + list(get_base_sources())
            _SOURCE_URL_CACHE = {_norm(s.name): s.url for s in sources if getattr(s, "url", "")}
        except Exception:
            _SOURCE_URL_CACHE = {}
    return _SOURCE_URL_CACHE.get(_norm(platform), "")


def _payment_doc(platform: str) -> dict[str, Any] | None:
    from cores.opportunity.source_payment_docs import KNOWN_PAYMENT_METHODS

    docs = KNOWN_PAYMENT_METHODS
    key = _norm(platform)
    for name, doc in docs.items():
        if _norm(name) == key:
            return doc
    # Some platforms are registered under a different display name.
    for name, doc in docs.items():
        if key and (key in _norm(name) or _norm(name) in key):
            return doc
    return None


def _safe_url(url: str) -> str:
    """Only http(s) URLs may be shown as clickable links."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url or "")
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return url
    except Exception:
        pass
    return ""


def _step(
    step_id: str,
    title: str,
    instruction: str,
    actor: Actor,
    *,
    url: str = "",
    evidence: Evidence = Evidence.AI_GENERATED_GUIDANCE,
    detail: str = "",
) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "instruction": instruction,
        "actor": str(actor),
        "actor_label": {
            Actor.HUMAN_REQUIRED: "Requiere acción tuya",
            Actor.OWNEX_AUTOMATED: "OWNEX lo ejecuta",
            Actor.OWNEX_ASSISTED: "OWNEX prepara, vos confirmás",
            Actor.EXTERNAL_WAITING: "Esperando a la plataforma",
            Actor.BLOCKED: "Bloqueado",
            Actor.VERIFIED_COMPLETED: "Completado con evidencia",
        }[actor],
        "url": _safe_url(url),
        "evidence": str(evidence),
        "detail": detail,
    }


def _access_steps(item: WorkItem) -> list[dict[str, Any]]:
    """Steps to reach a workable state on the platform."""
    guide = _platform_guide(item.platform)
    platform_url = (guide.url if guide else "") or _source_url(item.platform)
    access = item.access_status or "unknown"

    if access in ("public", "api", "rss"):
        return [
            _step(
                "platform-access",
                "Acceso a la plataforma",
                "Esta fuente es de acceso público o por API: no hace falta crear cuenta para ver la oportunidad. "
                "OWNEX ya recolectó la publicación; verificá que siga vigente antes de trabajar.",
                Actor.OWNEX_ASSISTED,
                url=platform_url,
                evidence=Evidence.VERIFIED_BY_OWNEX,
                detail=f"access_status={access}",
            )
        ]

    requirement = item.access_requirement or "Se requiere configuración manual de acceso."
    steps = [
        _step(
            "platform-access",
            f"Conseguir acceso en {item.platform}",
            requirement,
            Actor.HUMAN_REQUIRED,
            url=platform_url,
            evidence=Evidence.VERIFIED_BY_OWNEX,
            detail="Solo vos podés registrar la cuenta o cargar credenciales. OWNEX nunca registra ni firma en tu nombre.",
        )
    ]
    if guide:
        steps.append(
            _step(
                "platform-access-guide",
                f"Guía paso a paso de {guide.name}",
                "Seguí la guía oficial de OWNEX para crear la cuenta en la plataforma.",
                Actor.HUMAN_REQUIRED,
                url=platform_url,
                evidence=Evidence.AI_GENERATED_GUIDANCE,
                detail="Pasos UI-level para registro; pueden quedar desactualizados si la plataforma cambia su UI.",
            )
        )
    return steps


def _payment_guide(item: WorkItem) -> dict[str, Any]:
    doc = _payment_doc(item.platform)
    methods = doc.get("methods") if doc else None
    return {
        "reward_reported": item.reward if item.reward else None,
        "reward_caveat": "Recompensa anunciada por la fuente; no implica financiación ni pago confirmado.",
        "payout_method_suggested": item.payout_method or None,
        "payout_rationale": item.payout_method_rationale or None,
        "documented_methods": methods or [],
        "documentation_note": (doc or {}).get("note"),
        "owner_note": (doc or {}).get("owner_note"),
        "evidence": Evidence.VERIFIED_BY_OWNEX if doc else Evidence.UNKNOWN,
        "payment_verified": False,
        "guide": [
            "Después de la aceptación de la plataforma, verificá el estado del pago en el panel de la fuente.",
            "Registrá la evidencia de pago en OWNEX (Revenue Ledger) solo cuando el dinero esté efectivamente recibido.",
            "Una PR mergeada o una entrega aceptada NO equivale a pago.",
        ],
    }


def build_execution_guide(item: WorkItem, progress: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the full Opportunity Execution Guide for one Work Bank item."""
    progress = progress or {}
    completed: set[str] = set(progress.get("completed_steps", []))
    item_done = item.status in _TERMINAL_ITEM_STATES

    guide = _platform_guide(item.platform)
    platform_url = (guide.url if guide else "") or _source_url(item.platform)
    opportunity_url = _safe_url(item.url)

    # ── A. Overview ──
    overview = {
        "id": item.id,
        "title": item.title,
        "platform": item.platform,
        "description": item.description or "",
        "reward": item.reward or None,
        "reward_currency": "UNKNOWN",
        "category": item.category,
        "employment_type": item.employment_type,
        "difficulty": "unknown",
        "estimated_hours": None,
        "barrier_score": item.barrier_score,
        "status": item.status,
        "access_status": item.access_status,
        "created_at": item.created_at,
        "evidence": Evidence.VERIFIED_BY_OWNEX,
    }

    # ── B. Why this opportunity ──
    why = {
        "recommendation_reason": (
            "Seleccionada por el Work Bank por baja barrera de acceso" + (f" (barrier_score={item.barrier_score})" if item.barrier_score else "") + "."
        ),
        "requirements_met": ["Oportunidad indexada por OWNEX", "Sin portfolio ni entrevista obligatoria según filtros del banco"],
        "requirements_pending": [item.access_requirement] if item.access_status not in ("public", "api", "rss") else [],
        "advantages": ["Preparación automática de entregables por OWNEX", "Seguimiento de entrega y pago en el mismo lugar"],
        "disadvantages": ["Recompensa anunciada, no verificada", "Competencia y aceptación dependen de la plataforma"],
        "evidence": Evidence.AI_GENERATED_GUIDANCE,
    }

    # ── C. Where to go — only real URLs ──
    where = {
        "platform_name": item.platform,
        "platform_url": _safe_url(platform_url),
        "opportunity_url": opportunity_url,
        "register_url": "",
        "docs_url": "",
        "payment_url": "",
        "notes": "Los enlaces provienen del registro de fuentes de OWNEX o de la publicación original. "
        "OWNEX no inventa URLs de registro: si no hay enlace verificado, usá la URL oficial de la plataforma.",
        "evidence": Evidence.VERIFIED_BY_OWNEX if platform_url else Evidence.UNKNOWN,
    }
    if guide:
        where["guide_available"] = True
        where["guide_note"] = "Existe una guía UI-level curada para esta plataforma (registro y envío)."

    # ── D. Requirements ──
    requirements = {
        "account_needed": item.access_status not in ("public", "api", "rss"),
        "access_status": item.access_status,
        "access_requirement": item.access_requirement or None,
        "kyc": "unknown",
        "payout_method": item.payout_method or None,
        "tools": ["Navegador", "Git (para trabajo de código)"],
        "evidence": Evidence.VERIFIED_BY_OWNEX,
    }

    # ── E. Step-by-step instructions ──
    steps: list[dict[str, Any]] = []
    steps.append(
        _step(
            "verify-availability",
            "Verificar que la oportunidad sigue disponible",
            "Revisá la publicación original y confirmá que el bounty/trabajo sigue abierto y con la misma recompensa. "
            "OWNEX puede revalidarla; la decisión final es tuya.",
            Actor.OWNEX_ASSISTED,
            url=opportunity_url or platform_url,
            evidence=Evidence.VERIFIED_BY_API if opportunity_url else Evidence.AI_GENERATED_GUIDANCE,
        )
    )
    steps.extend(_access_steps(item))
    steps.extend(
        [
            _step(
                "prepare-work",
                "Dejar que OWNEX prepare el trabajo",
                "OWNEX genera el paquete de entrega local (borradores, análisis, archivos). No se envía nada sin tu aprobación.",
                Actor.OWNEX_AUTOMATED,
                evidence=Evidence.VERIFIED_BY_OWNEX,
                detail="Usa el botón 'Preparar paquete local' en esta ficha.",
            ),
            _step(
                "review-deliverables",
                "Revisar y aprobar la entrega",
                "Leé el paquete preparado, ajustá lo necesario y aprobá. La aprobación humana es obligatoria antes de cualquier envío.",
                Actor.HUMAN_REQUIRED,
                evidence=Evidence.OWNER_CONFIRMED,
            ),
            _step(
                "submit-work",
                "Enviar el trabajo en la plataforma",
                "Realizá el envío en la plataforma de origen siguiendo su formato. OWNEX puede asistir pero nunca envía en tu nombre sin autorización explícita.",
                Actor.HUMAN_REQUIRED if item.access_status not in ("public", "api", "rss") else Actor.OWNEX_ASSISTED,
                url=opportunity_url or platform_url,
                evidence=Evidence.AI_GENERATED_GUIDANCE,
                detail="Después de enviar, confirmalo en OWNEX para registrar la evidencia.",
            ),
            _step(
                "track-acceptance",
                "Seguir la aceptación",
                "Monitoreá el estado del trabajo en la plataforma (review → accepted/rejected). La aceptación no es pago.",
                Actor.EXTERNAL_WAITING,
                url=opportunity_url or platform_url,
                evidence=Evidence.AI_GENERATED_GUIDANCE,
            ),
            _step(
                "verify-payment",
                "Verificar y registrar el pago",
                "Cuando la plataforma confirme el pago, registrá la evidencia en el Revenue Ledger de OWNEX. Solo pagos con evidencia cuentan como ingresos verificados.",
                Actor.HUMAN_REQUIRED,
                evidence=Evidence.AI_GENERATED_GUIDANCE,
            ),
        ]
    )

    # Apply recorded progress: mark completed steps, collapse skipped stages.
    if item_done:
        for s in steps:
            if s["actor"] != str(Actor.EXTERNAL_WAITING):
                s["status"] = "completed"
                s["actor"] = str(Actor.VERIFIED_COMPLETED)
    else:
        access_ok = item.access_status in ("public", "api", "rss") or "platform-access" in completed
        for s in steps:
            if s["id"] in completed or s["id"] == "platform-access" and access_ok:
                s["status"] = "completed"
            elif s["id"] in ("prepare-work", "review-deliverables", "submit-work", "track-acceptance", "verify-payment") and not access_ok:
                s["status"] = "blocked"
                s["actor"] = str(Actor.BLOCKED)
            else:
                s["status"] = "pending"

    # ── F. Technical execution plan ──
    deliverables = item.deliverables or []
    technical = {
        "deliverables_identified": deliverables,
        "preparation": "OWNEX prepara un paquete local con borradores y análisis (AssistedExecutor). No ejecuta código externo sin aislamiento verificado.",
        "review_required": True,
        "submission_channel": item.platform,
        "evidence": Evidence.VERIFIED_BY_OWNEX,
    }
    if guide and guide.file_formats:
        technical["file_formats"] = guide.file_formats
        technical["file_formats_evidence"] = Evidence.AI_GENERATED_GUIDANCE

    # ── G. Submission guide ──
    submission = {
        "channel": "platform_ui",
        "channel_url": _safe_url(opportunity_url or platform_url),
        "format_notes": (guide.file_formats if guide else None) or "Verificá el formato exigido por la plataforma antes de enviar.",
        "must_include": ["Descripción clara del trabajo realizado", "Evidencia de tests/cambios cuando aplique"],
        "post_submission": "Guardá la confirmación de envío (URL, ID de submission) como evidencia.",
        "evidence": Evidence.AI_GENERATED_GUIDANCE,
    }

    # ── H. Payment guide ──
    payment = _payment_guide(item)

    done_count = sum(1 for s in steps if s.get("status") == "completed")
    next_step = next((s for s in steps if s.get("status") in ("pending", "blocked")), None)

    return {
        "guide_version": 1,
        "item_id": item.id,
        "generated_at": progress.get("updated_at"),
        "overview": overview,
        "why": why,
        "where_to_go": where,
        "requirements": requirements,
        "steps": steps,
        "technical_plan": technical,
        "submission_guide": submission,
        "payment_guide": payment,
        "progress": {
            "completed": done_count,
            "total": len(steps),
            "pct": round(100 * done_count / len(steps), 1) if steps else 0,
            "started_at": progress.get("started_at"),
            "updated_at": progress.get("updated_at"),
        },
        "next_step": next_step["id"] if next_step else None,
    }


def build_workspace(item: WorkItem, progress: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fase 2 — Guided Earning Workspace: one opportunity as an executable journey.

    Aggregates the execution guide with the platform account-verification
    state, the canonical journey position and the resume point. Read-only:
    all mutations still go through the existing step/verification endpoints.
    """
    from core.opportunity import account_verification as av

    progress = progress or {}
    guide = build_execution_guide(item, progress)
    verification = av.verification_view(item.platform)
    journey = _journey_stage(item, progress)

    access_blocked = item.access_status not in ("public", "api", "rss") and not av.is_platform_verified(item.platform)
    blockers: list[dict[str, Any]] = []
    if access_blocked:
        blockers.append(
            {
                "kind": "account_access",
                "label": "Acceso a la plataforma sin verificar",
                "resolution": "verification",
                "verification_url": f"/earning/verify/{item.platform}",
            }
        )
    for req in guide["requirements"].get("access_requirement") and [guide["requirements"]["access_requirement"]] or []:
        blockers.append({"kind": "requirement", "label": req, "resolution": "guide"})

    next_step = guide.get("next_step")
    resume_step = next((s for s in guide["steps"] if s["id"] == next_step), None) if next_step else None

    return {
        "item_id": item.id,
        "generated_at": datetime.now(UTC).isoformat(),
        "journey": journey,
        "guide": guide,
        "account_verification": {
            "platform": item.platform,
            "stage": verification.get("stage"),
            "account_status": verification.get("account_status"),
            "paused": verification.get("paused", False),
            "platform_verified": av.is_platform_verified(item.platform),
            "verification_url": f"/earning/verify/{item.platform}",
            "checklist": verification.get("checklist", []),
        },
        "resume": {
            "step_id": next_step,
            "step": resume_step,
            "progress": guide["progress"],
        },
        "blockers": blockers,
    }


def get_guide_progress(item_id: str) -> dict[str, Any]:
    return _load_progress().get(item_id, {})


def start_guide(item_id: str) -> dict[str, Any]:
    """Mark a guide as started (idempotent) and return its progress."""
    data = _load_progress()
    entry = data.setdefault(item_id, {"completed_steps": []})
    if "started_at" not in entry:
        entry["started_at"] = datetime.now(UTC).isoformat()
    entry["updated_at"] = datetime.now(UTC).isoformat()
    _save_progress(data)
    return entry


def complete_guide_step(item_id: str, step_id: str) -> dict[str, Any]:
    """Record owner-confirmed step completion. Idempotent; never auto-completes
    EXTERNAL_WAITING or VERIFIED steps without explicit confirmation."""

    bank = get_workbank()
    item = bank.get_item(item_id)
    if item is None:
        raise KeyError(item_id)
    guide = build_execution_guide(item)
    valid_ids = {s["id"] for s in guide["steps"]}
    if step_id not in valid_ids:
        raise ValueError(f"unknown step {step_id!r}")

    data = _load_progress()
    entry = data.setdefault(item_id, {"completed_steps": []})
    completed = entry.setdefault("completed_steps", [])
    if step_id not in completed:
        completed.append(step_id)
    entry["updated_at"] = datetime.now(UTC).isoformat()
    _save_progress(data)
    return entry


# ── Next Best Action ──────────────────────────────────────────────────

_JOURNEY_STAGES = [
    "discovery",
    "eligibility",
    "access",
    "preparation",
    "execution",
    "delivery",
    "acceptance",
    "payment",
    "withdrawal",
]

_ACTOR_LABELS = {
    Actor.HUMAN_REQUIRED: "Requiere acción tuya",
    Actor.OWNEX_AUTOMATED: "OWNEX lo ejecuta",
    Actor.OWNEX_ASSISTED: "OWNEX prepara, vos confirmás",
    Actor.EXTERNAL_WAITING: "Esperando a la plataforma",
    Actor.BLOCKED: "Bloqueado",
    Actor.VERIFIED_COMPLETED: "Completado con evidencia",
}


@dataclass
class _Candidate:
    kind: str
    item: WorkItem
    title: str
    instruction: str
    expected_outcome: str
    actor: Actor
    url: str
    score: float
    justification: str
    reason_codes: list[str]


def _journey_stage(item: WorkItem, progress: dict[str, Any]) -> dict[str, Any]:
    """Map work-bank state + guide progress onto the canonical journey."""
    completed = set(progress.get("completed_steps", []))
    access_ok = item.access_status in ("public", "api", "rss") or "platform-access" in completed
    if item.status == "delivered" or "submit-work" in completed:
        stage = "acceptance"
    elif access_ok and ("prepare-work" in completed or item.ready_to_deliver):
        stage = "delivery"
    elif access_ok:
        stage = "preparation"
    elif item.status == "needs_access":
        stage = "access"
    else:
        stage = "eligibility"
    idx = _JOURNEY_STAGES.index(stage)
    return {
        "current": stage,
        "stages": _JOURNEY_STAGES,
        "position": idx,
        "total": len(_JOURNEY_STAGES),
    }


def _item_candidates(bank: Any) -> list[_Candidate]:
    from core.opportunity.account_verification import is_platform_verified

    candidates: list[_Candidate] = []
    for item in bank._items.values():  # noqa: SLF001 — read-only ranking over persisted bank
        if item.status == "delivered":
            continue
        progress = get_guide_progress(item.id)
        if progress.get("dismissed"):
            continue
        snoozed_until = progress.get("snoozed_until")
        if snoozed_until and snoozed_until > datetime.now(UTC).isoformat():
            continue
        guide_started = bool(progress.get("started_at"))
        # A platform-verified account satisfies the access requirement for ALL
        # its opportunities — one registration, many unlocks.
        access_blocked = item.access_status not in ("public", "api", "rss") and not is_platform_verified(item.platform)

        if access_blocked and item.status == "needs_access":
            # The highest-leverage action is usually unblocking access.
            candidates.append(
                _Candidate(
                    kind="resolve_access",
                    item=item,
                    title=f"Conseguir acceso en {item.platform}",
                    instruction=item.access_requirement or "Configurá el acceso a la plataforma.",
                    expected_outcome=("Al completar el registro, OWNEX podrá verificar el acceso y habilitar la preparación técnica de la oportunidad."),
                    actor=Actor.HUMAN_REQUIRED,
                    url=_safe_url(_source_url(item.platform) or item.url),
                    score=item.reward * 0.8 + (100 - item.barrier_score),
                    justification=(f"{item.title[:80]} está bloqueado por acceso en {item.platform}. Resolverlo desbloquea la preparación y entrega."),
                    reason_codes=[
                        "access_pending",
                        "reward_published" if item.reward else "no_reward_data",
                        "low_barrier" if item.barrier_score <= 40 else "barrier_present",
                    ],
                )
            )
        elif item.status == "ready_to_deliver" or item.ready_to_deliver:
            step = "review-deliverables" if guide_started else "prepare-work"
            candidates.append(
                _Candidate(
                    kind="advance_work",
                    item=item,
                    title=f"{'Revisar' if step == 'review-deliverables' else 'Preparar'} entrega: {item.title[:80]}",
                    instruction=(
                        "Revisá el paquete preparado y aprobá la entrega."
                        if step == "review-deliverables"
                        else "Dejá que OWNEX prepare el paquete de entrega local."
                    ),
                    expected_outcome="Un paquete de entrega revisado y listo para enviar a la plataforma; la aceptación y el pago se verifican después por separado.",
                    actor=Actor.HUMAN_REQUIRED if step == "review-deliverables" else Actor.OWNEX_ASSISTED,
                    url=_safe_url(item.url),
                    score=item.reward + (100 - item.barrier_score) * 0.5 + (10 if guide_started else 0),
                    justification="Es el trabajo más cercano a generar ingreso verificable.",
                    reason_codes=["closest_to_payment", "reward_published" if item.reward else "no_reward_data"],
                )
            )
    return candidates


def next_best_action() -> dict[str, Any]:
    """Return the single most useful next action toward first verified revenue."""
    bank = get_workbank()
    candidates = _item_candidates(bank)
    candidates.sort(key=lambda c: c.score, reverse=True)

    generated_at = datetime.now(UTC).isoformat()

    if not candidates:
        return {
            "action": None,
            "reason": "No hay una siguiente acción confiable disponible: el Work Bank no tiene oportunidades accionables. Corré un ciclo de discovery primero.",
            "alternatives": [],
            "generated_at": generated_at,
        }

    top = candidates[0]
    progress = get_guide_progress(top.item.id)
    journey = _journey_stage(top.item, progress)
    from core.opportunity.account_verification import is_platform_verified

    access_blocked = top.item.access_status not in ("public", "api", "rss") and not is_platform_verified(top.item.platform)

    # Pending requirements checklist (honest: unknown stays unknown)
    pending_requirements = []
    if access_blocked:
        pending_requirements.append({"key": "account", "label": "Cuenta en la plataforma", "status": "pending"})
    pending_requirements.append({"key": "payment_method", "label": "Método de cobro verificado", "status": "unknown"})
    if top.item.access_status in ("public", "api", "rss"):
        pending_requirements = [{"key": "payment_method", "label": "Método de cobro verificado", "status": "unknown"}]

    return {
        "action": {
            "id": f"nba-{top.item.id}",
            "kind": top.kind,
            "item_id": top.item.id,
            "opportunity_id": top.item.id,
            "step_id": "platform-access" if top.kind == "resolve_access" else ("review-deliverables" if "Revisar" in top.title else "prepare-work"),
            "title": top.title,
            "instruction": top.instruction,
            "expected_outcome": top.expected_outcome,
            "actor": str(top.actor),
            "actor_label": _ACTOR_LABELS[top.actor],
            "url": top.url,
            "platform": top.item.platform,
            "category": top.item.category,
            "reward_published": top.item.reward or None,
            "reward_caveat": "Recompensa anunciada por la fuente; no es ingreso confirmado.",
            "barrier_score": top.item.barrier_score,
            "estimated_net": None,
            "net_caveat": "Neto desconocido: faltan datos de comisión y conversión.",
            "eligibility_status": "CONDITIONALLY_ELIGIBLE" if access_blocked else "UNKNOWN",
            "evidence_status": "VERIFIED_BY_OWNEX",
            "justification": top.justification,
            "reason_codes": top.reason_codes,
            "guide_url": f"/earning/work/{top.item.id}",
            "verification_url": f"/earning/verify/{top.item.platform}",
            "journey": journey,
            "pending_requirements": pending_requirements,
            "evidence": _action_evidence(top.item),
        },
        "reason": top.justification,
        "state": _nba_state(top, progress),
        "blocked": _blocked_actions(bank),
        "alternatives": [
            {
                "kind": c.kind,
                "item_id": c.item.id,
                "title": c.title,
                "actor": str(c.actor),
                "url": c.url,
                "reward_published": c.item.reward or None,
                "guide_url": f"/earning/work/{c.item.id}",
            }
            for c in candidates[1:4]
        ],
        "generated_at": generated_at,
    }


def _nba_state(top: _Candidate, progress: dict[str, Any]) -> str:
    """Spec §4 state vocabulary for the primary action."""
    if top.actor == Actor.EXTERNAL_WAITING:
        return "EXTERNAL_WAITING"
    if top.actor == Actor.BLOCKED:
        return "BLOCKED"
    if progress.get("started_at"):
        return "ACTION_IN_PROGRESS"
    if top.actor == Actor.HUMAN_REQUIRED:
        return "HUMAN_ACTION_REQUIRED"
    return "ACTION_AVAILABLE"


def _blocked_actions(bank: Any) -> list[dict[str, Any]]:
    """Spec §3 level 3: opportunities that need prep/info before they're actionable."""
    from core.opportunity.account_verification import is_platform_verified

    blocked: list[dict[str, Any]] = []
    for item in bank._items.values():  # noqa: SLF001
        if item.status != "needs_access":
            continue
        progress = get_guide_progress(item.id)
        if progress.get("dismissed"):
            continue
        if item.access_status in ("public", "api", "rss") or is_platform_verified(item.platform):
            continue
        blocked.append(
            {
                "item_id": item.id,
                "title": item.title[:90],
                "platform": item.platform,
                "reason": item.access_requirement or "Requiere acceso/configuración previa",
                "reward_published": item.reward or None,
                "guide_url": f"/earning/work/{item.id}",
                "verification_url": f"/earning/verify/{item.platform}",
            }
        )
    blocked.sort(key=lambda b: b["reward_published"] or 0, reverse=True)
    return blocked[:3]


def _action_evidence(item: WorkItem) -> list[dict[str, Any]]:
    """Evidence panel for 'Ver evidencia' — only real, dated sources."""
    evidence: list[dict[str, Any]] = []
    if item.url:
        evidence.append(
            {
                "label": "Publicación original",
                "value": item.url,
                "source": "work_bank_record",
                "verified_at": item.created_at,
                "status": "VERIFIED_BY_OWNEX",
            }
        )
    platform_url = _safe_url(_source_url(item.platform))
    if platform_url:
        evidence.append(
            {
                "label": "URL oficial de plataforma",
                "value": platform_url,
                "source": "source_registry",
                "verified_at": None,
                "status": "VERIFIED_BY_OWNEX",
            }
        )
    doc = _payment_doc(item.platform)
    if doc:
        evidence.append(
            {
                "label": "Métodos de pago documentados",
                "value": ", ".join(doc.get("methods") or []) or "ninguno documentado",
                "source": "source_payment_docs",
                "verified_at": None,
                "status": "VERIFIED_BY_OWNEX",
            }
        )
    evidence.append(
        {
            "label": "Recompensa",
            "value": f"{item.reward} (publicada por la fuente, no verificada)" if item.reward else "sin dato",
            "source": "work_bank_record",
            "verified_at": item.created_at,
            "status": "ESTIMATED",
        }
    )
    return evidence


def snooze_action(item_id: str, hours: int = 24) -> dict[str, Any]:
    """Posponer: hide the item from NBA until snoozed_until."""
    from datetime import timedelta

    data = _load_progress()
    entry = data.setdefault(item_id, {"completed_steps": []})
    entry["snoozed_until"] = (datetime.now(UTC) + timedelta(hours=hours)).isoformat()
    entry["updated_at"] = datetime.now(UTC).isoformat()
    _save_progress(data)
    return entry


def dismiss_action(item_id: str, reason: str = "") -> dict[str, Any]:
    """Descartar: exclude from NBA until manually re-enabled (history kept)."""
    data = _load_progress()
    entry = data.setdefault(item_id, {"completed_steps": []})
    entry["dismissed"] = True
    entry["dismissed_reason"] = reason
    entry["updated_at"] = datetime.now(UTC).isoformat()
    _save_progress(data)
    return entry
