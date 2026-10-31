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
import re
import os
import socket
import tempfile
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

    def add(self, name: str, url: str, discovered_by: str) -> SourceCandidate:
        source_url = _validate_public_url(url)
        source_id = hashlib.sha256(source_url.encode()).hexdigest()[:24]
        existing = self._candidates.get(source_id)
        if existing:
            return existing
        item = SourceCandidate(source_id, name[:200], source_url, discovered_by[:100])
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


def discover_github_repositories(*, registry: SourceDiscoveryRegistry | None = None, client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch a bounded set of GitHub topic candidates. Never auto-probes or activates them."""
    registry = registry or SourceDiscoveryRegistry()
    own_client = client is None
    http = client or httpx.Client(
        timeout=httpx.Timeout(HTTP_TIMEOUT_SECONDS),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
    )
    today = datetime.now(UTC).date()
    queries = (
        f"topic:ai-agent-bounty created:<={today - timedelta(days=30)} stars:>10",
        f"topic:x402 created:<={today - timedelta(days=60)}",
        f"topic:agent-payment created:<={today - timedelta(days=60)}",
        f"topic:bounty-platform created:<={today - timedelta(days=60)}",
        f"topic:mcp-server created:<={today - timedelta(days=60)} stars:>10",
    )
    discovered = 0
    errors = []
    known_urls = registry.known_urls()
    try:
        for query in queries:
            try:
                response = http.get("https://api.github.com/search/repositories", params={"q": query, "sort": "updated", "per_page": 30})
                if response.status_code != 200:
                    errors.append(f"github_search_http_{response.status_code}")
                    continue
                if len(response.content) > MAX_DOCUMENT_BYTES:
                    errors.append("github_search_response_too_large")
                    continue
                payload = _decode_json(response) or {}
                items = payload.get("items", [])
                if not isinstance(items, list):
                    errors.append("github_search_malformed")
                    continue
                for repo in items[:30]:
                    if not isinstance(repo, dict) or repo.get("archived") or repo.get("fork"):
                        continue
                    html_url = repo.get("html_url")
                    full_name = repo.get("full_name")
                    if not isinstance(html_url, str) or not isinstance(full_name, str) or not html_url.startswith("https://github.com/"):
                        continue
                    if html_url not in known_urls:
                        registry.add(full_name, html_url, "github_topic_search")
                        discovered += 1
                        known_urls.add(html_url)
            except httpx.HTTPError as exc:
                errors.append(f"github_search_{type(exc).__name__}")
    finally:
        if own_client:
            http.close()
    registry.refresh_lifecycle()
    return {"source": "github_topic_search", "new_candidates": discovered, "errors": errors, "activation_requires_human": True}


def run_daily_meta_discovery() -> dict[str, Any]:
    """Scheduler entry point; GitHub is currently the only enabled discovery feed."""
    try:
        return discover_github_repositories()
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
    import hashlib
    import json
    import re
    from datetime import datetime, timezone

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
                # Map GitHub issue to SourceCandidate
                candidate = SourceCandidate(
                    id=f"github_{repo_owner}_{repo_name}_{issue['number']}",
                    name=issue.get("title", "GitHub Bounty Issue")[:200],
                    source_url=issue.get("html_url", ""),
                    discovered_by="github_api",
                    # Extract reward from issue body or labels
                    profile={
                        "endpoints": [{"method": "GET", "path": issue.get("body", "")[:200]}] if issue.get("body") else [],
                        "capabilities": ["bug-reporting"],
                        "auth_methods": [],
                        "evidence": [{"url": issue.get("html_url", ""), "type": "github_issue"}],
                        "reward_reported": _extract_github_bounty_reward(issue),
                        "reward_status": "UNKNOWN" if not _extract_github_bounty_reward(issue) else "REPORTED",
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


def _extract_github_bounty_reward(issue: dict) -> float | None:
    """Extract USD amount from GitHub issue bounty labels or body.

    Aligned with OWNEX revenue rule: only processes bounties with
    declared/reportable reward amounts.
    """
    # Check labels for $ amount
    labels = issue.get("labels", [])
    for label in labels:
        label_name = label.get("name", "").lower()
        match = re.search(r"\$(\d+(?:\.\d{1,2})?)", label_name)
        if match:
            return float(match.group(1))

    # Check body for $ amounts
    body = issue.get("body", "")
    match = re.search(r"\$(\d+(?:\.\d{1,2})?)", body)
    if match:
        return float(match.group(1))

    # Check milestone for amount
    milestone = issue.get("milestone")
    if milestone and milestone.get("amount"):
        try:
            return float(milestone["amount"])
        except (ValueError, TypeError):
            pass

    return None


# End of GitHub Bounty Detection module
