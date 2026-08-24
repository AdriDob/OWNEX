"""FASE 5 — data-dir resolution for frozen bundles.

Regression: WorkBank and MarketKnowledgeBase hardcoded
``parents[3]/data`` — inside a PyInstaller bundle that resolves to an
unwritable/meaningless path. start_backend.py exports OWNEX_DATA_DIR
(%LOCALAPPDATA%/OWNEX); these stores must honor it like
application_assistant does.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
    return tmp_path


def test_workbank_honors_ownex_data_dir(data_dir: Path) -> None:
    from cores.direct_work_engine.workbank import WorkBank

    wb = WorkBank()
    assert wb._store_path == data_dir / "workbank.json"


def test_market_kb_honors_ownex_data_dir(data_dir: Path) -> None:
    from cores.direct_work_engine.market_evolution import MarketKnowledgeBase

    kb = MarketKnowledgeBase()
    assert kb._store_path == data_dir / "market_kb.json"


def test_explicit_store_path_still_wins(data_dir: Path) -> None:
    from cores.direct_work_engine.workbank import WorkBank

    custom = data_dir / "custom" / "wb.json"
    wb = WorkBank(store_path=custom)
    assert wb._store_path == custom


def test_dev_fallback_is_repo_data() -> None:
    """Without env var (dev), behavior stays repo-relative ./data."""
    import os

    monkey = pytest.MonkeyPatch()
    monkey.delenv("OWNEX_DATA_DIR", raising=False)
    try:
        from cores.direct_work_engine.workbank import _default_store_path

        p = _default_store_path()
        assert p.name == "workbank.json"
        assert p.parent.name == "data"
        assert not str(p).startswith(os.environ.get("OWNEX_DATA_DIR", "\0"))
    finally:
        monkey.undo()
