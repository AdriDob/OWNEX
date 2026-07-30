"""Scope Reader — downloads, parses, and indexes program scope documents."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any

logger = logging.getLogger("ownex.scope_reader")


class _HTMLTextExtractor(HTMLParser):
    """Extract text from HTML using stdlib HTMLParser."""
    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "div"):
            self._text.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self._text.append(stripped + " ")

    def get_text(self) -> str:
        return "".join(self._text)


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    parser = _HTMLTextExtractor()
    parser.feed(html)
    raw = parser.get_text()
    # Clean up excessive whitespace
    lines = [line.strip() for line in raw.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def extract_text_from_pdf(content: bytes) -> str:
    """Basic PDF text extraction (ASCII fallback)."""
    text_parts: list[str] = []
    # Simple PDF text extraction: look for text between parentheses or BT/ET markers
    content_str = content.decode("latin-1", errors="replace")

    # Try basic PDF text extraction
    in_text = False
    for line in content_str.split("\n"):
        stripped = line.strip()
        if stripped.startswith("BT"):
            in_text = True
            continue
        if stripped.startswith("ET"):
            in_text = False
            continue
        if in_text:
            # Extract text between parentheses in Tj operations
            texts = re.findall(r"\(([^)]*)\)", stripped)
            if texts:
                text_parts.extend(texts)

    if text_parts:
        return "\n".join(text_parts)

    # Fallback: return all printable ASCII
    printable = re.findall(r"[ -~]{10,}", content_str)
    return "\n".join(printable[:100]) if printable else "(binary PDF, text extraction limited)"


def download_url(url: str, timeout: int = 15) -> tuple[bytes | None, str | None]:
    """Download content from a URL. Returns (content, content_type)."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            content_type = resp.headers.get("Content-Type", "").lower()
            return content, content_type
    except urllib.error.HTTPError as exc:
        logger.warning("HTTP error downloading %s: %d %s", url, exc.code, exc.reason)
        return None, None
    except urllib.error.URLError as exc:
        logger.warning("URL error downloading %s: %s", url, exc.reason)
        return None, None
    except Exception as exc:
        logger.warning("Download error for %s: %s", url, exc)
        return None, None


def extract_text(content: bytes, content_type: str | None) -> str:
    """Extract text based on content type."""
    if not content:
        return ""

    ct = (content_type or "").lower()

    if "pdf" in ct:
        return extract_text_from_pdf(content)

    # Try UTF-8 first, fallback to latin-1
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1", errors="replace")

    if "html" in ct:
        return extract_text_from_html(text)

    # Plain text or unknown
    return text


def extract_assets(text: str) -> dict[str, list[str]]:
    """Extract domains, subdomains, and potential endpoints from scope text."""
    assets: dict[str, list[str]] = {
        "domains": [],
        "wildcards": [],
        "urls": [],
        "ip_ranges": [],
        "technologies": [],
    }

    # Wildcard domains: *.example.com
    wildcards = re.findall(r"\*\.([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
    assets["wildcards"] = sorted(set(wildcards))

    # Regular domains
    domains = re.findall(r"(?:^|\s)([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)", text)
    assets["domains"] = sorted(set(
        d.lower() for d in domains
        if not d.startswith("*") and d.count(".") >= 1 and not d.startswith("$")
    ))

    # Full URLs
    urls = re.findall(r"https?://[^\s<>\"')\]]+", text)
    assets["urls"] = sorted(set(urls))

    # IP ranges (CIDR)
    ip_ranges = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b", text)
    assets["ip_ranges"] = sorted(set(ip_ranges))

    # Common technologies mentioned
    tech_keywords = [
        "react", "angular", "vue", "node", "django", "flask", "rails", "laravel",
        "graphql", "rest", "soap", "api", "websocket",
        "aws", "gcp", "azure", "cloudflare", "docker", "kubernetes",
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "wordpress", "joomla", "drupal", "shopify", "salesforce",
    ]
    text_lower = text.lower()
    found_techs = [t for t in tech_keywords if re.search(rf"\b{re.escape(t)}\b", text_lower)]
    assets["technologies"] = sorted(set(found_techs))

    return assets


def compute_hash(text: str) -> str:
    """Compute a hash of the text for change detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def detect_changes(old_text: str | None, new_text: str) -> list[str]:
    """Detect meaningful changes between old and new scope text."""
    if not old_text:
        return ["First scan — no previous scope to compare"]

    changes: list[str] = []

    old_lower = old_text.lower()
    new_lower = new_text.lower()

    # Check for new wildcards
    old_wild = set(re.findall(r"\*\.([a-zA-Z0-9.-]+)", old_lower))
    new_wild = set(re.findall(r"\*\.([a-zA-Z0-9.-]+)", new_lower))
    added = new_wild - old_wild
    removed = old_wild - new_wild
    if added:
        changes.append(f"Nuevos wildcards en scope: {', '.join(sorted(added))}")
    if removed:
        changes.append(f"Wildcards removidos del scope: {', '.join(sorted(removed))}")

    # Check for new domains
    old_domains = set(re.findall(r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,})\b", old_lower))
    new_domains = set(re.findall(r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.[a-z]{2,})\b", new_lower))
    added_domains = new_domains - old_domains
    if added_domains:
        changes.append(f"Nuevos dominios: {', '.join(sorted(added_domains)[:10])}")

    # Size change
    size_ratio = len(new_text) / max(len(old_text), 1)
    if size_ratio > 2.0:
        changes.append(f"Scope expandido significativamente ({size_ratio:.1f}x más contenido)")
    elif size_ratio < 0.5:
        changes.append(f"Scope reducido ({size_ratio:.1f}x menos contenido)")

    return changes if changes else ["No se detectaron cambios significativos"]


def summarize_with_ai(text: str, program_name: str) -> str:
    """Summarize scope text using AI provider."""
    try:
        from cores.ai.provider import get_provider

        # Truncate very long texts
        if len(text) > 8000:
            text = text[:8000] + "\n...[truncated]"

        prompt = f"""Resumí el scope del programa bug bounty "{program_name}" en 3-5 líneas.

Extraé:
- Qué está en scope (dominios, wildcards, apps)
- Tecnologías mencionadas
- Exclusiones importantes
- Reglas especiales
- URLs/endpoints relevantes

Texto del scope:
{text}

Resumen conciso:"""

        provider = get_provider()
        response = provider.chat([
            {"role": "system", "content": "Sos un analista de bug bounty. Resumí scopes de forma concisa y precisa."},
            {"role": "user", "content": prompt},
        ], max_tokens=512)

        if response and isinstance(response, str):
            return response.strip()
    except Exception as exc:
        logger.warning("AI summarization failed: %s", exc)

    return "(AI summary unavailable — scope indexed)"


def read_program_scope(url: str, program_name: str, previous_hash: str | None = None, previous_text: str | None = None) -> dict[str, Any]:
    """Full scope reading pipeline for a single program URL.

    Returns a dict with: raw_text, summary, hash, assets_extracted, changes, content_type.
    """
    logger.info("Reading scope for %s: %s", program_name, url)

    # 1. Download
    content, content_type = download_url(url)
    if not content:
        return {
            "error": f"Could not download scope from {url}",
            "raw_text": "",
            "summary": "",
            "hash": "",
            "assets_extracted": "[]",
            "changes_from_previous": json.dumps(["Download failed"]),
            "content_type": None,
        }

    # 2. Extract text
    raw_text = extract_text(content, content_type)

    if not raw_text.strip():
        raw_text = f"(Content downloaded but text extraction returned empty. Type: {content_type})"

    # 3. Hash
    doc_hash = compute_hash(raw_text)

    # 4. Detect changes
    changes: list[str] = []
    if previous_hash and doc_hash == previous_hash:
        changes = ["No changes detected"]
    else:
        changes = detect_changes(previous_text, raw_text)

    # 5. Extract assets
    assets = extract_assets(raw_text)

    # 6. Summarize with AI
    summary = summarize_with_ai(raw_text, program_name)

    return {
        "raw_text": raw_text,
        "summary": summary,
        "hash": doc_hash,
        "assets_extracted": json.dumps(assets, ensure_ascii=False),
        "changes_from_previous": json.dumps(changes, ensure_ascii=False),
        "content_type": content_type,
    }
