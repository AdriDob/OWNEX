"""Execution safety — gates for consequential external actions.

Two sides of the same rule (owner = final authority):
- BrowserAgent: navigation/reading/extraction are free; anything that sends
  data outward (applications, claims, form submits, uploads, payments)
  requires a one-time human approval token.
- CoderAgent: repo work is sandboxed to allowed roots, destructive shell
  commands are blocked, secrets never enter prompts/logs, and pushing
  branches / opening PRs / submitting work requires approval.

Approval tokens are HMAC-signed (action + target + expiry), single-use,
and single-process by design. They are a human gate, not cross-machine auth.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import time
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.safety")

APPROVAL_TTL_SECONDS = 600

_EPHEMERAL_KEY: bytes | None = None


class ActionClass(StrEnum):
    READ = "read"
    WRITE = "write"
    CONSEQUENTIAL = "consequential"


# BrowserAgent methods that send data outward. Everything else is READ/WRITE-local.
CONSEQUENTIAL_BROWSER_METHODS = frozenset(
    {
        "easy_apply_linkedin",
        "claim_algora_issue",
        "dataannotation_claim_task",
        "outlier_claim_task",
    }
)


def classify_browser_action(method_name: str) -> ActionClass:
    """Classify a BrowserAgent method by outward effect."""
    name = (method_name or "").strip().lower()
    if name in CONSEQUENTIAL_BROWSER_METHODS:
        return ActionClass.CONSEQUENTIAL
    if name.startswith(("goto", "get_", "wait_", "save_session", "load_session")):
        return ActionClass.READ
    return ActionClass.WRITE


def _approval_key() -> bytes:
    configured = os.environ.get("OWNEX_APPROVAL_KEY", "")
    if configured:
        return configured.encode()
    # Ephemeral: approvals only valid in this process (documented limitation).
    global _EPHEMERAL_KEY
    if _EPHEMERAL_KEY is None:
        _EPHEMERAL_KEY = secrets.token_bytes(32)
    return _EPHEMERAL_KEY


_USED_TOKENS: set[str] = set()


def issue_approval(action: str, target: str, ttl_seconds: int = APPROVAL_TTL_SECONDS) -> str:
    """Issue a one-time approval token for (action, target). Human-facing."""
    expires = int(time.time()) + max(1, ttl_seconds)
    nonce = secrets.token_hex(8)
    payload = f"{action}\n{target}\n{expires}\n{nonce}"
    sig = hmac.new(_approval_key(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{expires}:{nonce}:{sig}"


def consume_approval(token: str | None, action: str, target: str) -> bool:
    """Validate and burn a one-time approval token. False = deny."""
    if not token:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    expires_raw, nonce, sig = parts
    if not nonce:
        return False
    try:
        if int(expires_raw) < int(time.time()):
            return False
    except ValueError:
        return False
    payload = f"{action}\n{target}\n{expires_raw}\n{nonce}"
    expected = hmac.new(_approval_key(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return False
    if token in _USED_TOKENS:
        return False
    _USED_TOKENS.add(token)
    # Bound the set: drop entries for tokens long expired (best effort).
    if len(_USED_TOKENS) > 10000:
        _USED_TOKENS.clear()
    return True


def require_browser_approval(method_name: str, target: str, approval_token: str | None) -> tuple[bool, str]:
    """Gate for BrowserAgent consequential methods. Returns (ok, message)."""
    if classify_browser_action(method_name) != ActionClass.CONSEQUENTIAL:
        return True, ""
    action = f"browser:{method_name}"
    if consume_approval(approval_token, action, target):
        return True, ""
    return False, (
        f"Requires human approval: {method_name} on {target} sends data outward. "
        "Issue a token via issue_approval() after owner review."
    )


# Shell commands that must never run under automation, even inside a repo.
BLOCKED_COMMAND_PATTERNS: tuple[str, ...] = (
    r"\brm\s+-rf\s+/(?:\s|$)",
    r"\brm\s+-rf\s+~(?:\s|$|/)",
    r"\bmkfs\b",
    r"\bdd\s+.*\bof=",
    r":\(\)\s*\{",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"\bpoweroff\b",
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R\s+",
    r"\bcurl\b.*\|\s*(?:bash|sh)\b",
    r"\bwget\b.*\|\s*(?:bash|sh)\b",
    r"\bnc\s+-l\b",
    r"\bncat\s+-l\b",
    r">\s*/dev/sd",
)

_COMPILED_BLOCKED = [re.compile(p) for p in BLOCKED_COMMAND_PATTERNS]


def check_command(command: str, extra_blocked: list[str] | None = None) -> tuple[bool, str]:
    """Return (allowed, reason). Blocks destructive/suspicious shell commands."""
    cmd = command or ""
    for pattern in _COMPILED_BLOCKED:
        if pattern.search(cmd):
            return False, f"Blocked destructive command pattern: {pattern.pattern}"
    for extra in extra_blocked or []:
        if extra and extra in cmd:
            return False, f"Blocked by policy: {extra!r}"
    return True, ""


_SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?i)(api[_-]?key\s*[:=]\s*)(['\"]?)[A-Za-z0-9_\-./+]{8,}\2", r"\1[REDACTED]"),
    (r"(?i)(secret\s*[:=]\s*)(['\"]?)[A-Za-z0-9_\-./+]{8,}\2", r"\1[REDACTED]"),
    (r"(?i)(token\s*[:=]\s*)(['\"]?)[A-Za-z0-9_\-./+]{8,}\2", r"\1[REDACTED]"),
    (r"(?i)(password\s*[:=]\s*)(['\"]?)\S+\2", r"\1[REDACTED]"),
    (r"sk-(live|test)-[A-Za-z0-9]{8,}", "sk-[REDACTED]"),
    (r"ghp_[A-Za-z0-9]{8,}", "ghp_[REDACTED]"),
    (r"gho_[A-Za-z0-9]{8,}", "gho_[REDACTED]"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "-----BEGIN REDACTED PRIVATE KEY-----"),
    (r"xox[bap]-[A-Za-z0-9-]+", "xox-[REDACTED]"),
)

_COMPILED_SECRETS = [(re.compile(p), r) for p, r in _SECRET_PATTERNS]


def redact_secrets(text: str) -> str:
    """Redact credential-looking material before prompts/logs. Best effort."""
    if not text:
        return text
    out = text
    for pattern, replacement in _COMPILED_SECRETS:
        out = pattern.sub(replacement, out)
    return out


def is_path_allowed(path: str | Path, allowed_roots: Sequence[str | Path]) -> bool:
    """Containment check: path must resolve inside one of the allowed roots."""
    try:
        resolved = Path(path).expanduser().resolve()
    except Exception:
        return False
    for root in allowed_roots:
        try:
            resolved.relative_to(Path(root).expanduser().resolve())
            return True
        except Exception:
            continue
    return False


def approval_status() -> dict[str, Any]:
    """Introspection for health/debug (never exposes the key)."""
    return {
        "ephemeral_key": not bool(os.environ.get("OWNEX_APPROVAL_KEY")),
        "consumed_tokens": len(_USED_TOKENS),
        "ttl_seconds": APPROVAL_TTL_SECONDS,
        "consequential_browser_methods": sorted(CONSEQUENTIAL_BROWSER_METHODS),
        "blocked_command_patterns": len(BLOCKED_COMMAND_PATTERNS),
    }
