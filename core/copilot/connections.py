from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.connection_detector")

FRONTEND_DIR = Path.home() / "projects" / "Rastro" / "frontend" / "src"
BACKEND_DIR = Path.home() / "projects" / "Rastro" / "api" / "routers"
CORE_API_DIR = Path.home() / "projects" / "Rastro" / "core" / "api"


def _normalize_path(path: str) -> str:
    path = re.sub(r"^(GET|POST|PUT|DELETE|PATCH)\s+", "", path.strip())
    path = re.sub(r":(\w+)", r"{\1}", path)
    path = path.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return path


def _scan_frontend_api_calls() -> set[str]:
    calls: set[str] = set()
    patterns = [
        r"`/api/[^`]+`",
        r"['\"]/api/[^'\"]+['\"]",
        r"fetch\(\s*['\"`](/api/[^'\"`]+)",
        r"axios\.\w+\(\s*['\"`](/api/[^'\"`]+)",
        r"api\.\w+\(\s*['\"`](/api/[^'\"`]+)",
        r"url:\s*['\"`](/api/[^'\"`]+)",
    ]
    for ext in ("*.ts", "*.vue"):
        for f in FRONTEND_DIR.rglob(ext):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                for pat in patterns:
                    for match in re.finditer(pat, text):
                        url = match.group(0).strip("'\"`")
                        url = re.sub(r"^[a-zA-Z]+\(?\s*['\"`]?", "", url)
                        url = re.sub(r"['\"`]\)?\s*$", "", url)
                        url = re.sub(r"\$\{[^}]+\}", "{param}", url)
                        url = _normalize_path(url)
                        if "/api/" in url:
                            calls.add(url)
            except (OSError, UnicodeDecodeError):
                continue
    return calls


def _scan_backend_routes() -> set[str]:
    routes: set[str] = set()
    route_pattern = re.compile(r'@\w+\.(?:get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']')
    include_pattern = re.compile(r'prefix\s*=\s*["\']([^"\']+)["\']')

    for scan_dir in (BACKEND_DIR, CORE_API_DIR):
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob("*.py"):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                prefix = ""
                if m := include_pattern.search(text):
                    prefix = m.group(1).rstrip("/")

                for m in route_pattern.finditer(text):
                    path = prefix + "/" + m.group(1).lstrip("/")
                    path = _normalize_path(path)
                    routes.add(path)
            except (OSError, UnicodeDecodeError):
                continue
    return routes


def _scan_frontend_components() -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    data_ref_patterns = [
        r"\.findings\b",
        r"\.reports\b",
        r"\.targets\b",
        r"\.endpoints\b",
        r"\.pipeline\b",
        r"\.hypotheses\b",
        r"\.verdicts\b",
        r"\.evidence\b",
        r"\.bounties\b",
        r"\.opportunities\b",
    ]
    store_pattern = re.compile(r"use\w+Store\(")

    for f in FRONTEND_DIR.rglob("*.vue"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            rel = f.relative_to(FRONTEND_DIR)
            if not store_pattern.search(text):
                continue
            for pat in data_ref_patterns:
                if re.search(pat, text):
                    ref = pat.strip("\\")
                    issues.append({"file": str(rel), "pattern": ref, "type": "data_reference_without_fetch"})
        except (OSError, UnicodeDecodeError):
            continue

    return issues


def run_connection_audit() -> dict[str, Any]:
    frontend_calls = _scan_frontend_api_calls()
    backend_routes = _scan_backend_routes()
    component_issues = _scan_frontend_components()

    fe_norm = set()
    for url in frontend_calls:
        url = re.sub(r"\{param\}", r"{param}", url)
        fe_norm.add(url)

    be_norm = set()
    for url in backend_routes:
        be_norm.add(url)

    orphaned_fe = fe_norm - be_norm
    orphaned_be = be_norm - fe_norm

    def _flex_match(url: str, candidates: set[str]) -> bool:
        pattern = re.sub(r"\{[^}]+\}", "[^/]+", re.escape(url))
        return any(re.fullmatch(pattern, c) for c in candidates)

    true_orphaned_fe = {u for u in orphaned_fe if not _flex_match(u, be_norm)}
    true_orphaned_be = {u for u in orphaned_be if not _flex_match(u, fe_norm)}

    return {
        "frontend_calls_count": len(frontend_calls),
        "backend_routes_count": len(backend_routes),
        "frontend_not_in_backend": sorted(true_orphaned_fe)[:50],
        "backend_not_in_frontend": sorted(true_orphaned_be)[:50],
        "component_data_issues": component_issues[:30],
        "summary": {
            "matched": len(fe_norm & be_norm),
            "frontend_orphans": len(true_orphaned_fe),
            "backend_orphans": len(true_orphaned_be),
            "component_red_flags": len(component_issues),
        },
    }
