"""Live-source Connection Manager — credentials for opportunity fetchers.

Single canonical surface for connecting/disconnecting the credentials that
unlock gated live-opportunity fetchers. Secrets live only in
``~/.config/ownex/opportunity.env`` (mode 600) and process env — never in
responses, logs, or the repo.

Honesty contract:
- ``configured`` means the credential is present; it does NOT prove the
  platform accepts it.
- ``verified`` is only set by a real probe against the platform's auth
  endpoint. Probes exist only where the endpoint is known; everything else
  reports ``probe: none``.
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from cores.opportunity.live_pipeline import CREDENTIAL_GATED_FETCHERS, LIVE_FETCHERS, SECURITY_FETCHERS

ENV_FILE = Path("~/.config/ownex/opportunity.env").expanduser()
ENV_BACKUP = ENV_FILE.with_suffix(".env.bak")

# fetcher -> credential spec. ``env`` lists the env vars the fetcher/vault
# actually reads. ``required=False`` means the fetcher works without it
# (enrichment only). ``probe`` names a real auth check implemented below.
SOURCE_CREDENTIAL_SPECS: dict[str, dict[str, Any]] = {
    "github_bounties": {
        "env": ["GITHUB_TOKEN"],
        "required": False,
        "probe": "github_user",
        "where": "https://github.com/settings/tokens (public_repo scope is enough)",
    },
    "github_sponsors": {"env": ["GITHUB_TOKEN"], "required": False, "probe": "github_user"},
    "algora": {
        "env": ["ALGORA_API_KEY"],
        "required": False,
        "probe": "none",
        "where": "Algora dashboard API settings",
    },
    "freelancer": {
        "env": ["FREELANCER_API_KEY"],
        "required": True,
        "probe": "none",
        "where": "freelancer.com/settings/api (OAuth token)",
    },
    "issuehunt": {"env": ["ISSUEHUNT_API_KEY"], "required": False, "probe": "none"},
    "opire": {"env": ["OPIRE_API_KEY"], "required": False, "probe": "none"},
    "opencollective": {"env": ["OPENCOLLECTIVE_API_KEY"], "required": False, "probe": "none"},
    "superteam": {"env": ["SUPERTEAM_API_KEY"], "required": False, "probe": "none"},
    "onlydust": {"env": [], "required": False, "probe": "none"},
    "ethglobal": {"env": [], "required": False, "probe": "none"},
    "codeforai": {"env": [], "required": False, "probe": "none"},
    "hackerone": {
        "env": ["HACKERONE_API_USERNAME", "HACKERONE_API_TOKEN"],
        "required": False,
        "probe": "hackerone_me",
        "where": "hackerone.com settings > API token",
    },
    "bugcrowd": {"env": ["BUGCROWD_API_TOKEN"], "required": False, "probe": "none"},
    "intigriti": {"env": ["INTIGRITI_API_TOKEN"], "required": False, "probe": "none"},
    "yeswehack": {"env": ["YESWEHACK_API_TOKEN"], "required": False, "probe": "none"},
    "immunefi": {"env": ["IMMUNEFI_API_TOKEN"], "required": False, "probe": "none"},
    "synack": {"env": ["SYNACK_API_KEY"], "required": True, "probe": "none", "invite_only": True},
    "cantina": {"env": [], "required": False, "probe": "none"},
    "sherlock": {"env": [], "required": False, "probe": "none"},
    "code4rena": {"env": [], "required": False, "probe": "none"},
    "codehawks": {"env": [], "required": False, "probe": "none"},
}

ALLOWED_ENV_VARS = {var for spec in SOURCE_CREDENTIAL_SPECS.values() for var in spec["env"]}
_ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def _read_env_file() -> dict[str, str]:
    """Parse opportunity.env; process env wins on conflicts (pydantic parity)."""
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _ENV_LINE.match(line)
            if m:
                values[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    for var in ALLOWED_ENV_VARS:
        if var in os.environ and os.environ[var]:
            values[var] = os.environ[var]
    return values


def _write_env_file(values: dict[str, str]) -> None:
    """Rewrite opportunity.env atomically with 0600 perms, preserving other keys."""
    existing: dict[str, str] = {}
    other_lines: list[str] = []
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            m = _ENV_LINE.match(stripped)
            if m and m.group(1) in ALLOWED_ENV_VARS:
                existing[m.group(1)] = m.group(2).strip().strip('"').strip("'")
            else:
                other_lines.append(line)
    merged = {**existing, **values}
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = ENV_FILE.with_suffix(".env.tmp")
    body = "\n".join([*other_lines, *(f"{k}={v}" for k, v in sorted(merged.items()))]) + "\n"
    tmp.write_text(body, encoding="utf-8")
    tmp.chmod(0o600)
    shutil.move(str(tmp), str(ENV_FILE))


def _present(env_values: dict[str, str], var: str) -> bool:
    val = env_values.get(var, "")
    if not val:
        return False
    # Same guard the github fetcher uses: reject placeholder tokens.
    return not any(bad in val.lower() for bad in ("test", "your_", "placeholder", "xxx", "changeme"))


def connection_status() -> dict[str, Any]:
    """Per-fetcher connection state. Never returns secret values."""
    env_values = _read_env_file()
    known = set(LIVE_FETCHERS) | set(SECURITY_FETCHERS)
    sources: list[dict[str, Any]] = []
    for name in sorted(known | set(SOURCE_CREDENTIAL_SPECS)):
        spec = SOURCE_CREDENTIAL_SPECS.get(name, {"env": [], "required": False, "probe": "none"})
        env = spec["env"]
        if not env:
            state = "public"
        else:
            present = [v for v in env if _present(env_values, v)]
            if len(present) == len(env):
                state = "configured"
            elif present:
                state = "partial"
            else:
                state = "pending" if spec.get("required") else "optional"
        sources.append(
            {
                "source": name,
                "state": state,
                "required": bool(spec.get("required")),
                "invite_only": bool(spec.get("invite_only")),
                "env_vars": [{"name": v, "configured": _present(env_values, v)} for v in env],
                "probe": spec.get("probe", "none"),
                "verified": False,  # only a successful probe flips this
                "where": spec.get("where"),
                "note": CREDENTIAL_GATED_FETCHERS.get(name),
            }
        )
    return {
        "env_file": str(ENV_FILE),
        "env_file_exists": ENV_FILE.exists(),
        "sources": sources,
        "counts": {
            "total": len(sources),
            "public": sum(1 for s in sources if s["state"] == "public"),
            "configured": sum(1 for s in sources if s["state"] == "configured"),
            "partial": sum(1 for s in sources if s["state"] == "partial"),
            "pending": sum(1 for s in sources if s["state"] == "pending"),
            "optional": sum(1 for s in sources if s["state"] == "optional"),
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }


async def _probe_github_user(token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
    if r.status_code == 200:
        login = r.json().get("login")
        return {"verified": True, "detail": f"authenticated as {login}" if login else "authenticated"}
    if r.status_code == 401:
        return {"verified": False, "detail": "token rejected (401)"}
    return {"verified": False, "detail": f"unexpected status {r.status_code}"}


async def _probe_hackerone(username: str, token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://api.hackerone.com/v1/hackers/me",
            auth=(username, token),
        )
    if r.status_code == 200:
        return {"verified": True, "detail": "credentials accepted"}
    if r.status_code in (401, 403):
        return {"verified": False, "detail": f"credentials rejected ({r.status_code})"}
    return {"verified": False, "detail": f"unexpected status {r.status_code}"}


async def test_connection(source: str) -> dict[str, Any]:
    """Probe a source's credentials for real. Only implemented probes verify."""
    spec = SOURCE_CREDENTIAL_SPECS.get(source)
    if spec is None:
        return {"source": source, "error": "unknown source"}
    env_values = _read_env_file()
    probe = spec.get("probe", "none")
    result: dict[str, Any] = {
        "source": source,
        "probe": probe,
        "verified": False,
        "tested_at": datetime.now(UTC).isoformat(),
    }
    if probe == "github_user":
        token = env_values.get("GITHUB_TOKEN", "")
        if not _present(env_values, "GITHUB_TOKEN"):
            result["detail"] = "GITHUB_TOKEN not configured"
        else:
            result.update(await _probe_github_user(token))
    elif probe == "hackerone_me":
        user, token = env_values.get("HACKERONE_API_USERNAME", ""), env_values.get("HACKERONE_API_TOKEN", "")
        if not (_present(env_values, "HACKERONE_API_USERNAME") and _present(env_values, "HACKERONE_API_TOKEN")):
            result["detail"] = "HACKERONE_API_USERNAME + HACKERONE_API_TOKEN not fully configured"
        else:
            result.update(await _probe_hackerone(user, token))
    else:
        result["detail"] = "no auth probe implemented; presence only — not verified"
    return result


def set_credential(env_var: str, value: str) -> dict[str, Any]:
    """Store one allowlisted credential in opportunity.env (0600)."""
    if env_var not in ALLOWED_ENV_VARS:
        return {"error": f"{env_var} is not a managed credential", "allowed": sorted(ALLOWED_ENV_VARS)}
    if not value or not value.strip():
        return {"error": "empty value"}
    _write_env_file({env_var: value.strip()})
    return {"env_var": env_var, "stored": True, "env_file": str(ENV_FILE)}


def revoke_credential(env_var: str) -> dict[str, Any]:
    """Remove one allowlisted credential from opportunity.env (backup first)."""
    if env_var not in ALLOWED_ENV_VARS:
        return {"error": f"{env_var} is not a managed credential", "allowed": sorted(ALLOWED_ENV_VARS)}
    if ENV_FILE.exists():
        shutil.copy2(ENV_FILE, ENV_BACKUP)
    current = _read_env_file()
    if env_var not in current:
        return {"env_var": env_var, "revoked": False, "detail": "not present in env file or environment"}
    # Rebuild file without the var; process-env values can't be deleted here.
    if env_var in os.environ:
        return {
            "env_var": env_var,
            "revoked": False,
            "detail": "value comes from process environment; unset it there or restart without it",
        }
    lines = [line for line in ENV_FILE.read_text(encoding="utf-8").splitlines() if not (m := _ENV_LINE.match(line.strip())) or m.group(1) != env_var]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_FILE.chmod(0o600)
    return {"env_var": env_var, "revoked": True, "backup": str(ENV_BACKUP)}
