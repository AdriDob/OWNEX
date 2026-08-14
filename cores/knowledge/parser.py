"""Markdown parser for Obsidian vaults.

Parses note files WITHOUT modifying them. The vault is the source of truth:
OWNEX only reads, indexes and analyzes. Handles frontmatter YAML, wikilinks,
embeds, tags, headings, lists, checkboxes, code fences and markdown links.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# ── Regexes ────────────────────────────────────────────────────────────────

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)
_WIKILINK_RE = re.compile(r"!?\[\[([^\]\n]+?)\]\]")
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$", re.MULTILINE)
_CHECKBOX_RE = re.compile(r"^[ \t]*[-*+] \[[ xX]\]", re.MULTILINE)
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^)]*[\"'])?\)")
_TAG_RE = re.compile(r"(?:^|[\s(])(#([A-Za-z0-9_\-/]+))(?![A-Za-z0-9_\-/])", re.MULTILINE)
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_DATE_TEXT_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_EMBED_RE = re.compile(r"!\[\[([^\]\n]+?)\]\]")

_ATTACHMENT_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".pdf",
    ".mp4",
    ".mp3",
    ".wav",
    ".ogg",
    ".mov",
    ".mkv",
    ".zip",
    ".csv",
    ".xlsx",
    ".docx",
    ".pptx",
}

_MAX_RAW_SIZE = 8 * 1024 * 1024  # 8 MB — oversized files are skipped, not loaded


@dataclass
class ParsedNote:
    """Result of parsing a single markdown note."""

    path: str
    rel_path: str
    title: str
    aliases: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    frontmatter: dict[str, Any] = field(default_factory=dict)
    headings: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)  # wikilink targets (note names)
    embeds: list[str] = field(default_factory=list)  # attachments / embedded notes
    markdown_links: list[str] = field(default_factory=list)  # external/file urls
    checkboxes_total: int = 0
    checkboxes_checked: int = 0
    word_count: int = 0
    created: str | None = None
    modified: str | None = None
    updated: str | None = None
    has_frontmatter: bool = False
    oversized: bool = False
    body: str = field(default="", repr=False)


def _strip_code(content: str) -> str:
    """Remove fenced code blocks and inline code (tags/links inside are not real)."""
    content = _FENCE_RE.sub(" ", content)
    content = _INLINE_CODE_RE.sub(" ", content)
    return content


def _parse_date(value: Any) -> str | None:
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
            try:
                return datetime.strptime(value[:19], fmt).isoformat()
            except ValueError:
                continue
        match = _DATE_TEXT_RE.search(value)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}T00:00:00"
    return None


def _extract_aliases(frontmatter: dict[str, Any]) -> list[str]:
    raw = frontmatter.get("aliases", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            out.append(item.strip())
    return out


def _extract_tags(frontmatter: dict[str, Any], inline: list[str]) -> list[str]:
    tags: list[str] = []
    raw = frontmatter.get("tags", [])
    if isinstance(raw, str):
        raw = [raw]
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                tags.append(item.strip().lstrip("#"))
    for tag in inline:
        if tag not in tags:
            tags.append(tag)
    return tags


def _title_from_content(body: str, filename: str) -> str:
    for heading in _HEADING_RE.finditer(body):
        level, text = heading.groups()
        if level == "#" and text.strip():
            return text.strip()
    return filename


def parse_markdown(content: str, rel_path: str, base_name: str | None = None) -> ParsedNote:
    """Parse raw markdown content into a ParsedNote (never writes anything)."""
    path = rel_path.replace("\\", "/")
    filename = base_name or Path(rel_path).stem

    frontmatter: dict[str, Any] = {}
    has_frontmatter = False
    body = content

    fm_match = _FRONTMATTER_RE.match(content)
    if fm_match:
        raw_fm = fm_match.group(1)
        try:
            parsed = yaml.safe_load(raw_fm)
            if isinstance(parsed, dict):
                frontmatter = parsed
                has_frontmatter = True
        except yaml.YAMLError:
            frontmatter = {}
        body = content[fm_match.end() :]

    stripped = _strip_code(body)

    title = _title_from_content(body, filename)
    aliases = _extract_aliases(frontmatter)
    links: list[str] = []
    embeds: list[str] = []
    for match in _WIKILINK_RE.finditer(stripped):
        raw = match.group(1)
        is_embed = match.group(0).startswith("!")
        target = raw.split("|")[0].split("#")[0].strip()
        if not target:
            continue
        if is_embed:
            embeds.append(target)
        else:
            links.append(target)

    markdown_links = [
        url for _, url in _MD_LINK_RE.findall(stripped) if not url.startswith("#") and not url.startswith("!")
    ]

    inline_tags = [t for _, t in _TAG_RE.findall(stripped)]
    tags = _extract_tags(frontmatter, inline_tags)

    headings = [m.group(2).strip() for m in _HEADING_RE.finditer(body) if m.group(2).strip()]

    checkboxes = _CHECKBOX_RE.findall(body)
    checked = sum(1 for box in checkboxes if box.strip().endswith("x"))

    words = len(re.findall(r"\b\w+\b", stripped))

    return ParsedNote(
        path=path,
        rel_path=path,
        title=title,
        aliases=aliases,
        tags=tags,
        frontmatter=frontmatter,
        headings=headings,
        links=links,
        embeds=embeds,
        markdown_links=markdown_links,
        checkboxes_total=len(checkboxes),
        checkboxes_checked=checked,
        word_count=words,
        created=_parse_date(frontmatter.get("created") or frontmatter.get("date")),
        modified=_parse_date(frontmatter.get("modified")),
        updated=_parse_date(frontmatter.get("updated")),
        has_frontmatter=has_frontmatter,
        body=body,
    )


def is_attachment(name: str) -> bool:
    """True if the filename is an attachment (image/pdf/media/etc)."""
    return Path(name).suffix.lower() in _ATTACHMENT_EXTS


def read_note_safe(path: Path, vault_root: Path) -> str | None:
    """Read a note file, guarding against symlink escape and oversized files."""
    resolved = path.resolve()
    root = vault_root.resolve()
    if root not in resolved.parents and resolved != root:
        return None
    if resolved.is_symlink():
        return None
    try:
        size = resolved.stat().st_size
    except OSError:
        return None
    if size > _MAX_RAW_SIZE:
        return None
    try:
        return resolved.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
