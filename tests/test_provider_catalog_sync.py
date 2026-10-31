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


def test_codex_provider_is_read_only_and_reports_unavailable_without_cli(monkeypatch) -> None:
    from cores.ai.provider import CodexCLIProvider

    monkeypatch.setattr("cores.ai.provider.shutil.which", lambda _: None)
    provider = CodexCLIProvider()
    assert not provider.is_available()


def test_codex_provider_extracts_final_message(monkeypatch) -> None:
    import json
    from types import SimpleNamespace

    from cores.ai.provider import CodexCLIProvider

    monkeypatch.setattr("cores.ai.provider.shutil.which", lambda _: "/usr/bin/codex")
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["login", "status"]:
            return SimpleNamespace(returncode=0, stdout="Logged in using ChatGPT", stderr="")
        event = {"type": "item.completed", "item": {"type": "agent_message", "text": "Respuesta"}}
        return SimpleNamespace(returncode=0, stdout=json.dumps(event) + "\n", stderr="")

    monkeypatch.setattr("cores.ai.provider.subprocess.run", fake_run)
    provider = CodexCLIProvider()
    assert provider.chat([{"role": "user", "content": "Hola"}]) == "Respuesta"
    exec_call = calls[-1]
    assert "--sandbox" in exec_call[0]
    assert exec_call[0][exec_call[0].index("--sandbox") + 1] == "read-only"
    assert exec_call[1]["input"].endswith("USER: Hola")
