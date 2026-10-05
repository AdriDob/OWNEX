"""Curated source registry — opt-in/out, gates y liveness para las 119 fuentes curadas.

Las fuentes viven en ``cores.opportunity.global_sources`` (datos, no código).
Este módulo NO inventa disponibilidad: una fuente solo entra al discovery con
fetch real verificado; el resto vive en el radar con provenance honesta.

Dueño-reglas codificadas (ver DECISIONS):
- Paga < USD 15/h (cuando el rate es conocido) → fuera, salvo opt-in explícito.
- Exige interview/empleo → fuera, salvo opt-in explícito.
- Sin datos → UNKNOWN, jamás se finge.

Quarantine automático (delegado por el owner): 3 probes muertos seguidos →
deshabilitada del radar/discovery con log + reversible en un clic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("ownex.direct_work_engine.source_registry")

# Regla permanente del owner: piso de pago y veto de funnel de contratación.
MIN_HOURLY_USD = 15.0
QUARANTINE_AFTER_DEAD = 3
PROBE_TIMEOUT_S = 10.0
PROBE_CONCURRENCY = 10

# ── Admisión de fuentes: DOS EJES SEPARADOS (corregido 2026-09-30) ──
#
# El gate anterior mezclaba dos preguntas y por eso producía un número
# engañoso (17 ACTIVE de 196):
#
#   EJE A — BARRERA (¿puedo entrar?)   → ADMISIÓN. Es el filtro del owner.
#   EJE B — PAGO (¿cuánto gana?)        → RANKING. NO es una barrera.
#
# "Payout no documentado" (`"varies"`) decía "no sé cuánto pagan", que es
# información faltante, NO una barrera de acceso: HackerOne no publicaba cifra
# en su SourceDefinition y quedaba fuera del ranking por eso. Ahora entra, y
# lo que no tiene cifra queda ORDER_EVIDENCE=NEGOTIATED para que el ranking lo
# sepa sin bloquearlo.
#
# El gate anterior también tenía un bug de alcance: `data_entry` y
# `ai_evaluation` NO estaban en TECHNICAL_CATEGORIES, así que las 37 fuentes
# de AI training quedaban BLOCKED por "no es trabajo técnico" — que es
# exactamente la rama que el owner quiere llena.

SOURCE_ACTIVE = "ACTIVE"
SOURCE_CONDITIONAL = "CONDITIONAL"
SOURCE_LOW_VALUE = "LOW_VALUE"
SOURCE_BLOCKED = "BLOCKED"

# Tipos de fuente que son tiles técnicos con entregable. Un job board genérico
# o un marketplace de servicios NO es trabajo técnico verificable.
TECHNICAL_SOURCE_TYPES = frozenset({"platform", "aggregator", "direct_api", "forum"})

# Categorías que son trabajo pagable y verificable por el usuario. Incluye
# data_entry y ai_evaluation: son ramas explícitas del radar del owner
# (AI training / annotation), no "curiosidades".
TECHNICAL_CATEGORIES = frozenset(
    {
        "bug_bounty",
        "dev_bounty",
        "oss_bounties",
        "open_source",
        "security_research",
        "competitions",
        "ai_evaluation",
        "data_entry",
        "data_annotation",
        "synthetic_data",
        "open_call",
    }
)

#: Categories paid per accepted outcome rather than per hour. The amount is
#: documented **per program/report**, so a single source-level figure would be
#: a fabrication — but "we don't know if it pays" is equally wrong for them.
PER_OUTCOME_CATEGORIES = frozenset({"bug_bounty", "dev_bounty", "oss_bounties"})

# ── EJE A: barrera de entrada (filtro del owner) ────────────────
# El owner: "sin experiencia profesional, sin entrevista; como mucho
# assessment/evaluation y/o SKILLS, y registrarse".
BARRIER_ZERO = "ZERO_BARRIER"  # registro y a cobrar
BARRIER_ASSESSMENT = "ASSESSMENT"  # + test de rol (DataAnnotation)
BARRIER_SKILLS = "SKILLS_ONLY"  # + entrevista/test de skills (micro1, Outlier T1)
BARRIER_CREDENTIALS = "CREDENTIALS"  # CV / LinkedIn / años de oficio

BARRIER_ORDER = (BARRIER_ZERO, BARRIER_ASSESSMENT, BARRIER_SKILLS)

# ── EJE B: evidencia de pago (ranking, NO admisión) ─────────────
PAYOUT_PUBLISHED = "PUBLISHED"  # hay cifra publicada
PAYOUT_NEGOTIATED = "NEGOTIATED"  # paga, cifra no publicada
PAYOUT_UNKNOWN = "UNKNOWN"  # "varies": no se sabe todavía

# ── Compatibilidad del rail de pago con Argentina (2026-09-30) ──
# Una plataforma puede ser 0 barrera y aun así NUNCA pagarte: es lo que
# pasa con Stripe, que no tiene cobertura en Argentina (AfterQuery excluye AR
# por eso mismo). Sin este eje, el ranking recomienda lo imposible de cobrar.
RAIL_AR_OK = "TRUE"  # verificado que paga en Argentina
RAIL_AR_NO = "FALSE"  # verificado que NO puede
RAIL_AR_UNKNOWN = "UNKNOWN"  # sin dato

# Payoneer / Deel / PayPal / Wise / AirTM: los rails que sí llegan a AR.
AR_COMPATIBLE_RAILS = frozenset(
    {"payoneer", "deel", "paypal", "wise", "airtm", "paypal_airtm", "bank_transfer", "crypto", "bitcoin"}
)
AR_INCOMPATIBLE_RAILS = frozenset({"stripe"})


def entry_barrier(src: Any) -> str:
    """EJE A — barrera de entrada, derivada de lo que YA declara la fuente.

    El owner: *"sin experiencia profesional, sin entrevista; como mucho
    assessment/evaluation y/o SKILLS, y registrarse"*.

    modelar que una plataforma tiene un track generalista 0 barrera y otro
    deriva de los flags existentes.
    """
    explicit = str(getattr(src, "entry_barrier", "") or "").strip().upper()
    if explicit in (BARRIER_ZERO, BARRIER_ASSESSMENT, BARRIER_SKILLS, BARRIER_CREDENTIALS):
        return explicit

    if bool(getattr(src, "requires_experience", False)) or bool(getattr(src, "requires_portfolio", False)):
        return BARRIER_CREDENTIALS
    if bool(getattr(src, "requires_interview", False)):
        return BARRIER_CREDENTIALS
    if bool(getattr(src, "requires_assessment", False)):
        return BARRIER_ASSESSMENT
    return BARRIER_ZERO


def payout_evidence(src: Any) -> str:
    """EJE B — evidencia del pago. NO es una barrera: es confianza de ranking."""
    rate = getattr(src, "typical_hourly_rate_usd", None)
    if rate is not None:
        try:
            if float(rate) > 0:
                return PAYOUT_PUBLISHED
        except (TypeError, ValueError):
            pass
    payout = str(getattr(src, "estimated_payout_range", "") or "").strip().lower()
    if payout and payout not in {"varies", "unknown", "n/a", "-"}:
        return PAYOUT_PUBLISHED
    if bool(getattr(src, "payment_proven", False)):
        return PAYOUT_NEGOTIATED
    # Per-outcome work (bounties, audit contests, bug rewards) pays a
    # documented amount **per program**, not a per-hour rate, so there is no
    # single figure to publish on the source. That is PAYOUT_NEGOTIATED, not
    # UNKNOWN. The previous check looked for "bounty" in `type`, which is
    # never set — `type` is platform/job_board/aggregator/forum/direct_api —
    # so this branch was unreachable and 166 sources were marked "pays but no
    # published figure" when the truth is "pays per program, figure varies".
    cat = str(getattr(getattr(src, "category", None), "value", "") or "").strip().lower()
    if cat in PER_OUTCOME_CATEGORIES or bool(getattr(src, "pays_per_outcome", False)):
        return PAYOUT_NEGOTIATED
    return PAYOUT_UNKNOWN


def payout_rail(src: Any) -> str:
    """Rail de pago declarado por la fuente (p.ej. "payoneer", "stripe")."""
    return str(getattr(src, "payout_rail", "") or "").strip().lower()


def pays_in_argentina(src: Any) -> str:
    """¿El rail de pago llega a Argentina? Decisivo: 0 barrera y rail
    incompatible = nunca cobrás nada.

    Verificado 2026-09-30: **Stripe no tiene cobertura en Argentina**
    (PayoutMap) y AfterQuery excluye explícitamente AR por eso mismo.
    """
    explicit = str(getattr(src, "rail_pays_in_argentina", "") or "").strip().upper()
    if explicit in (RAIL_AR_OK, RAIL_AR_NO):
        return explicit
    rail = payout_rail(src)
    if not rail:
        return RAIL_AR_UNKNOWN
    if rail in AR_INCOMPATIBLE_RAILS:
        return RAIL_AR_NO
    if rail in AR_COMPATIBLE_RAILS:
        return RAIL_AR_OK
    return RAIL_AR_UNKNOWN


class AdmissionResult:
    """Veredicto de admisión (EJE A) con los dos ejes visibles."""

    __slots__ = ("status", "reason", "p0_checks", "barrier", "payout", "rail_ar")

    def __init__(
        self,
        status: str,
        reason: str,
        p0_checks: dict[str, bool] | None = None,
        barrier: str = BARRIER_ZERO,
        payout: str = PAYOUT_UNKNOWN,
        rail_ar: str = RAIL_AR_UNKNOWN,
    ) -> None:
        self.status = status
        self.reason = reason
        self.p0_checks = p0_checks or {}
        self.barrier = barrier
        self.payout = payout
        self.rail_ar = rail_ar

    @property
    def admitted(self) -> bool:
        """Admitida si el owner no la vetó explícitamente (LOW_VALUE entra)."""
        return self.status != SOURCE_BLOCKED

    @property
    def zero_barrier(self) -> bool:
        """¿Cumple el filtro estricto del owner (sin exp / sin entrevista)?"""
        return self.barrier in BARRIER_ORDER

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "payout_known": self.payout == PAYOUT_PUBLISHED,
            "barrier": self.barrier,
            "payout_evidence": self.payout,
            "rail_pays_argentina": self.rail_ar,
            "p0_checks": dict(self.p0_checks),
        }


def admit_source(src: Any) -> AdmissionResult:
    """SOURCE ADMISSION TEST — EJE A (barrera). Puro, nunca raisea.

    El payout (EJE B) NO decide admisión: ordena el ranking. Ese era el bug que
    dejaba 17 de 196 en ACTIVE — "no sé cuánto pagan" se trataba igual que
    "no podés entrar" (HackerOne, Bugcrowd, Intigriti, yeswehack tienen
    `estimated_payout_range="varies"` y quedaban fuera del ranking por eso).
    """
    try:
        name = str(getattr(src, "name", "?"))
        cat = getattr(src, "category", None)
        cat_v = str(getattr(cat, "value", cat) or "")
        stype = str(getattr(src, "type", "") or "")
        checks: dict[str, bool] = {}

        barrier = entry_barrier(src)
        payout = payout_evidence(src)
        rail_ar = pays_in_argentina(src)

        checks["technical_source_type"] = stype in TECHNICAL_SOURCE_TYPES
        checks["technical_category"] = cat_v in TECHNICAL_CATEGORIES
        checks["clear_apply_method"] = bool(getattr(src, "apply_method", ""))
        checks["no_professional_credentials"] = barrier in BARRIER_ORDER

        def _res(status: str, reason: str) -> AdmissionResult:
            return AdmissionResult(status, reason, checks, barrier, payout, rail_ar)

        # ── EJE A: la barrera decide admisión ──
        if barrier == BARRIER_CREDENTIALS:
            return _res(
                SOURCE_BLOCKED,
                f"{name}: pide experiencia profesional / CV / entrevista — visible en el "
                "catálogo, fuera del ranking de 0 barrera",
            )
        if cat_v and not checks["technical_category"]:
            return _res(SOURCE_BLOCKED, f"{name}: categoría {cat_v} fuera de las pagables/verificables")
        if not cat_v and not checks["technical_source_type"]:
            return _res(SOURCE_CONDITIONAL, f"{name}: categoría/tipo sin verificar — requiere curar el dato")
        if not checks["technical_source_type"]:
            return _res(
                SOURCE_BLOCKED,
                f"{name}: tipo {stype or '?'} (marketplace/job_board de servicios) — no es trabajo verificable",
            )
        if not checks["clear_apply_method"]:
            return _res(SOURCE_CONDITIONAL, f"{name}: falta método de entrega claro — requiere curar el dato")

        # ── EJE B: el payout sólo modula el veredicto de ranking ──
        if payout == PAYOUT_UNKNOWN:
            return _res(
                SOURCE_CONDITIONAL,
                f"{name}: paga pero sin cifra publicada — usable; no se prioriza hasta verificar",
            )
        try:
            rate = getattr(src, "typical_hourly_rate_usd", None)
            if rate is not None and float(rate) < MIN_HOURLY_USD:
                return _res(
                    SOURCE_LOW_VALUE,
                    f"{name}: bajo el piso de USD {MIN_HOURLY_USD}/h — entra, no prioriza",
                )
        except (TypeError, ValueError):
            pass

        return _res(SOURCE_ACTIVE, f"{name}: admisible (barrera={barrier}, pago={payout}, rail_ar={rail_ar})")
    except Exception as exc:  # pragma: no cover — defensivo
        return AdmissionResult(SOURCE_BLOCKED, f"gate error: {exc}")


def _store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "curated_sources.json"


def _load_store() -> dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {"disabled": [], "liveness": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"disabled": [], "liveness": {}}
        data.setdefault("disabled", [])
        data.setdefault("liveness", {})
        return data
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("source_registry: store ilegible, defaults: %s", exc)
        return {"disabled": [], "liveness": {}}


def _save_store(store: dict[str, Any]) -> None:
    path = _store_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("source_registry: no se pudo persistir: %s", exc)


def _all_sources() -> list[Any]:
    from cores.opportunity.global_sources import get_sources  # type: ignore[import-not-found]

    return get_sources()


def source_gate(src: Any, *, private_unlocked: bool = False) -> tuple[bool, str]:
    """Aplica las reglas del owner. (allowed, reason) — puro, nunca raisea.

    P0 = admisión (trabajo técnico verificable con recompensa documentada).
    P1 = Interview/rate veto (reglas del owner, sin cambios).

    `CONDITIONAL` y `LOW_VALUE` **entran** (con motivo visible): no se bloquea
    por ignorancia, se marca. Sólo `BLOCKED` queda fuera sin opt-in.
    """
    try:
        name = str(getattr(src, "name", "?"))

        # P0 primero: una fuente que no es trabajo técnico no entra, por mucho
        # que pase los gates P1.
        admission = admit_source(src)
        if not admission.admitted:
            return False, admission.reason

        try:
            from cores.opportunity.global_sources import is_private_program

            if is_private_program(src) and not private_unlocked:
                return False, f"{name}: programa privado (aplicación/NDA) — solo con acceso ganado"
        except Exception:
            pass
        if bool(getattr(src, "requires_interview", False)):
            return False, f"{name}: exige entrevista — fuera salvo opt-in explícito"
        rate = getattr(src, "typical_hourly_rate_usd", None)
        if rate is not None:
            try:
                if float(rate) < MIN_HOURLY_USD:
                    return False, f"{name}: USD {float(rate)}/h < piso USD {MIN_HOURLY_USD}/h — fuera salvo opt-in"
            except (TypeError, ValueError):
                pass
        return True, admission.reason
    except Exception as exc:
        return False, f"gate error: {exc}"


def is_source_enabled(name: str) -> bool:
    """True salvo opt-out del usuario o quarantine. Default: habilitada."""
    store = _load_store()
    if name in set(store.get("disabled", [])):
        return False
    return not is_quarantined(name)


def is_private_unlocked(name: str) -> bool:
    """True si el humano desbloqueó un programa privado (acceso ganado)."""
    try:
        return name in set(_load_store().get("private_unlocked", []))
    except Exception:
        return False


def unlock_private_source(name: str) -> bool:
    """Desbloqueo explícito humano de un programa privado. False si no existe o no es privado."""
    try:
        from cores.opportunity.global_sources import is_private_program

        target = None
        for s in _all_sources():
            if str(getattr(s, "name", "")) == name:
                target = s
                break
        if target is None or not is_private_program(target):
            return False
        store = _load_store()
        unlocked = set(store.get("private_unlocked", []))
        unlocked.add(name)
        store["private_unlocked"] = sorted(unlocked)
        _save_store(store)
        return True
    except Exception as exc:
        logger.warning("source_registry: unlock falló: %s", exc)
        return False


def set_source_enabled(name: str, enabled: bool) -> bool:
    """Opt-in/out persistente. False si el nombre no existe. Nunca raisea."""
    try:
        names = {str(getattr(s, "name", "")) for s in _all_sources()}
        if name not in names:
            return False
        store = _load_store()
        disabled = set(store.get("disabled", []))
        if enabled:
            disabled.discard(name)
            # Re-habilitar limpia quarantine (decisión humana > probe).
            live = store.get("liveness", {}).get(name)
            if isinstance(live, dict):
                live["consecutive_dead"] = 0
        else:
            disabled.add(name)
        store["disabled"] = sorted(disabled)
        _save_store(store)
        return True
    except Exception as exc:
        logger.warning("source_registry: opt falló: %s", exc)
        return False


def liveness_for(name: str) -> dict[str, Any]:
    """Estado de liveness conocido. UNKNOWN si nunca se probeó."""
    store = _load_store()
    entry = store.get("liveness", {}).get(name)
    if not isinstance(entry, dict):
        return {"status": "unknown", "reason": "sin probe todavía"}
    return {
        "status": entry.get("status", "unknown"),
        "latency_ms": entry.get("latency_ms"),
        "checked_at": entry.get("checked_at"),
        "consecutive_dead": int(entry.get("consecutive_dead", 0)),
        "reason": entry.get("reason", ""),
    }


async def _probe_one(client: httpx.AsyncClient, url: str) -> tuple[str, float | None, str]:
    """(status, latency_ms, reason). Tri-estado honesto: live/dead/unknown."""
    if not url or not url.startswith(("http://", "https://")):
        return "unknown", None, "sin URL probeable"
    start = datetime.now(UTC)
    try:
        try:
            resp = await client.head(url, timeout=PROBE_TIMEOUT_S)
            if resp.status_code in (404, 410):
                # HEAD no implementado en muchos servidores (ej. Kaggle):
                # un 404 de HEAD no es veredicto hasta intentar GET.
                resp = await client.get(url, timeout=PROBE_TIMEOUT_S)
        except Exception:
            resp = await client.get(url, timeout=PROBE_TIMEOUT_S)
        latency = (datetime.now(UTC) - start).total_seconds() * 1000
        code = resp.status_code
        if 200 <= code < 400:
            return "live", round(latency, 1), f"HTTP {code}"
        if code in (404, 410):
            return "dead", round(latency, 1), f"HTTP {code}: recurso inexistente"
        # 401/403/muros, 405/500/501/502/503 y rarezas: el servidor responde,
        # pero no se puede juzgar → unknown, jamás dead por un código ambiguo.
        return "unknown", round(latency, 1), f"HTTP {code}: sin veredicto"
    except Exception as exc:
        return "dead", None, f"conexión fallida: {type(exc).__name__}"


async def probe_all_sources() -> dict[str, Any]:
    """Probea las 119 fuentes. Nunca raisea. Persiste snapshot + quarantine."""
    sources = _all_sources()
    store = _load_store()
    liveness = store.get("liveness", {})
    semaphore = asyncio.Semaphore(PROBE_CONCURRENCY)

    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "OWNEX-probe/1.0"}) as client:

        async def _one(src: Any) -> tuple[str, dict[str, Any]]:
            name = str(getattr(src, "name", "?"))
            url = str(getattr(src, "url", "") or "")
            async with semaphore:
                status, latency, reason = await _probe_one(client, url)
            prev = liveness.get(name) if isinstance(liveness.get(name), dict) else {}
            consecutive = int(prev.get("consecutive_dead", 0) or 0)
            if status == "dead":
                consecutive += 1
            elif status == "live":
                consecutive = 0
            entry = {
                "status": status,
                "latency_ms": latency,
                "checked_at": datetime.now(UTC).isoformat(),
                "consecutive_dead": consecutive,
                "reason": reason,
                "quarantined": consecutive >= QUARANTINE_AFTER_DEAD,
            }
            return name, entry

        results = await asyncio.gather(*(_one(s) for s in sources))

    quarantined_now: list[str] = []
    for name, entry in results:
        old = liveness.get(name) if isinstance(liveness.get(name), dict) else {}
        liveness[name] = entry
        if entry["quarantined"] and not bool(old.get("quarantined", False)):
            quarantined_now.append(name)
            logger.warning("source_registry: quarantine %s (%s)", name, entry["reason"])

    store["liveness"] = liveness
    _save_store(store)

    counts = {"live": 0, "dead": 0, "unknown": 0}
    for _, entry in results:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return {
        "probed": len(results),
        "live": counts.get("live", 0),
        "dead": counts.get("dead", 0),
        "unknown": counts.get("unknown", 0),
        "quarantined_now": quarantined_now,
        "checked_at": datetime.now(UTC).isoformat(),
    }


def is_quarantined(name: str) -> bool:
    entry = liveness_for(name)
    return entry.get("status") == "dead" and int(entry.get("consecutive_dead", 0) or 0) >= QUARANTINE_AFTER_DEAD


def run_source_probe_cycle() -> dict[str, Any]:
    """Entry sync para el scheduler. Nunca raisea (el scheduler no debe caer)."""
    try:
        return asyncio.run(probe_all_sources())
    except Exception as exc:
        logger.error("source_registry: ciclo de probe falló: %s", exc)
        return {"probed": 0, "live": 0, "dead": 0, "unknown": 0, "quarantined_now": [], "error": str(exc)}


def sources_overview() -> dict[str, Any]:
    """Las 119 con gates + liveness + enabled. Para GET /direct-work/sources.

    Perf: UNA sola lectura del store (antes: 2 lecturas por fuente × N).
    """
    store = _load_store()
    disabled = set(store.get("disabled", []))
    unlocked = set(store.get("private_unlocked", []))
    liveness_map = store.get("liveness", {})
    if not isinstance(liveness_map, dict):
        liveness_map = {}
    out: list[dict[str, Any]] = []
    verified_count = 0
    for src in _all_sources():
        name = str(getattr(src, "name", "?"))
        try:
            from cores.opportunity.global_sources import is_private_program

            is_private = is_private_program(src)
        except Exception:
            is_private = False
        src_unlocked = (not is_private) or (name in unlocked)
        allowed, reason = source_gate(src, private_unlocked=src_unlocked)
        raw = liveness_map.get(name)
        if isinstance(raw, dict):
            live = {
                "status": raw.get("status", "unknown"),
                "latency_ms": raw.get("latency_ms"),
                "checked_at": raw.get("checked_at"),
                "consecutive_dead": int(raw.get("consecutive_dead", 0) or 0),
                "reason": raw.get("reason", ""),
            }
        else:
            live = {"status": "unknown", "reason": "sin probe todavía"}
        quarantined = (
            live.get("status") == "dead" and int(live.get("consecutive_dead", 0) or 0) >= QUARANTINE_AFTER_DEAD
        )
        enabled = name not in disabled and not quarantined and src_unlocked
        # Effective verification: static VERIFIED, o promovido por liveness live
        # (excluyendo el filler "Extra" que solo suma al conteo 1000).
        static_verified = str(getattr(src, "source_status", "VERIFIED")) == "VERIFIED"
        is_filler = "Extra" in name or name.startswith("Open Collective —")
        is_effective_verified = static_verified or (live.get("status") == "live" and not is_filler)
        if is_effective_verified:
            verified_count += 1
        out.append(
            {
                "name": name,
                "url": str(getattr(src, "url", "") or ""),
                "category": getattr(getattr(src, "category", ""), "value", str(getattr(src, "category", ""))),
                "type": str(getattr(src, "type", "")),
                "gate": {"allowed": allowed, "reason": reason},
                "liveness": live,
                "quarantined": quarantined,
                "enabled": enabled,
                "disabled_by_user": name in disabled,
                "visibility": "private" if is_private else "public",
                "unlocked": src_unlocked,
                # Exact onboarding "empiezo de 0" + overwrite con exclusión? no removemos nada
                "onboarding": _onboarding_for(src),
                "verified": "VERIFIED" if is_effective_verified else "UNVERIFIED",
            }
        )
    return {
        "total": len(out),
        "verified": verified_count,
        "unverified": len(out) - verified_count,
        "enabled": sum(1 for s in out if s["enabled"]),
        "quarantined": sum(1 for s in out if s["quarantined"]),
        "disabled_by_user": len(disabled),
        "sources": out,
    }


def _onboarding_for(src: Any) -> list[dict[str, str]]:
    """Onboarding steps deterministas por fuente (empiezo de 0 en cada web)."""
    try:
        from cores.opportunity.global_sources import onboarding_steps

        return onboarding_steps(src)
    except Exception:
        return []
