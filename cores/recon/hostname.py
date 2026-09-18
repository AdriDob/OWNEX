"""Hostname hygiene — fail-closed gates so scans never burn budget on garbage.

Two verified leaks (2026-09-18, evidencia DB real):
- 402/719 targets tienen dominios con `_` (ej. `agoda_public.com`, slug+"com"):
  DNS inválido, toda herramienta falla con "no address found", el scan jamás
  puede producir findings. Cuestan timeouts y cómputo.
- El parser convertía banners ASCII de las herramientas en "endpoints"
  (`host=example.com`, `score=0`): endpoints falsos contaminan risk scoring.

Todo puro y testeable. Ninguna función raisea por input raro: devuelve False/None.
"""

from __future__ import annotations

import re

_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_TLD_RE = re.compile(r"^[a-z]{2,}$")

# Hosts placeholder que el parser usa cuando la línea no trae host real.
PLACEHOLDER_HOSTS = frozenset({"", "example.com"})


def is_valid_hostname(value: object) -> bool:
    """True si `value` es un hostname DNS resoluble en teoría.

    Rechaza: vacíos, con `_`/espacios, labels vacíos o con `-` en bordes,
    TLD numérico o de 1 letra, >253 chars. No hace DNS (puro, sin red).
    """
    if not isinstance(value, str):
        return False
    host = value.strip().lower().rstrip(".")
    if not host or len(host) > 253 or "_" in host or " " in host:
        return False
    labels = host.split(".")
    if len(labels) < 2:
        return False
    if not _TLD_RE.match(labels[-1]):
        return False
    return all(bool(_LABEL_RE.match(label)) for label in labels)


def scannable_domain(name: object, domain: object) -> str | None:
    """Dominio efectivo para escanear (`domain or name`), o None si inválido.

    Espeja la regla de `api/scheduler._recon_target` (`target.domain or
    target.name`) para que scheduler, servicio y validadores decidan igual.
    Acepta `dominio:PUERTO` (corta el puerto antes de validar).
    """
    raw = domain or name or ""
    if not isinstance(raw, str):
        return None
    candidate = raw.strip().split(":")[0].strip()
    if not candidate:
        return None
    return candidate if is_valid_hostname(candidate) else None


def has_real_host(host: object) -> bool:
    """True si el host parseado es evidencia real, no placeholder del parser."""
    if not isinstance(host, str):
        return False
    return host.strip().lower() not in PLACEHOLDER_HOSTS
