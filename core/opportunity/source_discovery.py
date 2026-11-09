"""Safe discovery and lifecycle tracking for external work-source metadata.

Discovered protocol documents are untrusted input. This module only reads and
describes them; it never executes declared tools, operations, or generated code.
"""

from __future__ import annotations

import builtins
import hashlib
import ipaddress
import json
import logging
import os
import re
import socket
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger("ownex.opportunity.source_discovery")

MAX_DOCUMENT_BYTES = 1_000_000
MAX_OPENAPI_PATHS = 100
MAX_PROFILE_ENDPOINTS = 100
HTTP_TIMEOUT_SECONDS = 8.0
USER_AGENT = "OWNEX-SourceDiscovery/1.0 (metadata-only; contact: owner-configured)"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_SEARCH_CACHE_TTL_SECONDS = 6 * 60 * 60
_GITHUB_RETRYABLE_STATUS = {403, 429, 500, 502, 503}
_BOUNTY_CONTEXT_TERMS = ("bounty", "reward", "paid", "funding", "funded", "prize", "payout")

# Argentina compatibility signals - keywords that indicate a source supports
# Argentina payout methods (USDC, Payoneer, AirTM, etc.)
_ARGENTINA_PAYOUT_KEYWORDS = (
    "usdc",
    "usdt",
    "airtm",
    "payoneer",
    "btc",
    "eth",
    "argentina",
    "ar",
    "argentino",
    "usd",
    "crypto",
    "stablecoin",
    "latam",
    "latin",
    "dolar",
    "dolares",
)


class SourceLifecycle(StrEnum):
    DISCOVERED = "DISCOVERED"
    PROBED = "PROBED"
    VERIFIED = "VERIFIED"
    ACTIVE = "ACTIVE"
    DECAY = "DECAY"
    DEACTIVATED = "DEACTIVATED"


@dataclass(slots=True)
class SourceProfile:
    source_url: str
    adapter_type: str = "unknown"
    document_url: str = ""
    title: str = ""
    version: str = ""
    endpoints: list[dict[str, str]] = field(default_factory=list)
    auth_methods: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    evidence: list[dict[str, str]] = field(default_factory=list)
    probed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceCandidate:
    id: str
    name: str
    source_url: str
    discovered_by: str
    record_type: str = "source"
    lifecycle: SourceLifecycle = SourceLifecycle.DISCOVERED
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    profile: dict[str, Any] | None = None
    verification_evidence: list[str] = field(default_factory=list)
    activated_at: str | None = None
    last_payout_at: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["lifecycle"] = self.lifecycle.value
        return value


def _state_path() -> Path:
    configured = os.getenv("OWNEX_DATA_DIR") or os.getenv("CATEYE_DATA_DIR")
    root = Path(configured).expanduser() if configured else Path.home() / ".orion"
    return root / "source_discovery" / "candidates.json"


def _validate_public_url(url: str) -> str:
    """Reject non-HTTPS, local, private, link-local, and non-public targets."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Source URL must be an absolute HTTPS URL without credentials")
    if parsed.port not in (None, 443):
        raise ValueError("Source URL must use the default HTTPS port")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local source URLs are not allowed")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise ValueError("Source host could not be resolved") from exc
        if not addresses or any(not address.is_global for address in addresses):
            raise ValueError("Source host must resolve only to public IP addresses") from None
    else:
        if not literal.is_global:
            raise ValueError("Source URL must use a public IP address")
    return url.rstrip("/")


def _decode_json(response: httpx.Response) -> dict[str, Any] | None:
    try:
        value = response.json()
    except (ValueError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


class UniversalSourceAdapter:
    """Probe public protocol metadata and describe safe, non-executable clients."""

    DOCUMENTS = (
        ("openapi", "/openapi.json"),
        ("skill_md", "/skill.md"),
        ("ai_catalog", "/ai-catalog.json"),
        ("a2a", "/.well-known/agent.json"),
        ("llms_txt", "/llms.txt"),
    )

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def probe(self, base_url: str) -> SourceProfile:
        base = _validate_public_url(base_url)
        evidence: list[dict[str, str]] = []
        with httpx.Client(
            timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
            follow_redirects=False,
            trust_env=False,
            transport=self._transport,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/markdown, text/plain;q=0.9"},
        ) as client:
            for kind, path in self.DOCUMENTS:
                url = f"{base}{path}"
                try:
                    with client.stream("GET", url) as streamed:
                        oversized = False
                        response_body = bytearray()
                        if streamed.status_code == 200:
                            for chunk in streamed.iter_bytes():
                                response_body.extend(chunk)
                                if len(response_body) > MAX_DOCUMENT_BYTES:
                                    oversized = True
                                    break
                        response = httpx.Response(
                            status_code=streamed.status_code,
                            headers=streamed.headers,
                            content=bytes(response_body),
                            request=streamed.request,
                        )
                except httpx.HTTPError as exc:
                    evidence.append({"url": url, "result": f"request_error:{type(exc).__name__}"})
                    continue
                if response.status_code != 200:
                    evidence.append({"url": url, "result": f"http_{response.status_code}"})
                    continue
                if oversized or len(response.content) > MAX_DOCUMENT_BYTES:
                    evidence.append({"url": url, "result": "document_too_large"})
                    continue
                profile = self._parse(kind, base, url, response)
                if profile is not None:
                    profile.evidence = evidence + [{"url": url, "result": "parsed"}]
                    profile.probed_at = datetime.now(UTC).isoformat()
                    return profile
                evidence.append({"url": url, "result": "malformed_or_unsupported"})

        return SourceProfile(
            source_url=base,
            adapter_type="unknown",
            evidence=evidence,
            probed_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def _parse(kind: str, base: str, document_url: str, response: httpx.Response) -> SourceProfile | None:
        if kind == "openapi":
            spec = _decode_json(response)
            if spec is None or not str(spec.get("openapi", "")).startswith("3."):
                return None
            endpoints = []
            paths = spec.get("paths", {})
            if isinstance(paths, dict):
                for route, operations in list(paths.items())[:MAX_OPENAPI_PATHS]:
                    if not isinstance(operations, dict):
                        continue
                    for method in operations:
                        if method.lower() in {"get", "post", "put", "patch", "delete"}:
                            endpoints.append({"method": method.upper(), "path": str(route)[:300]})
                            if len(endpoints) >= MAX_PROFILE_ENDPOINTS:
                                break
                    if len(endpoints) >= MAX_PROFILE_ENDPOINTS:
                        break
            security = spec.get("components", {}).get("securitySchemes", {}) if isinstance(spec.get("components"), dict) else {}
            auth = sorted(str(item)[:100] for item in security) if isinstance(security, dict) else []
            info_value = spec.get("info")
            info = info_value if isinstance(info_value, dict) else {}
            return SourceProfile(base, kind, document_url, str(info.get("title", ""))[:200], str(info.get("version", ""))[:80], endpoints, auth)

        if kind in {"ai_catalog", "a2a"}:
            manifest = _decode_json(response)
            if not manifest:
                return None
            raw_tools = manifest.get("tools", manifest.get("capabilities", []))
            title = manifest.get("name", manifest.get("title", ""))
            if kind == "ai_catalog" and not (title or "tools" in manifest or "capabilities" in manifest):
                return None
            if kind == "a2a" and not (title or "capabilities" in manifest or "skills" in manifest):
                return None
            names = []
            if isinstance(raw_tools, list):
                names = [str(item.get("name", item.get("id", "")))[:120] if isinstance(item, dict) else str(item)[:120] for item in raw_tools[:100]]
            elif isinstance(raw_tools, dict):
                names = [str(key)[:120] for key in list(raw_tools)[:100]]
            if kind == "a2a" and isinstance(manifest.get("skills"), list):
                names.extend(str(item.get("id", item.get("name", "")))[:120] for item in manifest["skills"][:100] if isinstance(item, dict))
            auth = manifest.get("authentication", manifest.get("auth", {}))
            auth_names = sorted(str(key)[:100] for key in auth) if isinstance(auth, dict) else []
            return SourceProfile(
                base,
                kind,
                document_url,
                str(title)[:200],
                str(manifest.get("version", ""))[:80],
                auth_methods=auth_names,
                capabilities=names,
            )

        text = response.text[:MAX_DOCUMENT_BYTES]
        if kind == "skill_md":
            if not text.strip() or "\x00" in text:
                return None
            return SourceProfile(base, kind, document_url, endpoints=UniversalSourceAdapter._markdown_endpoints(text))
        if kind == "llms_txt":
            if not text.lstrip().startswith("#"):
                return None
            links = []
            for line in text.splitlines()[:500]:
                if "](" in line and "[" in line:
                    _label = line.split("](", 1)[0].rsplit("[", 1)[-1][:120]
                    target = line.split("](", 1)[1].split(")", 1)[0][:300]
                    if target.startswith(("https://", "/")):
                        links.append({"method": "LINK", "path": target})
                    if len(links) >= MAX_PROFILE_ENDPOINTS:
                        break
            return SourceProfile(base, kind, document_url, endpoints=links)
        return None

    @staticmethod
    def _markdown_endpoints(text: str) -> list[dict[str, str]]:
        import re

        result = []
        pattern = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[^\s`]{1,300})", re.IGNORECASE)
        for method, path in pattern.findall(text[:MAX_DOCUMENT_BYTES]):
            result.append({"method": method.upper(), "path": path})
            if len(result) >= MAX_PROFILE_ENDPOINTS:
                break
        return result

    def generate_adapter(self, profile: SourceProfile) -> dict[str, Any]:
        """Return a declarative descriptor; never generate or execute code."""
        if profile.adapter_type == "unknown":
            raise ValueError("Unsupported source protocol")
        return {
            "kind": "metadata_only",
            "protocol": profile.adapter_type,
            "source_url": profile.source_url,
            "document_url": profile.document_url,
            "endpoints": profile.endpoints,
            "capabilities": profile.capabilities,
            "executable": False,
            "task_schema_verified": False,
        }

    @staticmethod
    def normalize(raw: dict[str, Any], *, source_id: str, profile: SourceProfile) -> dict[str, Any]:
        """Normalize only a small explicit task envelope; do not infer money or eligibility."""
        title = raw.get("title")
        description = raw.get("description")
        task_url = raw.get("url")
        if not isinstance(title, str) or not title.strip() or not isinstance(description, str):
            raise ValueError("Task must include a non-empty title and description")
        if task_url is not None and (not isinstance(task_url, str) or not task_url.startswith("https://")):
            raise ValueError("Task URL must be HTTPS")
        reward = raw.get("reward")
        reward_reported = reward if isinstance(reward, (str, int, float, dict)) else None
        return {
            "id": f"{source_id}:{str(raw.get('id', ''))[:200]}",
            "source": source_id,
            "title": title.strip()[:500],
            "description": description[:10000],
            "url": task_url,
            "reward": None,
            "reward_reported": reward_reported,
            "reward_status": "REPORTED" if reward_reported is not None else "UNKNOWN",
            "eligibility": "PENDING",
            "source_protocol": profile.adapter_type,
            "evidence": profile.evidence,
        }


class SourceDiscoveryRegistry:
    """Small atomic JSON registry for discovered sources and explicit approvals."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _state_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._candidates: dict[str, SourceCandidate] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for row in raw.get("candidates", []):
                candidate = SourceCandidate(**{**row, "lifecycle": SourceLifecycle(row.get("lifecycle", "DISCOVERED"))})
                self._candidates[candidate.id] = candidate
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Source discovery state could not be loaded: %s", exc)

    def _save(self) -> None:
        payload = {"schema_version": 1, "candidates": [item.to_dict() for item in self._candidates.values()]}
        fd, temporary = tempfile.mkstemp(prefix="candidates-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def add(
        self,
        name: str,
        url: str,
        discovered_by: str,
        *,
        record_type: str = "source",
        profile: dict[str, Any] | None = None,
    ) -> SourceCandidate:
        source_url = _validate_public_url(url)
        source_id = hashlib.sha256(source_url.encode()).hexdigest()[:24]
        existing = self._candidates.get(source_id)
        if existing:
            if record_type == "opportunity" and existing.record_type != "opportunity":
                existing.record_type = "opportunity"
                existing.discovered_by = discovered_by[:100]
                if profile:
                    existing.profile = profile
                self._save()
            return existing
        item = SourceCandidate(
            source_id,
            name[:200],
            source_url,
            discovered_by[:100],
            record_type=record_type,
            profile=profile,
        )
        self._candidates[source_id] = item
        self._save()
        return item

    def get(self, source_id: str) -> SourceCandidate | None:
        return self._candidates.get(source_id)

    def list(self, *, limit: int = 100) -> builtins.list[SourceCandidate]:
        return list(self._candidates.values())[-max(1, min(limit, 500)) :][::-1]

    def known_urls(self) -> set[str]:
        return {item.source_url for item in self._candidates.values()}

    def set_profile(self, source_id: str, profile: SourceProfile) -> SourceCandidate:
        item = self._require(source_id)
        item.profile = profile.to_dict()
        item.lifecycle = SourceLifecycle.PROBED if profile.adapter_type != "unknown" else SourceLifecycle.DISCOVERED
        item.last_error = None if profile.adapter_type != "unknown" else "No supported protocol metadata found"
        self._save()
        return item

    def mark_verified(self, source_id: str, checks: dict[str, str]) -> SourceCandidate:
        item = self._require(source_id)
        if not item.profile or item.lifecycle != SourceLifecycle.PROBED:
            raise ValueError("A source must have a successful protocol probe before verification")
        required_checks = {"honeypot_pass", "funding_verified", "eligibility_verified"}
        if set(checks) != required_checks or any(not value.strip() for value in checks.values()):
            raise ValueError("Verification requires evidence for honeypot, funding, and eligibility checks")
        item.verification_evidence = [f"{key}:{value[:450]}" for key, value in sorted(checks.items())]
        item.lifecycle = SourceLifecycle.VERIFIED
        self._save()
        return item

    def activate(self, source_id: str, *, approval_note: str) -> SourceCandidate:
        item = self._require(source_id)
        if item.lifecycle != SourceLifecycle.VERIFIED or not item.verification_evidence:
            raise ValueError("Only verified sources can be activated")
        if not approval_note.strip():
            raise ValueError("Human approval note is required")
        item.lifecycle = SourceLifecycle.ACTIVE
        item.activated_at = datetime.now(UTC).isoformat()
        item.verification_evidence.append(f"human_approval:{approval_note[:400]}")
        self._save()
        return item

    def refresh_lifecycle(self, *, now: datetime | None = None) -> builtins.list[SourceCandidate]:
        current = now or datetime.now(UTC)
        changed = []
        for item in self._candidates.values():
            if item.lifecycle not in {SourceLifecycle.ACTIVE, SourceLifecycle.DECAY}:
                continue
            anchor = item.last_payout_at or item.activated_at
            if not anchor:
                continue
            try:
                last_activity = datetime.fromisoformat(anchor)
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=UTC)
            except ValueError:
                continue
            age = current - last_activity
            new_state: SourceLifecycle = item.lifecycle
            if age >= timedelta(days=30):
                new_state = SourceLifecycle.DEACTIVATED
            elif age >= timedelta(days=7):
                new_state = SourceLifecycle.DECAY
            if new_state != item.lifecycle:
                item.lifecycle = new_state
                changed.append(item)
        if changed:
            self._save()
        return changed

    def record_confirmed_payout(self, source_id: str, *, evidence_reference: str) -> SourceCandidate:
        item = self._require(source_id)
        if item.lifecycle not in {SourceLifecycle.ACTIVE, SourceLifecycle.DECAY, SourceLifecycle.DEACTIVATED}:
            raise ValueError("A payout can be attached only to an activated source")
        if not evidence_reference.strip() or not evidence_reference.startswith(("https://", "tx:")):
            raise ValueError("Payout confirmation requires an HTTPS evidence URL or transaction reference")
        item.last_payout_at = datetime.now(UTC).isoformat()
        item.verification_evidence.append(f"confirmed_payout:{evidence_reference[:400]}")
        if item.lifecycle in {SourceLifecycle.DECAY, SourceLifecycle.DEACTIVATED}:
            item.lifecycle = SourceLifecycle.ACTIVE
        self._save()
        return item

    def _require(self, source_id: str) -> SourceCandidate:
        item = self.get(source_id)
        if item is None:
            raise KeyError("Source candidate not found")
        return item


def _github_token(github_token: str | None = None) -> str:
    return github_token if github_token is not None else (os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or "")


def _github_search_interval(github_token: str | None = None) -> float:
    token = _github_token(github_token)
    default = "2.1" if token else "6.5"
    try:
        return max(0.0, float(os.getenv("GITHUB_SEARCH_MIN_INTERVAL", default)))
    except ValueError:
        return 2.1 if token else 6.5


def _github_headers(github_token: str | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = _github_token(github_token)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _is_argentina_compatible(repo: dict[str, Any]) -> bool:
    """Check if a GitHub repository is Argentina-compatible based on its description and topics.

    A repository is considered Argentina-compatible if its description or topics contain
    keywords indicating support for Argentina payout methods (USDC, Payoneer, AirTM, crypto, etc.).
    This helps filter opportunities that can pay users in Argentina.
    """
    description = repo.get("description", "") or ""
    topics = repo.get("topic", []) if isinstance(repo.get("topic"), list) else []
    if isinstance(topics, str):
        topics = [topics]
    # Normalize to lowercase for matching
    desc_lower = description.lower()
    # Check description for Argentina payout keywords
    for keyword in _ARGENTINA_PAYOUT_KEYWORDS:
        if keyword in desc_lower:
            return True
    # Check topics for Argentina signals
    for topic in topics:
        topic_lower = str(topic).lower() if isinstance(topic, str) else ""
        if topic_lower in _ARGENTINA_PAYOUT_KEYWORDS:
            return True
        # Also check if topic contains any keyword
        for keyword in _ARGENTINA_PAYOUT_KEYWORDS:
            if keyword in topic_lower:
                return True
    return False


def _search_cache_path(registry: SourceDiscoveryRegistry) -> Path:
    return registry.path.parent / "github_search_cache.json"


def _load_search_cache(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _save_search_cache(path: Path, cache: dict[str, Any]) -> None:
    fd, temporary = tempfile.mkstemp(prefix="github-search-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(cache, stream, indent=2, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _cache_key(params: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()


def _fresh_entry(entry: Any, ttl_seconds: float) -> bool:
    if not isinstance(entry, dict) or ttl_seconds <= 0:
        return False
    try:
        fetched = datetime.fromisoformat(str(entry.get("fetched_at", "")))
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=UTC)
    return (datetime.now(UTC) - fetched).total_seconds() < ttl_seconds


def _github_search_items(
    client: httpx.Client,
    endpoint: str,
    params: dict[str, Any],
    headers: dict[str, str],
    *,
    min_interval_seconds: float,
    cache_ttl_seconds: float,
    cache: dict[str, Any],
    state: dict[str, Any],
) -> tuple[list[Any] | None, str | None]:
    key = _cache_key(params)
    entry = cache.get(key)
    if _fresh_entry(entry, cache_ttl_seconds):
        state["cache_hits"] += 1
        items = entry.get("items") if isinstance(entry, dict) else None
        return (items if isinstance(items, list) else []), None

    if min_interval_seconds > 0 and state.get("last_request") is not None:
        elapsed = time.monotonic() - float(state["last_request"])
        if elapsed < min_interval_seconds:
            time.sleep(min_interval_seconds - elapsed)

    attempts = 0
    while True:
        state["last_request"] = time.monotonic()
        state["http_requests"] += 1
        try:
            response = client.get(f"{GITHUB_API_BASE}{endpoint}", params=params, headers=headers)
        except httpx.HTTPError as exc:
            return None, f"github_search_{type(exc).__name__}"
        if response.status_code in _GITHUB_RETRYABLE_STATUS and attempts < 1:
            attempts += 1
            retry_after = response.headers.get("retry-after", "")
            try:
                delay = float(retry_after) if retry_after else 5.0
            except ValueError:
                delay = 5.0
            time.sleep(max(0.0, min(delay, 30.0)))
            continue
        if response.status_code != 200:
            return None, f"github_search_http_{response.status_code}"
        if len(response.content) > MAX_DOCUMENT_BYTES:
            return None, "github_search_response_too_large"
        payload = _decode_json(response)
        if payload is None:
            return None, "github_search_malformed"
        items = payload.get("items")
        if not isinstance(items, list):
            return None, "github_search_malformed"
        cache[key] = {"fetched_at": datetime.now(UTC).isoformat(), "items": items}
        state["dirty"] = True
        return items, None


def discover_github_repositories(
    *,
    registry: SourceDiscoveryRegistry | None = None,
    client: httpx.Client | None = None,
    github_token: str | None = None,
    min_interval_seconds: float = 0.0,
    cache_ttl_seconds: float = GITHUB_SEARCH_CACHE_TTL_SECONDS,
    max_pages: int = 1,
) -> dict[str, Any]:
    """Fetch bounded GitHub repository candidates.

    Searches across multiple dimensions:
    - Topics (bounty, payment, frameworks, languages)
    - Programming languages with minimum stars
    - Recent activity and popularity
    - Specialized platforms (Algora, Opire, IssueHunt, OnlyDust)
    Never auto-probes or activates them.
    """
    registry = registry or SourceDiscoveryRegistry()
    own_client = client is None
    headers = _github_headers(github_token)
    http = client or httpx.Client(
        timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
        follow_redirects=False,
        trust_env=False,
        headers=headers,
    )
    today = datetime.now(UTC).date()

    # Expanded queries across multiple dimensions
    queries = (
        # Original bounty/payment topics
        f"topic:ai-agent-bounty created:<={today - timedelta(days=30)} stars:>10",
        f"topic:x402 created:<={today - timedelta(days=60)}",
        f"topic:agent-payment created:<={today - timedelta(days=60)}",
        # Data annotation & AI training topics (alignerr, codeforai.tech, datannotation)
        f"topic:data-annotation created:<={today - timedelta(days=90)} stars:>3",
        f"topic:ai-coding created:<={today - timedelta(days=90)} stars:>3",
        f"topic:ai-training created:<={today - timedelta(days=90)} stars:>3",
        # Languages with stars
        f"language:python created:<={today - timedelta(days=90)} stars:>5",
        f"language:javascript created:<={today - timedelta(days=90)} stars:>5",
        f"language:typescript created:<={today - timedelta(days=90)} stars:>5",
        f"language:go created:<={today - timedelta(days=90)} stars:>5",
        f"language:rust created:<={today - timedelta(days=90)} stars:>5",
        f"language:java created:<={today - timedelta(days=90)} stars:>5",
        f"language:csharp created:<={today - timedelta(days=90)} stars:>5",
        # Framework-specific
        f"topic:fastapi created:<={today - timedelta(days=90)} stars:>3",
        f"topic:spring created:<={today - timedelta(days=90)} stars:>3",
        f"topic:react created:<={today - timedelta(days=90)} stars:>3",
        f"topic:angular created:<={today - timedelta(days=90)} stars:>3",
        # Specialized platforms
        f"topic:algora created:<={today - timedelta(days=120)}",
        f"topic:opire created:<={today - timedelta(days=120)}",
        f"topic:issuehunt created:<={today - timedelta(days=120)}",
        f"topic:onlydust created:<={today - timedelta(days=120)}",
        # Bounty platforms
        f"topic:bugcrowd created:<={today - timedelta(days=120)} stars:>3",
        f"topic:hackerone created:<={today - timedelta(days=120)} stars:>3",
        f"topic:intigriti created:<={today - timedelta(days=120)} stars:>3",
        # General open source and freelance
        f"topic:open-source created:<={today - timedelta(days=90)} stars:>10",
        f"topic:freelance created:<={today - timedelta(days=90)} stars:>5",
        f"topic:mcp-server created:<={today - timedelta(days=60)} stars:>10",
        # Recent activity
        f"created:<={today - timedelta(days=30)} stars:>15",
        "updated:>2024-01-01 stars:>20",
    )
    cache_path = _search_cache_path(registry)
    cache = _load_search_cache(cache_path)
    state: dict[str, Any] = {"last_request": None, "http_requests": 0, "cache_hits": 0, "dirty": False}
    discovered = 0
    errors: list[str] = []
    known_urls = registry.known_urls()
    try:
        for query in queries:
            for page in range(1, max(1, max_pages) + 1):
                params = {"q": query, "sort": "updated", "per_page": 30, "page": page}
                items, error = _github_search_items(
                    http,
                    "/search/repositories",
                    params,
                    headers,
                    min_interval_seconds=min_interval_seconds,
                    cache_ttl_seconds=cache_ttl_seconds,
                    cache=cache,
                    state=state,
                )
                if error:
                    errors.append(error)
                    break
                for repo in items or []:
                    if not isinstance(repo, dict) or repo.get("archived") or repo.get("fork"):
                        continue
                    html_url = repo.get("html_url")
                    full_name = repo.get("full_name")
                    if not isinstance(html_url, str) or not isinstance(full_name, str) or not html_url.startswith("https://github.com/"):
                        continue
                    # Filter: only keep Argentina-compatible repositories
                    if not _is_argentina_compatible(repo):
                        continue
                    if html_url not in known_urls:
                        registry.add(full_name, html_url, "github_topic_search")
                        discovered += 1
                        known_urls.add(html_url)
    finally:
        if state["dirty"]:
            _save_search_cache(cache_path, cache)
        if own_client:
            http.close()
    registry.refresh_lifecycle()
    return {
        "source": "github_topic_search",
        "new_candidates": discovered,
        "errors": errors,
        "activation_requires_human": True,
        "http_requests": state["http_requests"],
        "cache_hits": state["cache_hits"],
    }


def discover_github_bounty_issues(
    *,
    registry: SourceDiscoveryRegistry | None = None,
    client: httpx.Client | None = None,
    github_token: str | None = None,
    min_interval_seconds: float = 0.0,
    cache_ttl_seconds: float = GITHUB_SEARCH_CACHE_TTL_SECONDS,
    max_pages: int = 1,
) -> dict[str, Any]:
    """Discover concrete GitHub issues that look reward-backed.

    These are opportunity candidates (record_type="opportunity"), not sources.
    Reward remains reported/unknown until independently verified.
    """
    registry = registry or SourceDiscoveryRegistry()
    own_client = client is None
    headers = _github_headers(github_token)
    http = client or httpx.Client(
        timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
        follow_redirects=False,
        trust_env=False,
        headers=headers,
    )
    queries = (
        "label:bounty is:issue is:open",
        "label:reward is:issue is:open",
        "label:USD is:issue is:open",
        "label:USDC is:issue is:open",
        "bounty in:title is:issue is:open",
    )
    cache_path = _search_cache_path(registry)
    cache = _load_search_cache(cache_path)
    state: dict[str, Any] = {"last_request": None, "http_requests": 0, "cache_hits": 0, "dirty": False}
    discovered = 0
    rewarded = 0
    errors: list[str] = []
    known_urls = registry.known_urls()
    try:
        for query in queries:
            for page in range(1, max(1, max_pages) + 1):
                params = {"q": query, "sort": "updated", "order": "desc", "per_page": 30, "page": page}
                items, error = _github_search_items(
                    http,
                    "/search/issues",
                    params,
                    headers,
                    min_interval_seconds=min_interval_seconds,
                    cache_ttl_seconds=cache_ttl_seconds,
                    cache=cache,
                    state=state,
                )
                if error:
                    errors.append(error)
                    break
                for issue in items or []:
                    if not isinstance(issue, dict) or "pull_request" in issue:
                        continue
                    html_url = issue.get("html_url")
                    title = issue.get("title")
                    if not isinstance(html_url, str) or not isinstance(title, str):
                        continue
                    if not html_url.startswith("https://github.com/") or "/issues/" not in html_url:
                        continue
                    reward, reward_currency = _extract_github_bounty_reward_details(issue)
                    profile = {
                        "endpoints": [],
                        "capabilities": ["issue"],
                        "auth_methods": [],
                        "evidence": [{"url": html_url, "type": "github_issue"}],
                        "reward_reported": reward,
                        "reward_currency": reward_currency,
                        "reward_status": "REPORTED" if reward is not None else "UNKNOWN",
                        "record_type": "opportunity",
                    }
                    if html_url not in known_urls:
                        registry.add(title[:200], html_url, "github_issue_search", record_type="opportunity", profile=profile)
                        discovered += 1
                        known_urls.add(html_url)
                        if reward is not None:
                            rewarded += 1
    finally:
        if state["dirty"]:
            _save_search_cache(cache_path, cache)
        if own_client:
            http.close()
    registry.refresh_lifecycle()
    return {
        "source": "github_issue_search",
        "new_opportunities": discovered,
        "reward_reported": rewarded,
        "errors": errors,
        "http_requests": state["http_requests"],
        "cache_hits": state["cache_hits"],
        "reward_verification_required": True,
    }


def run_daily_meta_discovery() -> dict[str, Any]:
    """Scheduler entry point; GitHub is currently the only enabled discovery feed."""
    try:
        registry = SourceDiscoveryRegistry()
        token = _github_token()
        interval = _github_search_interval(token)
        repos = discover_github_repositories(registry=registry, github_token=token, min_interval_seconds=interval)
        issues = discover_github_bounty_issues(registry=registry, github_token=token, min_interval_seconds=interval)
        return {"repositories": repos, "issues": issues, "activation_requires_human": True}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Daily meta-discovery failed: %s", exc)
        return {"status": "error", "error": type(exc).__name__}


# === Bountic-inspired: GitHub Bounty Issue Detection ===


def fetch_github_bounties(
    repo_owner: str,
    repo_name: str,
    github_token: str | None = None,
    limit: int = 50,
) -> list[SourceCandidate]:
    """Fetch GitHub Issues with 'bounty' label - inspired by Bountic.

    Uses the GitHub API to find issues labeled as bounties in a repository.
    Returns SourceCandidate objects ready for integration into the Work Bank.

    Rules (aligned with OWNEX policy):
    - No KYC / no stake required to discover
    - Only open issues with 'bounty' label
    - Reward extraction from labels or issue body
    - ID format: github_{owner}_{repo}_{issue_number}
    """

    headers = {"Accept": "application/vnd.github+json"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    bounties: list[SourceCandidate] = []
    page = 1
    per_page = min(limit, 100)

    while len(bounties) < limit:
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
        params = {
            "labels": "bounty",  # Filter by bounty label
            "state": "open",
            "per_page": per_page,
            "page": page,
        }

        import httpx

        try:
            resp = httpx.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                logger.warning("GitHub API error: %s %s", resp.status_code, resp.text[:200])
                break

            issues = resp.json()
            if not issues:
                break

            for issue in issues:
                reward, reward_currency = _extract_github_bounty_reward_details(issue)
                # Map GitHub issue to SourceCandidate
                candidate = SourceCandidate(
                    id=f"github_{repo_owner}_{repo_name}_{issue['number']}",
                    name=issue.get("title", "GitHub Bounty Issue")[:200],
                    source_url=issue.get("html_url", ""),
                    discovered_by="github_api",
                    record_type="opportunity",
                    # Extract reward from issue body or labels
                    profile={
                        "endpoints": [{"method": "GET", "path": issue.get("body", "")[:200]}] if issue.get("body") else [],
                        "capabilities": ["bug-reporting"],
                        "auth_methods": [],
                        "evidence": [{"url": issue.get("html_url", ""), "type": "github_issue"}],
                        "reward_reported": reward,
                        "reward_currency": reward_currency,
                        "reward_status": "UNKNOWN" if reward is None else "REPORTED",
                    },
                )
                candidate.lifecycle = SourceLifecycle.DISCOVERED
                bounties.append(candidate)

                if len(bounties) >= limit:
                    break

        except Exception as exc:
            logger.error("Error fetching GitHub bounties: %s", exc)
            break

        page += 1

    return bounties


_REWARD_AMOUNT_RE = re.compile(
    r"\$\s*(?P<usd_amount>\d+(?:\.\d{1,2})?)"
    r"|(?P<amount_before>\d+(?:\.\d{1,2})?)[-\s]*(?P<currency_after>USDC|USDT|USD|EUR|GBP)\b"
    r"|\b(?P<currency_before>USDC|USDT|USD|EUR|GBP)[-\s]*(?P<amount_after>\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)


def _reward_match(match: re.Match[str]) -> tuple[float, str] | None:
    if match.group("usd_amount") is not None:
        return float(match.group("usd_amount")), "USD"
    if match.group("amount_before") is not None:
        return float(match.group("amount_before")), str(match.group("currency_after")).upper()
    if match.group("amount_after") is not None:
        return float(match.group("amount_after")), str(match.group("currency_before")).upper()
    return None


def _reward_context_near(text: str, start: int, end: int, title: str) -> bool:
    window = text[max(0, start - 160) : min(len(text), end + 160)].lower()
    title_lower = title.lower()
    return any(term in window or term in title_lower for term in _BOUNTY_CONTEXT_TERMS)


def _extract_github_bounty_reward_details(issue: dict) -> tuple[float | None, str | None]:
    """Extract a reported reward amount/currency from labels, body, or milestone.

    Body amounts only count when bounty context appears nearby; a random "$"
    mention is not treated as a reward. The result is still only reported
    evidence — never verified payment.
    """
    labels = issue.get("labels", [])
    if isinstance(labels, list):
        for label in labels:
            name = label.get("name", "") if isinstance(label, dict) else str(label)
            match = _REWARD_AMOUNT_RE.search(str(name))
            if match:
                found = _reward_match(match)
                if found:
                    return found

    body = issue.get("body")
    raw_title = issue.get("title")
    title = raw_title if isinstance(raw_title, str) else ""
    if isinstance(body, str) and body:
        for match in _REWARD_AMOUNT_RE.finditer(body):
            if not _reward_context_near(body, match.start(), match.end(), title):
                continue
            found = _reward_match(match)
            if found:
                return found

    milestone = issue.get("milestone")
    if isinstance(milestone, dict) and milestone.get("amount") is not None:
        try:
            amount = float(milestone["amount"])
        except (ValueError, TypeError):
            amount = None
        if amount is not None and amount > 0:
            currency = milestone.get("currency")
            return amount, str(currency).upper() if isinstance(currency, str) and currency.strip() else "USD"

    return None, None


def _extract_github_bounty_reward(issue: dict) -> float | None:
    """Backward-compatible amount-only view of ``_extract_github_bounty_reward_details``."""
    amount, _currency = _extract_github_bounty_reward_details(issue)
    return amount


# End of GitHub Bounty Detection module
