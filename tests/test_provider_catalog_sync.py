"""Provider catalog drift guard — frontend fallback mirrors backend SSOT.

Settings.vue keeps a static FALLBACK_PROVIDERS list used until
GET /api/settings/ai/providers responds (and when it fails). If the
backend PROVIDER_CATALOG gains/loses an id, the fallback would silently
drift — this guard pins both sides to the same id set.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _backend_provider_ids() -> set[str]:
    src = (REPO / "cores" / "ai" / "provider.py").read_text(encoding="utf-8")
    ids: set[str] = set()
    # ProviderSpec( blocks start with id="..." on their own line.
    for match in re.finditer(r'ProviderSpec\(\s*\n\s*id="([^"]+)"', src):
        ids.add(match.group(1))
    assert ids, "no ProviderSpec ids parsed from cores/ai/provider.py"
    return ids


def _frontend_fallback_ids() -> set[str]:
    src = (REPO / "frontend" / "src" / "pages" / "Settings.vue").read_text(encoding="utf-8")
    block = re.search(r"FALLBACK_PROVIDERS: ProviderCatalogEntry\[\] = \[(.*?)\]", src, re.S)
    assert block, "FALLBACK_PROVIDERS not found in Settings.vue"
    return set(re.findall(r"\{ id: '([^']+)'", block.group(1)))


def test_fallback_provider_ids_match_backend_catalog() -> None:
    backend = _backend_provider_ids()
    frontend = _frontend_fallback_ids()
    assert frontend == backend, (
        "FALLBACK_PROVIDERS drifted from PROVIDER_CATALOG. "
        f"Backend-only: {sorted(backend - frontend)} · "
        f"Frontend-only: {sorted(frontend - backend)}. "
        "Update Settings.vue FALLBACK_PROVIDERS to mirror the backend catalog."
    )
