"""Auto-Submission Engine — Real delivery to platforms via API.

Closes the loop: WorkBank prepares → AutoSubmitEngine delivers → RevenueTracker records.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.identity_vault import IdentityVault
from cores.opportunity.executors.assisted_mode import AssistedExecutor, PreparedWork

logger = logging.getLogger("ownex.opportunity.auto_submit")

# Orden canónico de resolución de credenciales. SSOT compartido entre el motor
# (`AutoSubmitEngine._get_api_key`) y los adapters, que antes lo tenían
# duplicado y divergente — el motor sólo miraba IdentityVault, así que un
# GITHUB_TOKEN en ~/.config/ownex/opportunity.env era ignorado.
_ENV_KEY_NAMES: dict[str, tuple[str, ...]] = {
    "github": ("GITHUB_TOKEN", "GH_TOKEN"),
    "github_bounty": ("GITHUB_TOKEN", "GH_TOKEN"),
    "gitlab": ("GITLAB_TOKEN",),
    "algora": ("ALGORA_API_KEY",),
    "opire": ("OPIRE_API_KEY",),
    "issuehunt": ("ISSUEHUNT_API_KEY",),
}

# Atributos equivalents en `cores.credentials.vault.Credentials`.
_VAULT_ATTR_BY_PLATFORM: dict[str, tuple[str, ...]] = {
    "github": ("github_token",),
    "github_bounty": ("github_token",),
    "gitlab": ("gitlab_token",),
    "algora": ("algora_api_key",),
    "opire": ("opire_api_key",),
    "issuehunt": ("issuehunt_api_key",),
}


# Lazy imports to avoid circular deps
def _get_hackerone():
    from cores.platforms.hackerone import HackerOne

    return HackerOne()


def _get_bugcrowd():
    from cores.platforms.bugcrowd import Bugcrowd

    return Bugcrowd()


def _get_intigriti():
    from cores.platforms.intigriti import Intigriti

    return Intigriti()


def _get_yeswehack():
    from cores.platforms.yeswehack import YesWeHack

    return YesWeHack()


def _get_opire_adapter():
    from cores.opportunity.adapters.opire import OpireAdapter

    return OpireAdapter()


def _get_issuehunt_adapter():
    from cores.opportunity.adapters.issuehunt import IssueHuntAdapter

    return IssueHuntAdapter()


def _get_freelancer_adapter():
    from cores.opportunity.adapters.freelancer import FreelancerAdapter

    return FreelancerAdapter()


def _get_algora_adapter():
    from cores.opportunity.executors.algora_executor import AlgoraDweAdapter

    return AlgoraDweAdapter()


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    PREPARING = "preparing"
    READY = "ready"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DLQ = "dlq"  # Dead Letter Queue - requires manual intervention


_GITHUB_ISSUE_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/issues/(\d+)", re.I)
_CODE_BOUNTY_PLATFORMS = frozenset({"github", "github_bounty", "oss", "algora", "opire", "issuehunt"})


def _github_issue(url: str) -> tuple[str, str, int] | None:
    """Extrae (owner, repo, issue_number) de una URL de issue de GitHub."""
    m = _GITHUB_ISSUE_RE.match((url or "").strip())
    if not m:
        return None
    owner, repo, number = m.groups()
    return owner, repo, int(number)


@dataclass
class SubmissionRecord:
    """Single submission attempt with full traceability."""

    id: str
    platform: str
    opportunity_id: str
    opportunity_title: str
    idempotency_key: str
    status: SubmissionStatus
    prepared_work: PreparedWork | None = None
    submission_result: dict[str, Any] | None = None
    attempts: int = 0
    max_attempts: int = 3
    last_error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    submitted_at: str | None = None
    confirmed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "opportunity_id": self.opportunity_id,
            "opportunity_title": self.opportunity_title,
            "idempotency_key": self.idempotency_key,
            "status": self.status.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_error": self.last_error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "submitted_at": self.submitted_at,
            "confirmed_at": self.confirmed_at,
            "metadata": self.metadata,
        }


class GitHubBountyAdapter:
    """Adaptador para issues de bounty de GitHub (plataformas `github_bounty`).

    Un bounty de GitHub se resuelve con un PULL REQUEST sobre el repo, igual que
    Algora pero **sin** la API de Algora (`api.algora.io`): por eso NO reutiliza
    `AlgoraExecutor` (que haría `claim_issue` contra Algora y fallaría).

    Reglas duras (spec FIRST PAID / §11-§12):
    - **Fail-closed**: sin `GITHUB_TOKEN` no hay envío, ni parcial, ni error
      silencioso — devuelve `needs_access` con el requisito exacto.
    - **Human Gate**: la creación del PR delega en `PRBuilder.create_pr`, que ya
      exige un `approval_token` de un solo uso (`require_approval=True`).
    - Nunca envía nada por su cuenta: sin token/aprobación devuelve el estado y
      el próximo paso humano.
    """

    provider_id = "github"

    def __init__(self) -> None:
        self._token: str | None = None

    @staticmethod
    def _resolve_token() -> str | None:
        """Mismo orden de resolución que `build_algora_executor` (80% rule):
        env → credentials vault (~/.config/ownex/opportunity.env) → IdentityVault.
        """
        token = os.environ.get("GITHUB_TOKEN") or None
        if token:
            return token
        try:
            from cores.credentials import vault as _creds_vault

            token = _creds_vault.get_credentials(force_refresh=True).github_token or None
        except Exception as exc:
            logger.debug("GitHub adapter: credentials vault unavailable: %s", exc)
        if token:
            return token
        try:
            vault = IdentityVault()
            creds = vault.get_credentials("platform_github")
            if creds and creds.get("token"):
                return creds["token"]
        except Exception as exc:
            logger.debug("GitHub adapter: IdentityVault unavailable: %s", exc)
        return None

    async def submit_work(self, prepared_work: Any, api_key: str) -> dict[str, Any]:
        """Entrega vía PR a un issue de bounty de GitHub. Fail-closed sin token."""
        opportunity = getattr(prepared_work, "metadata", {}).get("opportunity", {})
        issue_url = opportunity.get("url") or opportunity.get("issue_url")
        if not issue_url:
            return {"success": False, "error": "No issue_url in opportunity", "state": "needs_preparation"}

        token = api_key or self._resolve_token()
        if not token:
            # Fail-closed explícito: el requisito humano exacto, sin ejecutar nada.
            return {
                "success": False,
                "state": "needs_access",
                "provider": self.provider_id,
                "issue_url": issue_url,
                "error": "GITHUB_TOKEN no configurada",
                "requirement": (
                    "Pegar GITHUB_TOKEN en ~/.config/ownex/opportunity.env "
                    "(o exportarla). Es el mismo archivo que lee el checklist."
                ),
                "human_gate": "required_before_send",
                "attempted_external_action": False,
            }

        # Con token: la creación del PR sigue siendo un Human Gate. El envío
        # real lo ejecuta `PRBuilder.create_pr(..., require_approval=True)`.
        return {
            "success": False,
            "state": "ready_for_human_approval",
            "provider": self.provider_id,
            "issue_url": issue_url,
            "error": None,
            "requirement": (
                "Token disponible. El PR se abre vía PRBuilder con approval_token "
                "de un solo uso: la apertura es una acción externa y la decide el humano."
            ),
            "human_gate": "required_before_send",
            "attempted_external_action": False,
        }


def _get_github_bounty_adapter() -> GitHubBountyAdapter:
    return GitHubBountyAdapter()


class AutoSubmitEngine:
    """Orchestrates real API submissions to all supported platforms."""

    def __init__(
        self,
        vault: IdentityVault | None = None,
        dlq_path: str | Path | None = None,
        queue_path: str | Path | None = None,
    ):
        self.vault = vault or IdentityVault()
        data_base = Path(os.environ.get("OWNEX_DATA_DIR", Path.home() / "ownex"))
        self.dlq_path = Path(dlq_path).expanduser() if dlq_path else data_base / "submissions" / "dlq"
        self.dlq_path.mkdir(parents=True, exist_ok=True)
        self._queue_path: Path = (
            Path(queue_path).expanduser() if queue_path else data_base / "submissions" / "submission_queue.json"
        )

        # Platform instances (lazy-loaded with credentials)
        self._platforms: dict[str, Any] = {}
        self._adapters: dict[str, Any] = {}

        # Submission queue (persisted)
        self._submissions: dict[str, SubmissionRecord] = {}
        self._load_queue()

        # Retry config
        self.base_retry_delay = 30  # seconds
        self.max_retry_delay = 3600  # 1 hour

    def _get_platform(self, platform_key: str) -> Any:
        """Lazy-load platform instance with credentials from vault."""
        if platform_key in self._platforms:
            return self._platforms[platform_key]

        platform_map = {
            "hackerone": _get_hackerone(),
            "bugcrowd": _get_bugcrowd(),
            "intigriti": _get_intigriti(),
            "yeswehack": _get_yeswehack(),
        }

        if platform_key not in platform_map:
            raise ValueError(f"Unsupported platform for auto-submit: {platform_key}")

        platform = platform_map[platform_key]
        self._platforms[platform_key] = platform
        return platform

    def _get_adapter(self, platform_key: str) -> Any:
        """Lazy-load opportunity adapter for dev bounty platforms."""
        if platform_key in self._adapters:
            return self._adapters[platform_key]

        adapter_map = {
            "opire": _get_opire_adapter(),
            "issuehunt": _get_issuehunt_adapter(),
            "freelancer": _get_freelancer_adapter(),
            "algora": _get_algora_adapter(),
            "github": _get_github_bounty_adapter(),
            "github_bounty": _get_github_bounty_adapter(),
        }

        if platform_key not in adapter_map:
            raise ValueError(f"Unsupported adapter for auto-submit: {platform_key}")

        adapter = adapter_map[platform_key]
        self._adapters[platform_key] = adapter
        return adapter

    def _get_adapter_or_none(self, platform_key: str) -> Any | None:
        """`_get_adapter` sin lanzar: el adapter puede no existir para la plataforma."""
        try:
            return self._get_adapter(platform_key)
        except ValueError:
            return None

    def _get_api_key(self, platform: str) -> str | None:
        """Retrieve API key. Orden canónico de resolución (3 tiers).

        Antes sólo consultaba `IdentityVault`. Eso dejaba dos agujeros medidos:

        1. Los adapters resuelven su propia credencial (env → credentials vault →
           IdentityVault, ver `GitHubBountyAdapter._resolve_token`), pero el motor
           abortaba con `ValueError` **antes** de dejarles ejecutar — dejando su
           salida fail-closed `needs_access` como código muerto.
        2. Un `GITHUB_TOKEN` pegado en `~/.config/ownex/opportunity.env` — que es
           exactamente donde el propio adapter dice pegarlo — era ignorado, y el
           item terminaba en DLQ tras 3 reintentos.

        Ahora el motor usa el mismo orden que los adapters. One Source of Truth
        del orden de resolución.
        """
        env_names = _ENV_KEY_NAMES.get(platform, ())
        for env_name in env_names:
            token = os.environ.get(env_name, "").strip()
            if token:
                return token

        try:
            from cores.credentials import vault as _creds_vault

            creds = _creds_vault.get_credentials(force_refresh=True)
            for attr in _VAULT_ATTR_BY_PLATFORM.get(platform, ()):
                token = str(getattr(creds, attr, "") or "").strip()
                if token:
                    return token
        except Exception as exc:
            logger.debug("credentials vault unavailable for %s: %s", platform, exc)

        try:
            # Try platform-specific key first
            creds = self.vault.get_credentials(f"platform_{platform}")
            if creds and creds.get("token"):
                return creds["token"]
            # Fallback to generic platform name
            creds = self.vault.get_credentials(platform)
            if creds and creds.get("token"):
                return creds["token"]
            # Try common variations
            for prefix in ("", "platform_"):
                creds = self.vault.get_credentials(f"{prefix}{platform}_api_key")
                if creds and creds.get("token"):
                    return creds["token"]
                creds = self.vault.get_credentials(f"{prefix}{platform}_api")
                if creds and creds.get("token"):
                    return creds["token"]
        except Exception:
            return None
        return None

    async def submit_workbank_item(
        self, item_id: str, platform: str, opportunity: dict[str, Any], force: bool = False
    ) -> SubmissionRecord:
        """Submit a WorkBank item to its platform via API.

        Args:
            item_id: WorkBank item ID
            platform: Platform key (hackerone, bugcrowd, opire, etc.)
            opportunity: Full opportunity data
            force: Re-submit even if already submitted/confirmed

        Returns:
            SubmissionRecord with current status
        """
        # Generate idempotency key
        idempotency_key = f"{platform}:{item_id}:{uuid.uuid4().hex[:8]}"

        # Check for existing submission
        existing = self._find_submission(item_id, platform)
        if existing and existing.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.CONFIRMED) and not force:
            logger.info(f"Submission already exists for {item_id} on {platform}: {existing.id}")
            self._record_revenue_bridge(existing, opportunity)
            return existing

        # Create new submission record
        record = SubmissionRecord(
            id=idempotency_key,
            platform=platform,
            opportunity_id=item_id,
            opportunity_title=opportunity.get("title", "Unknown"),
            idempotency_key=idempotency_key,
            status=SubmissionStatus.PENDING,
            metadata={"opportunity": opportunity},
        )
        self._submissions[record.id] = record
        self._save_queue()

        # Execute submission with retries
        record = await self._execute_submission(record, opportunity)
        self._record_revenue_bridge(record, opportunity)
        return record

    def _record_revenue_bridge(self, record: SubmissionRecord, opportunity: dict[str, Any]) -> None:
        """Registra el resultado en el RevenueTracker. Nunca rompe el envío.

        Un fallo del bridge se persiste en `record.metadata` (y en la cola): que
        el bookkeeping no bloquee el envío no puede significar que nadie se entere
        de que faltó el revenue_event.
        """
        try:
            from cores.revenue_tracker.execution_bridge import record_submission_outcome

            record_submission_outcome(record, opportunity)
            # Éxito: se limpia un fallo anterior, si lo hubo.
            record.metadata.pop("revenue_bridge_error", None)
        except Exception as exc:  # revenue never blocks submission
            # Se traga para no perder el envío, pero NO en silencio: el registro
            # se persiste en la cola, así que el fallo queda consultable. Sin
            # esto, un envío "correcto" puede no tener revenue_event y nadie
            # sabe por qué.
            logger.warning("Revenue bridge skipped for %s: %s", getattr(record, "id", "?"), exc)
            record.metadata["revenue_bridge_error"] = {
                "error": f"{type(exc).__name__}: {exc}",
                "at": datetime.now(UTC).isoformat(),
                "meaning": "el envío se registró, pero NO hay revenue_event: revisá esto",
            }
        # La cola es lo que sobrevive al reinicio: si el fallo no queda ahí,
        # no queda en ninguna parte.
        self._save_queue()

    async def _execute_submission(self, record: SubmissionRecord, opportunity: dict[str, Any]) -> SubmissionRecord:
        """Execute the submission with retry logic."""
        platform = record.platform

        while record.attempts < record.max_attempts:
            record.attempts += 1
            record.status = SubmissionStatus.SUBMITTING
            record.updated_at = datetime.now(UTC).isoformat()
            self._save_queue()

            try:
                logger.info(f"Submitting {record.opportunity_id} to {platform} (attempt {record.attempts})")

                # Prepare the work using AssistedExecutor
                assisted = AssistedExecutor(base_executor=None)
                prepared = await assisted.prepare_work(opportunity)
                record.prepared_work = prepared

                # assisted mode genera un SCAFFOLD: el enunciado pegado en
                # un markdown con placeholders. Enviarlo a una plataforma real
                # es mandar un placeholder bajo el nombre del owner, y el
                # sistema lo hacia sin preguntar. Se detiene aqui, ANTES de
                # gastar un intento y antes de tocar la red.
                # Cesión: si esto es un bounty de CÓDIGO con repo e issue
                # parseables, el trabajo real lo hace DevBountyPipeline (LLM +
                # tests + PR). assisted mode no puede, y caer de vuelta al
                # scaffold sería el bug que se acaba de cerrar.
                parsed = _github_issue(str(opportunity.get("url") or ""))
                if parsed is not None:
                    owner, repo_name, issue_number = parsed
                    record.status = SubmissionStatus.PREPARING
                    record.metadata["delegated_to"] = "dev_bounty_pipeline"
                    self._save_queue()
                    try:
                        from cores.autonomy.dev_bounty_pipeline import get_dev_bounty_pipeline

                        result = await get_dev_bounty_pipeline().execute_dev_bounty(
                            bounty_id=record.opportunity_id,
                            platform=platform,
                            repo_url=f"https://github.com/{owner}/{repo_name}",
                            issue_number=issue_number,
                            issue_url=str(opportunity.get("url") or ""),
                            title=str(opportunity.get("title") or ""),
                            description=str(opportunity.get("description") or ""),
                        )
                    except Exception as exc:
                        # Sin red, sin LLM, sin repo clonado: NO se cae al
                        # scaffold. Se bloquea diciendo por qué.
                        record.status = SubmissionStatus.READY
                        record.last_error = f"delegacion fallida: {type(exc).__name__}: {exc}"
                        record.metadata["blocked_by"] = "delegation_failed"
                        record.metadata["blocked_note"] = (
                            "DevBountyPipeline fallo. NO se vuelve al scaffold a proposito: "
                            "enviar un placeholder en tu nombre es peor que no enviar."
                        )
                        record.updated_at = datetime.now(UTC).isoformat()
                        self._save_queue()
                        logger.exception("Delegacion a DevBountyPipeline fallo para %s", record.id)
                        return record

                    # El pipeline ya envío y ya registró el outcome en
                    # RevenueTracker. Volver a hacerlo aquí sería doble
                    # envío y doble revenue.
                    # El pipeline es fail-closed: si el PR falla (por falta de
                    # aprobación, por tests en rojo) devuelve `failed` y nunca
                    # llega a enviar. Esa salida NO es un envío.
                    # El mapeo anterior caía a SUBMITTED en cualquier verdict
                    # distinto de "submitted" — o sea, un fallo quedaba
                    # registrado como enviado. Es el bug que este mismo commit
                    # arregla en otro sitio, reintroducido aquí.
                    verdict = str(getattr(result, "verdict", "") or "")
                    if verdict == "submitted":
                        record.status = SubmissionStatus.SUBMITTED
                    else:
                        record.status = SubmissionStatus.FAILED
                        record.last_error = str(getattr(result, "error", "") or f"pipeline verdict={verdict}")
                        record.metadata["blocked_by"] = "pipeline_failed"
                        record.metadata["blocked_note"] = (
                            "DevBountyPipeline no llegó a enviar. El verdict y el error "
                            "quedan registrados; esto NO es un envío."
                        )
                    record.metadata["pipeline_reference"] = getattr(result, "pr_url", None) or getattr(
                        result, "submission_id", None
                    )
                    record.metadata["pipeline_verdict"] = getattr(result, "verdict", None)
                    record.updated_at = datetime.now(UTC).isoformat()
                    self._save_queue()
                    self._record_revenue_bridge(record, opportunity)
                    return record

                if getattr(prepared, "metadata", {}).get("requires_implementation"):
                    record.status = SubmissionStatus.READY
                    record.last_error = "scaffold sin implementar: assisted mode no genera el trabajo"
                    record.metadata["blocked_by"] = "requires_implementation"
                    record.metadata["blocked_note"] = (
                        "Falta el trabajo real (implementación + tests + evidencia). "
                        "El camino que lo produce es cores/autonomy/code_generator.py "
                        "(GenerationPlan) vía dev_bounty_pipeline, no assisted mode."
                    )
                    record.updated_at = datetime.now(UTC).isoformat()
                    self._save_queue()
                    self._notify(
                        "submission:blocked",
                        id=record.id,
                        message=(
                            f"Bloqueado: {platform} requiere trabajo real, y assisted mode sólo genera el scaffold"
                        ),
                    )
                    return record

                # Save to disk for user review
                work_dir = await assisted.save_work_to_disk(prepared)
                record.metadata["package_path"] = str(work_dir)

                # Get API key. NO abortar si falta: un adapter puede resolver su
                # propia credencial y/o devolver `needs_access` fail-closed con el
                # requisito humano exacto. Antes el `raise` las dejaba como
                # código muerto y el item iba a DLQ (ver KNOWN_DEBT #56).
                api_key = self._get_api_key(platform) or ""
                if not api_key and self._get_adapter_or_none(platform) is None:
                    raise ValueError(f"No API key configured for {platform}")

                # Execute platform-specific submission
                result = await self._submit_to_platform(platform, prepared, api_key)

                # If API submission failed, try Computer Use fallback
                if not result.get("success") and self._should_try_computer_use(platform):
                    logger.info(f"API submission failed for {platform}, trying Computer Use fallback")
                    result = await self._submit_via_computer_use(platform, prepared, record)

                record.submission_result = result

                if result.get("success"):
                    # Sólo un envío REAL se marca SUBMITTED. Antes el status se
                    # seteaba incondicionalmente antes de mirar success, así que
                    # un fallo quedaba registrado como enviado: contaminaba el
                    # revenue bridge (SUBMITTED → REVIEWING) y, peor, `_find_submission`
                    # lo contaba como ya-enviado para siempre (línea del skip).
                    record.status = SubmissionStatus.SUBMITTED
                    record.submitted_at = datetime.now(UTC).isoformat()
                    record.updated_at = datetime.now(UTC).isoformat()
                    self._save_queue()

                    # Poll for confirmation
                    external_id = result.get("external_id")
                    if external_id:
                        confirmed = await self._poll_confirmation(platform, external_id, api_key)
                    else:
                        confirmed = False
                    if confirmed:
                        record.status = SubmissionStatus.CONFIRMED
                        record.confirmed_at = datetime.now(UTC).isoformat()
                        logger.info(f"Submission confirmed: {record.id}")
                        self._notify(
                            "submission:confirmed",
                            id=record.id,
                            message=f"Submission confirmado en {platform}: {record.opportunity_id}",
                        )
                    else:
                        record.status = SubmissionStatus.SUBMITTED  # Submitted, awaiting review
                        self._notify(
                            "submission:submitted",
                            id=record.id,
                            message=f"Submission enviado a {platform}, esperando revisión: {record.opportunity_id}",
                        )
                    self._save_queue()
                    return record
                else:
                    # Un envío fallido NO es un envío. `FAILED` (no SUBMITTED) para
                    # que el retry siga vivo y `_find_submission` lo reintente.
                    record.status = SubmissionStatus.FAILED
                    record.last_error = result.get("error") or result.get("state") or "Unknown error"
                    record.updated_at = datetime.now(UTC).isoformat()
                    self._save_queue()
                    logger.warning(f"Submission failed (attempt {record.attempts}): {record.last_error}")

            except Exception as exc:
                record.last_error = str(exc)
                logger.exception(f"Submission error for {record.id}: {exc}")

            # Exponential backoff
            if record.attempts < record.max_attempts:
                delay = min(self.base_retry_delay * (2 ** (record.attempts - 1)), self.max_retry_delay)
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        # All attempts exhausted -> DLQ
        record.status = SubmissionStatus.DLQ
        record.updated_at = datetime.now(UTC).isoformat()
        self._move_to_dlq(record)
        self._save_queue()
        logger.error(f"Submission moved to DLQ after {record.max_attempts} attempts: {record.id}")
        self._notify(
            "submission:dead_letter",
            id=record.id,
            message=(
                f"Submission a DLQ tras {record.max_attempts} intentos: "
                f"{record.opportunity_id} ({record.last_error or 'sin detalle'})"
            ),
        )
        return record

    async def _submit_to_platform(self, platform: str, prepared: PreparedWork, api_key: str) -> dict[str, Any]:
        """Submit prepared work to specific platform."""
        # Dev-bounty platforms route to adapters FIRST (they are not in _get_platform).
        try:
            adapter = self._get_adapter(platform)
        except ValueError:
            adapter = None
        if adapter is not None and hasattr(adapter, "submit_work"):
            return await adapter.submit_work(prepared, api_key)

        platform_impl = self._get_platform(platform)

        # Convert PreparedWork to platform report format
        report_data = {
            "title": prepared.title,
            "vulnerability": prepared.metadata.get("opportunity", {}).get("description", ""),
            "program": prepared.metadata.get("opportunity", {}).get("program", ""),
            "severity": prepared.metadata.get("opportunity", {}).get("severity", "medium"),
            "content": prepared.files,
            "url": prepared.submission_url,
        }

        # For bug bounty platforms, use their submit method
        if hasattr(platform_impl, "submit"):
            result = platform_impl.submit(report_data, api_key)
            return {
                "success": result.success,
                "external_id": result.external_id,
                "url": result.url,
                "error": result.error,
                "data": result.data,
            }

        return {"success": False, "error": f"Platform {platform} does not support auto-submission"}

    async def _poll_confirmation(self, platform: str, external_id: str, api_key: str, max_polls: int = 10) -> bool:
        """Poll platform for submission confirmation."""
        platform_impl = self._get_platform(platform)

        for _i in range(max_polls):
            await asyncio.sleep(30)  # Wait 30s between polls
            try:
                status = platform_impl.check_status(external_id, api_key)
                if status in ("triaged", "resolved", "paid", "confirmed"):
                    return True
                if status in ("rejected", "duplicate", "informative"):
                    return False  # Final negative state
            except Exception:
                pass

        return False  # Timeout - still pending review

    def _should_try_computer_use(self, platform: str) -> bool:
        """Check if Computer Use fallback should be attempted."""
        try:
            from cores.computer_use.submission_executor import should_use_computer_use

            return should_use_computer_use(platform, api_submission_failed=True)
        except ImportError:
            return False

    async def _submit_via_computer_use(
        self, platform: str, prepared: PreparedWork, record: SubmissionRecord
    ) -> dict[str, Any]:
        """Submit via Computer Use (desktop form filling) as fallback."""
        try:
            from cores.computer_use.submission_executor import get_computer_use_executor

            executor = get_computer_use_executor()
            if not executor.can_handle(platform):
                return {"success": False, "error": f"Computer Use cannot handle {platform}"}

            work_data = {
                "title": prepared.title,
                "description": prepared.metadata.get("opportunity", {}).get("description", ""),
                "severity": prepared.metadata.get("opportunity", {}).get("severity", "medium"),
                "program": prepared.metadata.get("opportunity", {}).get("program", ""),
            }

            result = await executor.submit(
                platform=platform,
                work_data=work_data,
                work_item_id=record.opportunity_id,
                opportunity_title=record.opportunity_title,
            )

            return {
                "success": result.success,
                "method": "computer_use",
                "error": result.error,
                "duration_ms": result.duration_ms,
                "screenshots": result.screenshots,
            }
        except Exception as exc:
            logger.warning(f"Computer Use fallback failed for {platform}: {exc}")
            return {"success": False, "error": f"Computer Use fallback failed: {exc}"}

    def _find_submission(self, opportunity_id: str, platform: str) -> SubmissionRecord | None:
        """Find existing submission for opportunity/platform."""
        for record in self._submissions.values():
            if record.opportunity_id == opportunity_id and record.platform == platform:
                return record
        return None

    def get_submission(self, submission_id: str) -> SubmissionRecord | None:
        """Get submission by ID."""
        return self._submissions.get(submission_id)

    def list_submissions(
        self, status: SubmissionStatus | None = None, platform: str | None = None
    ) -> list[SubmissionRecord]:
        """List submissions with optional filters."""
        results = list(self._submissions.values())
        if status:
            results = [r for r in results if r.status == status]
        if platform:
            results = [r for r in results if r.platform == platform]
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    def get_dlq(self) -> list[SubmissionRecord]:
        """Get all dead-letter queue items."""
        return self.list_submissions(status=SubmissionStatus.DLQ)

    async def retry_dlq(self, submission_id: str) -> SubmissionRecord | None:
        """Retry a DLQ item."""
        record = self._submissions.get(submission_id)
        if not record or record.status != SubmissionStatus.DLQ:
            return None
        record.status = SubmissionStatus.PENDING
        record.attempts = 0
        record.last_error = None
        record.updated_at = datetime.now(UTC).isoformat()
        self._save_queue()
        return await self._execute_submission(record, record.metadata.get("opportunity", {}))

    # Notifications
    def _notify(self, event_type: str, **payload: Any) -> None:
        """Publish a user-facing outcome. Never raises: the submit must survive."""
        try:
            from cores.notifications.emit import emit

            emit(event_type, **payload)
        except Exception as exc:
            logger.debug("emit(%s) skipped: %s", event_type, exc)

    # Persistence
    def _save_queue(self) -> None:
        """Persist submission queue to disk."""
        queue_file = self._queue_path
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "submissions": {k: v.to_dict() for k, v in self._submissions.items()},
        }
        queue_file.write_text(json.dumps(data, indent=2))

    def _load_queue(self) -> None:
        """Load submission queue from disk."""
        queue_file = self._queue_path
        if not queue_file.exists():
            return
        try:
            data = json.loads(queue_file.read_text())
            for k, v in data.get("submissions", {}).items():
                v["status"] = SubmissionStatus(v["status"])
                if v.get("prepared_work"):
                    # Reconstruct PreparedWork (simplified)
                    pass
                self._submissions[k] = SubmissionRecord(**v)
        except Exception as exc:
            logger.warning(f"Could not load submission queue: {exc}")

    def _move_to_dlq(self, record: SubmissionRecord) -> None:
        """Move failed submission to DLQ file."""
        dlq_file = self.dlq_path / f"{record.id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        dlq_file.write_text(json.dumps(record.to_dict(), indent=2))
        logger.warning(f"Submission moved to DLQ: {dlq_file}")


# Global instance
_auto_submit_engine: AutoSubmitEngine | None = None


def get_auto_submit_engine() -> AutoSubmitEngine:
    global _auto_submit_engine
    if _auto_submit_engine is None:
        _auto_submit_engine = AutoSubmitEngine()
    return _auto_submit_engine


# API entry point
async def auto_submit_workbank_item(
    item_id: str, platform: str, opportunity: dict[str, Any], force: bool = False
) -> dict[str, Any]:
    """Public API: submit a WorkBank item to its platform."""
    engine = get_auto_submit_engine()
    record = await engine.submit_workbank_item(item_id, platform, opportunity, force)
    return record.to_dict()
