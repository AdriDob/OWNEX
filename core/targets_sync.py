"""Sync real in-scope bug bounty domains into the ``targets`` table.

The ``targets`` table historically accumulated program *handles* with
fabricated ``.com`` domains (``hackerone_agoda_public`` → ``agoda_public.com``),
which the DNS filter in ``_pick_scan_targets`` mostly skips — diluting scan
coverage. This module pulls the curated bounty-targets-data repository
(arkadiyt) for HackerOne, Bugcrowd, Intigriti and YesWeHack, extracts
bounty-eligible in-scope web assets, and upserts them as real ``Target`` rows.
Stale platform-prefixed rows that no longer appear in the fresh data are
deactivated.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("ownex.targets_sync")

_DATA_BASE = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data"
_SOURCES = {
    "hackerone": f"{_DATA_BASE}/hackerone_data.json",
    "bugcrowd": f"{_DATA_BASE}/bugcrowd_data.json",
    "intigriti": f"{_DATA_BASE}/intigriti_data.json",
    "yeswehack": f"{_DATA_BASE}/yeswehack_data.json",
}
_PLATFORM_PREFIXES = ("hackerone_", "bugcrowd_", "intigriti_", "yeswehack_")
_MAX_ASSETS_PER_PROGRAM = 50
_FETCH_TIMEOUT = 30

_slug_re = re.compile(r"[^a-z0-9]+")


def _slugify(text: str, max_len: int = 60) -> str:
    slug = _slug_re.sub("_", (text or "").lower()).strip("_")
    return slug[:max_len] or "unknown"


def _fetch_json(url: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(url, headers={"User-Agent": "OWNEX-targets-sync/1.0"})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data if isinstance(data, list) else []


def _extract_host(asset: str) -> str | None:
    """Normalize a scope asset string to a scannable hostname, or None."""
    asset = (asset or "").strip()
    if not asset:
        return None
    # Wildcard-only or multi-wildcard patterns can't be resolved directly.
    if asset.count("*") > 1:
        return None
    asset = asset.lstrip("*.")
    if "://" not in asset:
        asset = f"https://{asset}"
    try:
        host = urlparse(asset).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower().lstrip("*.")
    # Reject wildcards-in-host, regex-ish scope strings and bare IPs.
    if "*" in host or not re.fullmatch(r"[a-z0-9.-]+", host):
        return None
    if "." not in host or host.replace(".", "").isdigit() or host == "localhost":
        return None
    return host


def _programs(platform: str, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Yield normalized program dicts with bounty-eligible scope assets."""
    out: list[dict[str, Any]] = []
    for prog in data:
        targets = prog.get("targets") or {}
        scope = targets.get("in_scope") or []

        if platform == "hackerone":
            if not (prog.get("offers_bounties") and prog.get("submission_state") == "open"):
                continue
            handle = prog.get("handle") or _slugify(prog.get("name", ""))
            assets = [
                a.get("asset_identifier", "")
                for a in scope
                if a.get("eligible_for_bounty") and a.get("eligible_for_submission")
            ]
        elif platform == "bugcrowd":
            if not (prog.get("max_payout") or 0) > 0:
                continue
            handle = _slugify(prog.get("name", ""))
            assets = [a.get("uri") or a.get("target", "") for a in scope]
        elif platform == "intigriti":
            if prog.get("status") not in (None, "open", "public"):
                continue
            max_bounty = prog.get("max_bounty") or {}
            if not (max_bounty.get("value") or 0) > 0:
                continue
            handle = prog.get("handle") or _slugify(prog.get("name", ""))
            assets = [a.get("endpoint", "") for a in scope if a.get("endpoint") != "all"]
        else:  # yeswehack
            if prog.get("disabled") or not prog.get("public", True):
                continue
            if not (prog.get("max_bounty") or 0) > 0:
                continue
            handle = _slugify(prog.get("name", ""))
            assets = [a.get("target", "") for a in scope]

        hosts = []
        for asset in assets[:_MAX_ASSETS_PER_PROGRAM]:
            host = _extract_host(asset)
            if host and host not in hosts:
                hosts.append(host)
        if hosts:
            out.append({"handle": handle, "name": prog.get("name") or handle, "hosts": hosts})
    return out


def collect_bounty_targets() -> dict[tuple[str, str], dict[str, Any]]:
    """Fetch all sources and return {(name, domain): meta} of real targets."""
    fresh: dict[tuple[str, str], dict[str, Any]] = {}
    for platform, url in _SOURCES.items():
        try:
            data = _fetch_json(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("targets_sync: %s fetch failed: %s", platform, exc)
            continue
        programs = _programs(platform, data)
        for prog in programs:
            base_name = f"{platform}_{prog['handle']}"
            for idx, host in enumerate(prog["hosts"]):
                name = base_name if idx == 0 else f"{base_name}_{idx + 1}"
                fresh[(name, host)] = {
                    "name": name,
                    "domain": host,
                    "program": prog["name"],
                    "platform": platform,
                }
        logger.info("targets_sync: %s → %d programs", platform, len(programs))
    return fresh


def sync_bounty_targets() -> dict[str, Any]:
    """Upsert fresh bounty targets and deactivate stale platform rows."""
    from database import db
    from database.models import Target

    fresh = collect_bounty_targets()
    if not fresh:
        return {"status": "error", "message": "no targets collected from any source"}

    def _norm(domain: str | None) -> str:
        d = (domain or "").strip().lower()
        for scheme in ("https://", "http://"):
            if d.startswith(scheme):
                d = d[len(scheme) :]
        return d.rstrip("/")

    session = db.SessionLocal()
    try:
        existing = {(t.name, _norm(t.domain)): t for t in session.query(Target).all()}
        created = 0
        for name, domain in fresh:
            row = existing.get((name, domain))
            if row is None:
                session.add(Target(name=name, domain=domain, active=True))
                created += 1
            elif not row.active:
                row.active = True

        fresh_pairs = set(fresh.keys())
        deactivated = 0
        for (name, domain), row in existing.items():
            if (
                row.active
                and name
                and name.startswith(_PLATFORM_PREFIXES)
                and (name, domain) not in fresh_pairs
            ):
                row.active = False
                deactivated += 1

        session.commit()
    finally:
        session.close()

    logger.info(
        "targets_sync: %d fresh, %d created, %d stale deactivated",
        len(fresh),
        created,
        deactivated,
    )
    return {
        "status": "ok",
        "fresh_targets": len(fresh),
        "created": created,
        "deactivated": deactivated,
    }
