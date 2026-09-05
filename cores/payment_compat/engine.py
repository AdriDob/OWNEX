"""Payment Compatibility Engine — decides whether OWNEX can collect a payout.

Deterministic evaluation chain for every opportunity:

    PAYMENT METHOD -> REQUIRED COUNTRY -> CURRENCY -> AVAILABLE OWNEX ACCOUNTS -> COMPATIBLE?

The engine never invents solutions: if a platform requires residency, an
entity or documentation OWNEX does not have, the verdict is
``incompatible`` with an explicit reason. Opening accounts to bypass a
platform restriction is never suggested.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from cores.financial_intelligence.argentina_payout_methods import (
    ARGENTINA_PAYOUT_METHODS,
)
from cores.payment_compat.network import (
    PAYMENT_NETWORK,
    OwnAccount,
    PaymentFunction,
    PaymentLayer,
    get_account,
)

logger = logging.getLogger("ownex.payment_compat")

# Methods that require a bank account in a specific jurisdiction
_REGION_BOUND_METHODS: dict[str, str] = {
    "ach": "usa",
    "wire": "usa",
    "sepa": "eu",
    "cbu": "argentina",
    "cvu": "argentina",
}

# Documentación que OWNEX bloquea automáticamente (no tiene forma de satisfacerlas)
_DOCUMENTATION_BLOCKED: set[str] = {
    "llc",
    "us_entity",
    "eu_residency",
    "us_residency",
    "uk_entity",
}

# Documentación que OWNEX acepta sin bloqueo
_DOCUMENTATION_ACCEPTED: set[str] = {
    "kyc",
    "kyc_personal",
    "id",
}

# Metadatos enriquecidos desde el catálogo Argentina Payout Methods
# (reliability, fees, withdrawal limits, notes). Se usa para dar contexto
# en el reason y un pequeño boost al score cuando la cuenta tiene datos documentados.
_PAYOUT_META_CACHE: dict[str, dict[str, Any]] = {}


def _get_payout_meta(account_id: str) -> dict[str, Any] | None:
    """Obtener metadatos desde ARGENTINA_PAYOUT_METHODS por payout_ref."""
    # Usar caché en memoria para evitar repetidas consultas
    if account_id in _PAYOUT_META_CACHE:
        return _PAYOUT_META_CACHE[account_id]

    account = get_account(account_id)
    if not account or not account.payout_ref:
        return None

    # Usar ARGENTINA_PAYOUT_METHODS (importado en módulo) directamente
    for m in ARGENTINA_PAYOUT_METHODS:
        if m.id == account.payout_ref:
            meta = {
                "reliability": m.reliability_score,
                "fees_pct": sum(m.fees.values()) if m.fees else 0.0,
                "min_withdrawal": m.minimum_withdrawal,
                "max_withdrawal": m.maximum_withdrawal,
                "notes": m.notes,
            }
            _PAYOUT_META_CACHE[account_id] = meta
            return meta

    return None


# Bank-transfer methods: receiving is viable on its own, conversion is manual
_BANK_METHODS = {"ach", "wire", "sepa", "paypal", "cbu", "cvu", "local_transfer"}

_METHOD_LABELS: dict[str, str] = {
    "ach": "ACH",
    "wire": "WIRE",
    "sepa": "SEPA",
    "cbu": "CBU",
    "cvu": "CVU",
    "paypal": "PAYPAL",
    "crypto": "CRYPTO",
    "p2p": "P2P",
    "card": "CARD",
    "cash": "CASH",
    "local_transfer": "LOCAL_TRANSFER",
    "marketplace": "MARKETPLACE",
    "wallet": "WALLET",
}

_LAYER_LABELS: dict[PaymentLayer, str] = {
    PaymentLayer.BANKING: "banking",
    PaymentLayer.PROCESSORS: "processors",
    PaymentLayer.CRYPTO: "crypto",
    PaymentLayer.SELF_CUSTODY: "self_custody",
    PaymentLayer.WITHDRAWAL: "withdrawal",
}

_FUNCTION_LABELS: dict[PaymentFunction, str] = {
    PaymentFunction.PRIMARY: "primary",
    PaymentFunction.US_ACCOUNT: "us_account",
    PaymentFunction.GLOBAL: "global",
    PaymentFunction.PAYOUT: "payout",
    PaymentFunction.LOCAL: "local",
    PaymentFunction.BACKUP: "backup",
    PaymentFunction.SPECIALIZED: "specialized",
}


@dataclass
class PaymentRequirement:
    """What the platform needs to pay OWNEX."""

    method: str = "crypto"
    currency: str = "USDC"
    region: str = "global"
    amount: float = 0.0
    required_documentation: str = ""
    platform: str = ""


@dataclass
class PaymentMatch:
    """A compatible OWNEX account for a requirement."""

    account_id: str
    account_name: str
    layer: str
    function: str
    reason: str = ""
    score: float = 0.0


@dataclass
class PaymentVerdict:
    """Result of evaluating whether OWNEX can collect a payout."""

    compatible: bool
    viable: bool
    score: float
    requirement: dict[str, Any]
    matches: list[PaymentMatch] = field(default_factory=list)
    off_ramp: list[PaymentMatch] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    honest_notes: list[str] = field(default_factory=list)


class PaymentCompatibilityEngine:
    """Decides whether an opportunity payout can be collected."""

    def __init__(self, network: list[OwnAccount] | None = None) -> None:
        self._network = network or PAYMENT_NETWORK
        self._configured_path = os.path.expanduser("~/.config/ownex/payment_network.json")
        os.makedirs(os.path.dirname(self._configured_path), exist_ok=True)
        self._configured_accounts: list[str] = self._load_configured()

    def _load_configured(self) -> list[str]:
        """Load configured account IDs from persistent storage."""
        try:
            with open(self._configured_path, encoding="utf-8") as f:
                data = json.load(f)
                return data.get("configured_accounts", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_configured(self) -> None:
        """Persist configured account IDs to disk."""
        with open(self._configured_path, "w", encoding="utf-8") as f:
            json.dump({"configured_accounts": self._configured_accounts}, f, indent=2, ensure_ascii=False)

    def set_configured_accounts(self, account_ids: list[str]) -> None:
        """Set the list of configured account IDs and persist them."""
        self._configured_accounts = account_ids
        self._save_configured()

    def get_configured_accounts(self) -> list[str]:
        """Get the list of configured account IDs."""
        return list(self._configured_accounts)

    def has_cvu_configured(self) -> bool:
        """Check if any configured account supports CVU withdrawals (local ARS off-ramp)."""
        cvu_account_ids = {
            a.id
            for a in self._network
            if a.layer == PaymentLayer.BANKING
            and a.function in (PaymentFunction.LOCAL, PaymentFunction.PAYOUT)
            and any(m in {"cvu", "cbu", "local_transfer"} for m in a.methods)
        }
        return bool(set(self._configured_accounts) & cvu_account_ids)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def evaluate(self, requirement: PaymentRequirement) -> PaymentVerdict:
        """Evaluate a single payment requirement against the network."""
        req = self._normalize_requirement(requirement)
        honest_notes: list[str] = []
        missing: list[str] = []

        documentation = self._check_documentation(req)
        if documentation:
            missing.append(documentation)
            honest_notes.append(
                "La plataforma exige documentación que OWNEX no tiene; no se sugiere ningún workaround."
            )

        method_region = _REGION_BOUND_METHODS.get(req.method.lower())
        if method_region and req.region != method_region:
            missing.append(
                f"El método {_METHOD_LABELS.get(req.method, req.method)} "
                f"requiere cuenta en {method_region.upper()}, pedida para {req.region.upper()}."
            )
        matches = self._find_matches(req)

        score = self._score_requirement(req, matches, bool(documentation))
        compatible = bool(matches) and not missing and not documentation
        viable = compatible

        if compatible and req.amount > 0:
            for m in matches:
                if m.score < 40:
                    viable = False
                    missing.append(f"{m.account_name}: condiciones limitadas para este monto")
                    break
        return PaymentVerdict(
            compatible=compatible,
            viable=viable,
            score=round(score, 1),
            requirement=self._requirement_dict(req),
            matches=matches,
            missing=missing,
            honest_notes=honest_notes,
        )

    def evaluate_chain(
        self,
        requirement: PaymentRequirement,
        final_currency: str = "ARS",
    ) -> PaymentVerdict:
        """Evaluate receive + off-ramp: can OWNEX receive AND convert to the final currency."""
        verdict = self.evaluate(requirement)
        if not verdict.compatible:
            return verdict

        if requirement.currency.upper() == final_currency.upper():
            verdict.viable = True
            return verdict

        if requirement.method.lower() in _BANK_METHODS:
            verdict.viable = True
            verdict.honest_notes.append(
                f"Receiving viable en {requirement.region.upper()}; la conversión a "
                f"{final_currency.upper()} es manual (transferencia desde la cuenta bancaria)."
            )
            return verdict

        off_ramp = self._find_off_ramp(requirement, final_currency=final_currency)
        verdict.off_ramp = off_ramp
        if not off_ramp:
            verdict.viable = False
            verdict.missing.append(f"No hay salida a {final_currency.upper()} desde los métodos disponibles.")
        else:
            verdict.viable = True
        return verdict

    def network_summary(self) -> dict[str, Any]:
        """Catalog grouped by layer and function."""
        by_layer: dict[str, list[str]] = {}
        by_function: dict[str, list[str]] = {}
        by_region: dict[str, list[str]] = {}
        for account in self._network:
            layer = _LAYER_LABELS.get(account.layer, account.layer.value)
            function = _FUNCTION_LABELS.get(account.function, account.function.value)
            by_layer.setdefault(layer, []).append(account.id)
            by_function.setdefault(function, []).append(account.id)
            for region in account.regions:
                by_region.setdefault(region.value, []).append(account.id)
        return {
            "total_accounts": len(self._network),
            "by_layer": by_layer,
            "by_function": by_function,
            "by_region": by_region,
        }

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------
    def _find_matches(self, req: PaymentRequirement) -> list[PaymentMatch]:
        matches: list[PaymentMatch] = []
        for account in self._network:
            if not account.matches_method(req.method):
                continue
            if not account.matches_region(req.region):
                continue
            if req.currency.upper() not in {c.upper() for c in account.currencies}:
                continue
            matches.append(self._build_match(account, req))
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def _find_off_ramp(self, req: PaymentRequirement, final_currency: str) -> list[PaymentMatch]:
        """Accounts that receive crypto and convert to the final currency."""
        ramps: list[PaymentMatch] = []
        for account in self._network:
            if account.layer != PaymentLayer.CRYPTO:
                continue
            if not account.matches_method(req.method):
                continue
            currencies = {c.upper() for c in account.currencies}
            if req.currency.upper() not in currencies:
                continue
            if final_currency.upper() not in currencies:
                continue
            if not account.matches_region(req.region):
                continue
            ramps.append(self._build_match(account, req, is_off_ramp=True))
        ramps.sort(key=lambda m: m.score, reverse=True)
        return ramps

    def _build_match(self, account: OwnAccount, req: PaymentRequirement, is_off_ramp: bool = False) -> PaymentMatch:
        score = 100.0
        if account.function in (PaymentFunction.PRIMARY, PaymentFunction.US_ACCOUNT, PaymentFunction.LOCAL):
            score += 10
        if account.kyc_required:
            score -= 5
        if is_off_ramp:
            score += 5
        if req.region == "global" and payment_function_boost(account.function) < 0:
            score += payment_function_boost(account.function)

        # CVU boost per-match: si el usuario tiene CVU y la cuenta soporta salida a CVU,
        # bonificar el score individual (especialmente útil para off_ramp).
        if self.has_cvu_configured() and account.supports_cvu_out:
            score += 8.0

        # Enriquecimiento con metadatos desde ArgentinaPayoutMethods
        meta = _get_payout_meta(account.id)
        if meta:
            # Boost ligero por confiabilidad documentada (0-5 puntos)
            score += min(5.0, meta["reliability"] * 0.1)
            # Construir reason con metadatos opcionales
            reason_parts = [self._match_reason(account, req, is_off_ramp)]
            if meta["notes"]:
                notes_preview = meta["notes"][:80].replace("\n", " ")
                reason_parts.append(f"({notes_preview})")
            reason = " ".join(reason_parts)
        else:
            reason = self._match_reason(account, req, is_off_ramp)
        score = round(min(score, 100.0), 1)
        return PaymentMatch(
            account_id=account.id,
            account_name=account.name,
            layer=_LAYER_LABELS.get(account.layer, account.layer.value),
            function=_FUNCTION_LABELS.get(account.function, account.function.value),
            reason=reason,
            score=score,
        )

    def _match_reason(self, account: OwnAccount, req: PaymentRequirement, is_off_ramp: bool) -> str:
        if is_off_ramp:
            return (
                f"Recibe {req.currency.upper()} y convierte a salida local; retiro disponible según cuenta/condiciones."
            )
        method_label = _METHOD_LABELS.get(req.method, req.method)
        region = req.region.upper()
        return f"Compatible con {account.name}. {req.currency.upper()} · {method_label} · {region}."

    # ------------------------------------------------------------------
    # Honesty rules
    # ------------------------------------------------------------------
    def _check_documentation(self, req: PaymentRequirement) -> str:
        doc = (req.required_documentation or "").strip().lower()
        if not doc:
            return ""
        if doc in _DOCUMENTATION_ACCEPTED:
            return ""
        if doc in _DOCUMENTATION_BLOCKED:
            return f"Exige {doc.upper()} (documentación de entidad/residencia que OWNEX no tiene)."
        # Catch-all: cualquier otro string no reconocido se trata como bloqueante
        return f"Exige documentación no reconocida ({doc.upper()})."

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------
    def _score_requirement(
        self,
        req: PaymentRequirement,
        matches: list[PaymentMatch],
        blocked: bool,
    ) -> float:
        if blocked:
            return 0.0
        if not matches:
            return 0.0
        best = matches[0].score
        # Bonus por tener metadatos documentados (payout_ref): indica cuenta real con
        # confiabilidad y fees conocidos, en lugar de una cuenta genérica.
        documented_bonus = 0.0
        for m in matches:
            account = get_account(m.account_id)
            if account and account.payout_ref:
                documented_bonus = max(documented_bonus, min(5.0, account.payout_ref and 5 or 0))
                break
        # CVU boost: si el usuario tiene CVU configurado y la requirement implica
        # conversión a ARS, bonificar cuentas que soporten salida a CVU.
        cvu_bonus = 0.0
        if self.has_cvu_configured():
            for m in matches:
                account = get_account(m.account_id)
                if account and account.supports_cvu_out:
                    # Boost moderado (0-10 puntos) por tener off-ramp CVU real
                    cvu_bonus = max(cvu_bonus, 8.0)
                    break
        coverage = len(matches) / max(1, len(self._network)) * 20
        return min(100.0, best * 0.8 + coverage + documented_bonus + cvu_bonus)

    def _normalize_requirement(self, req: PaymentRequirement) -> PaymentRequirement:
        region = (req.region or "global").lower()
        # Map ISO country codes to Region enum values
        region_map = {
            "ar": "argentina",
            "us": "usa",
            "usa": "usa",
            "eu": "eu",
            "europe": "eu",
            "global": "global",
            "world": "global",
        }
        region = region_map.get(region, region)
        return PaymentRequirement(
            method=(req.method or "crypto").lower(),
            currency=(req.currency or "USD").upper(),
            region=region,
            amount=max(0.0, req.amount or 0.0),
            required_documentation=(req.required_documentation or "").strip(),
            platform=(req.platform or "").strip(),
        )

    @staticmethod
    def _requirement_dict(req: PaymentRequirement) -> dict[str, Any]:
        return {
            "method": req.method,
            "currency": req.currency,
            "region": req.region,
            "amount": req.amount,
            "required_documentation": req.required_documentation,
            "platform": req.platform,
        }


def payment_function_boost(function: PaymentFunction) -> float:
    """Small preference for settlement-oriented roles on global requirements."""
    if function in (PaymentFunction.PRIMARY, PaymentFunction.US_ACCOUNT):
        return 2.0
    if function == PaymentFunction.PAYOUT:
        return 1.0
    return -1.0


def get_payment_engine() -> PaymentCompatibilityEngine:
    """Get the shared PaymentCompatibilityEngine instance."""
    return PaymentCompatibilityEngine()


def account_to_dict(account: OwnAccount) -> dict[str, Any]:
    """Serialize an account for API responses."""
    return {
        "id": account.id,
        "name": account.name,
        "layer": _LAYER_LABELS.get(account.layer, account.layer.value),
        "function": _FUNCTION_LABELS.get(account.function, account.function.value),
        "regions": [r.value for r in account.regions],
        "currencies": account.currencies,
        "methods": account.methods,
        "networks": [n.value for n in account.networks],
        "kyc_required": account.kyc_required,
        "withdrawal_available": account.withdrawal_available,
        "notes": account.notes,
        "payout_ref": account.payout_ref,
    }


def get_account_or_none(account_id: str) -> OwnAccount | None:
    """Get an account by id, or None when missing."""
    return get_account(account_id)
