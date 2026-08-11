"""Scope Enforcement — capa unificada de cumplimiento de alcance por programa.

Esta capa centraliza toda la lógica de verificación de alcance (scope) que hoy
está dispersa en planners, validators, notificaciones y LLM scanners.

Responsabilidades:
1. Parsear scope policy de un programa (assets in-scope / out-of-scope, rules)
2. Verificar si un target/endpoint/asset está en alcance
3. Bloquear operaciones fuera de alcance antes de ejecutar
4. Emitir eventos para que otras capas reaccionen

No reemplaza validaciones existentes; es la fuente de verdad única de scope.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from cores.events.event_bus import EventBus, get_event_bus

LOG = logging.getLogger("ownex.scope_enforcement")


class ScopeDecision(StrEnum):
    """Resultado de verificación de alcance."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"  # programa sin policy configurada


class AssetType(StrEnum):
    """Tipos de asset que pueden estar en scope."""

    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    URL = "url"
    IP = "ip"
    CIDR = "cidr"
    WILDCARD = "wildcard"
    MOBILE_APP = "mobile_app"
    API_ENDPOINT = "api_endpoint"
    MOBILE_APP_ID = "mobile_app_id"


@dataclass(frozen=True, slots=True)
class ScopeRule:
    """Una regla de alcance individual (in-scope o out-of-scope)."""

    asset_type: AssetType
    pattern: str  # regex o string exacta según asset_type
    is_in_scope: bool  # True = in-scope, False = out-of-scope
    description: str = ""
    severity: str = "medium"  # critical/high/medium/low/info


@dataclass(frozen=True, slots=True)
class ProgramScopePolicy:
    """Policy completa de alcance de un programa."""

    program_id: str
    program_name: str
    platform: str  # hackerone, bugcrowd, intigriti, etc.
    rules: list[ScopeRule] = field(default_factory=list)
    raw_policy_text: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: int = 1

    def is_asset_in_scope(self, asset_type: AssetType, value: str) -> ScopeDecision:
        """Verifica si un asset está in-scope, out-of-scope, o unknown.

        Precedencia: exclusiones (out-of-scope) siempre ganan.
        """
        for rule in self.rules:
            if rule.asset_type == asset_type and not rule.is_in_scope and self._matches(rule, value):
                return ScopeDecision.OUT_OF_SCOPE
        for rule in self.rules:
            if rule.asset_type == asset_type and rule.is_in_scope and self._matches(rule, value):
                return ScopeDecision.IN_SCOPE
        return ScopeDecision.UNKNOWN

    def is_endpoint_in_scope(self, url: str) -> ScopeDecision:
        """Verifica si un endpoint (URL completa) está in-scope.

        Precedencia: cualquier exclusión (out-of-scope) gana sobre inclusiones.
        """
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # Pass 1 — exclusions always win
        for rule in self.rules:
            if rule.is_in_scope:
                continue
            matched = (
                (rule.asset_type in (AssetType.DOMAIN, AssetType.SUBDOMAIN) and self._matches(rule, host))
                or (rule.asset_type == AssetType.WILDCARD and self._matches_wildcard(rule, host))
                or (rule.asset_type == AssetType.API_ENDPOINT and self._matches_endpoint(rule, url))
                or (
                    rule.asset_type in (AssetType.IP, AssetType.CIDR)
                    and self._is_ip(host)
                    and self._matches(rule, host)
                )
            )
            if matched:
                return ScopeDecision.OUT_OF_SCOPE

        # Pass 2 — inclusions
        for rule in self.rules:
            if not rule.is_in_scope:
                continue
            matched = (
                (rule.asset_type in (AssetType.DOMAIN, AssetType.SUBDOMAIN) and self._matches(rule, host))
                or (rule.asset_type == AssetType.WILDCARD and self._matches_wildcard(rule, host))
                or (rule.asset_type == AssetType.API_ENDPOINT and self._matches_endpoint(rule, url))
                or (
                    rule.asset_type in (AssetType.IP, AssetType.CIDR)
                    and self._is_ip(host)
                    and self._matches(rule, host)
                )
            )
            if matched:
                return ScopeDecision.IN_SCOPE

        return ScopeDecision.UNKNOWN

    @staticmethod
    def _matches(rule: ScopeRule, value: str) -> bool:
        if rule.asset_type == AssetType.WILDCARD:
            return False  # handled separately
        try:
            return bool(re.fullmatch(rule.pattern, value, re.IGNORECASE))
        except re.error:
            return rule.pattern.lower() == value.lower()

    @staticmethod
    def _matches_wildcard(rule: ScopeRule, host: str) -> bool:
        """Matches wildcard like *.example.com"""
        pattern = rule.pattern
        if pattern.startswith("*."):
            suffix = pattern[2:].lower()
            return host.endswith(suffix) or host == suffix
        return False

    @staticmethod
    def _matches_endpoint(rule: ScopeRule, url: str) -> bool:
        try:
            return bool(re.search(rule.pattern, url, re.IGNORECASE))
        except re.error:
            return rule.pattern in url

    @staticmethod
    def _is_ip(value: str) -> bool:
        try:
            parts = value.split(":")[0].split(".")  # remove port if present
            return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts) and len(parts) == 4
        except (ValueError, AttributeError):
            return False


class ScopeEnforcer:
    """Motor central de cumplimiento de alcance.

    Unifica checks que hoy están en planners, validators, notificaciones y LLM scanners.
    """

    def __init__(self, event_bus: EventBus | None = None):
        self._policies: dict[str, ProgramScopePolicy] = {}
        self._event_bus = event_bus or get_event_bus()

    def register_policy(self, policy: ProgramScopePolicy) -> None:
        """Registra/actualiza la policy de un programa."""
        self._policies[policy.program_id] = policy
        LOG.info("Scope policy registered: %s (%s)", policy.program_name, policy.platform)

    def get_policy(self, program_id: str) -> ProgramScopePolicy | None:
        return self._policies.get(program_id)

    def check_endpoint(self, program_id: str, url: str) -> ScopeDecision:
        """Verifica si un endpoint está en alcance para un programa."""
        policy = self._policies.get(program_id)
        if not policy:
            return ScopeDecision.UNKNOWN
        decision = policy.is_endpoint_in_scope(url)
        self._emit_event(program_id, url, decision, "endpoint")
        return decision

    def check_asset(self, program_id: str, asset_type: AssetType, value: str) -> ScopeDecision:
        """Verifica si un asset (dominio, IP, etc.) está en alcance."""
        policy = self._policies.get(program_id)
        if not policy:
            return ScopeDecision.UNKNOWN
        decision = policy.is_asset_in_scope(asset_type, value)
        self._emit_event(program_id, value, decision, f"asset:{asset_type.value}")
        return decision

    def enforce_endpoint(self, program_id: str, url: str) -> None:
        """Fuerza la verificación: lanza excepción si está out-of-scope."""
        decision = self.check_endpoint(program_id, url)
        if decision == ScopeDecision.OUT_OF_SCOPE:
            raise ScopeViolationError(f"Endpoint {url} está OUT OF SCOPE para programa {program_id}")
        if decision == ScopeDecision.UNKNOWN:
            LOG.warning("Scope unknown para programa %s, endpoint: %s", program_id, url)

    def enforce_asset(self, program_id: str, asset_type: AssetType, value: str) -> None:
        """Fuerza la verificación de asset: lanza excepción si está out-of-scope."""
        decision = self.check_asset(program_id, asset_type, value)
        if decision == ScopeDecision.OUT_OF_SCOPE:
            raise ScopeViolationError(
                f"Asset {value} ({asset_type.value}) está OUT OF SCOPE para programa {program_id}"
            )

    def _emit_event(self, program_id: str, target: str, decision: ScopeDecision, check_type: str) -> None:
        self._event_bus.publish(
            "scope.check",
            program_id=program_id,
            target=target,
            decision=decision.value,
            check_type=check_type,
            timestamp=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def parse_from_platform(platform: str, raw_data: dict[str, Any]) -> ProgramScopePolicy:
        """Factory: parsea scope policy desde datos crudos de una plataforma."""
        if platform == "hackerone":
            return ScopeEnforcer._parse_hackerone(raw_data)
        if platform == "bugcrowd":
            return ScopeEnforcer._parse_bugcrowd(raw_data)
        if platform == "intigriti":
            return ScopeEnforcer._parse_intigriti(raw_data)
        raise ValueError(f"Plataforma no soportada: {platform}")

    @staticmethod
    def _parse_hackerone(data: dict) -> ProgramScopePolicy:
        """Parsea scope desde estructura HackerOne."""
        rules = []
        structured_scope = data.get("structured_scope", [])
        for item in structured_scope:
            asset_type = ScopeEnforcer._map_h1_asset_type(item.get("asset_type", ""))
            if asset_type:
                rules.append(
                    ScopeRule(
                        asset_type=asset_type,
                        pattern=item.get("asset_identifier", ""),
                        is_in_scope=item.get("eligible_for_submission", True),
                        description=item.get("instruction", ""),
                        severity=item.get("severity", "medium"),
                    )
                )
        return ProgramScopePolicy(
            program_id=str(data.get("id", "")),
            program_name=data.get("name", ""),
            platform="hackerone",
            rules=rules,
            raw_policy_text=data.get("policy", ""),
        )

    @staticmethod
    def _parse_bugcrowd(data: dict) -> ProgramScopePolicy:
        """Parsea scope desde estructura Bugcrowd."""
        rules = []
        targets = data.get("targets", [])
        for target in targets:
            asset_type = ScopeEnforcer._map_bc_asset_type(target.get("category", ""))
            if asset_type:
                rules.append(
                    ScopeRule(
                        asset_type=asset_type,
                        pattern=target.get("name", ""),
                        is_in_scope=target.get("in_scope", True),
                        description=target.get("description", ""),
                    )
                )
        return ProgramScopePolicy(
            program_id=str(data.get("id", "")),
            program_name=data.get("name", ""),
            platform="bugcrowd",
            rules=rules,
            raw_policy_text=data.get("brief", ""),
        )

    @staticmethod
    def _parse_intigriti(data: dict) -> ProgramScopePolicy:
        """Parsea scope desde estructura Intigriti."""
        rules = []
        scopes = data.get("scope", [])
        for scope in scopes:
            asset_type = ScopeEnforcer._map_intigriti_asset_type(scope.get("type", ""))
            if asset_type:
                rules.append(
                    ScopeRule(
                        asset_type=asset_type,
                        pattern=scope.get("endpoint", ""),
                        is_in_scope=scope.get("in_scope", True),
                        description=scope.get("description", ""),
                    )
                )
        return ProgramScopePolicy(
            program_id=str(data.get("id", "")),
            program_name=data.get("name", ""),
            platform="intigriti",
            rules=rules,
            raw_policy_text=data.get("description", ""),
        )

    @staticmethod
    def _map_h1_asset_type(h1_type: str) -> AssetType | None:
        mapping = {
            "URL": AssetType.URL,
            "DOMAIN": AssetType.DOMAIN,
            "SUBDOMAIN": AssetType.SUBDOMAIN,
            "IP": AssetType.IP,
            "CIDR": AssetType.CIDR,
            "WILDCARD": AssetType.WILDCARD,
            "MOBILE": AssetType.MOBILE_APP,
            "API": AssetType.API_ENDPOINT,
        }
        return mapping.get(h1_type.upper())

    @staticmethod
    def _map_bc_asset_type(bc_type: str) -> AssetType | None:
        mapping = {
            "website": AssetType.URL,
            "api": AssetType.API_ENDPOINT,
            "mobile": AssetType.MOBILE_APP,
            "domain": AssetType.DOMAIN,
            "ip": AssetType.IP,
        }
        return mapping.get(bc_type.lower())

    @staticmethod
    def _map_intigriti_asset_type(intigriti_type: str) -> AssetType | None:
        mapping = {
            "url": AssetType.URL,
            "domain": AssetType.DOMAIN,
            "wildcard": AssetType.WILDCARD,
            "api": AssetType.API_ENDPOINT,
            "mobile": AssetType.MOBILE_APP,
        }
        return mapping.get(intigriti_type.lower())


class ScopeViolationError(Exception):
    """Excepción lanzada cuando se intenta operar fuera de alcance."""

    pass


# Singleton
_enforcer: ScopeEnforcer | None = None


def get_scope_enforcer() -> ScopeEnforcer:
    global _enforcer
    if _enforcer is None:
        _enforcer = ScopeEnforcer()
    return _enforcer
