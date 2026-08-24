"""Packaging regression guards — Tauri bundle integrity (FASE 4).

These tests pin the contracts the Windows installer depends on. The
2026-08-24 audit found no test would catch a broken bundle config (the
Gen2-era MSI shipped without its sidecar's _internal/ for weeks).

All checks are file-based and CI-safe on Linux.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def tauri_conf() -> dict:
    conf_path = REPO_ROOT / "src-tauri" / "tauri.conf.json"
    return json.loads(conf_path.read_text(encoding="utf-8"))


class TestTauriConf:
    def test_parseable_and_branded(self, tauri_conf: dict) -> None:
        assert tauri_conf["productName"] == "OWNEX Alpha"
        assert tauri_conf["version"]
        assert not tauri_conf["productName"].lower().startswith("omega"), (
            "Omega branding must not leak into the product name"
        )

    def test_frontend_dist_exists_with_entry(self, tauri_conf: dict) -> None:
        dist = REPO_ROOT / "src-tauri" / tauri_conf["build"]["frontendDist"]
        assert dist.is_dir(), f"frontendDist missing: {dist}"
        assert (dist / "index.html").is_file(), "dist has no SPA entry"

    def test_external_bin_matches_sidecar_contract(self, tauri_conf: dict) -> None:
        external_bin = tauri_conf["bundle"]["externalBin"][0]
        # Tauri contract: <name>-<target-triple>.exe must exist next to the
        # spec output; here we pin the name used by the CI copy step.
        assert external_bin == "binaries/ownex-backend"

    def test_csp_allows_dynamic_backend_ports(self, tauri_conf: dict) -> None:
        csp = tauri_conf["app"]["security"]["csp"]
        assert "http://127.0.0.1:*" in csp, "CSP must allow dynamic HTTP ports"
        assert "ws://127.0.0.1:*" in csp, "CSP must allow dynamic WS ports"


class TestSidecarSpec:
    def test_spec_is_onefile_named_ownex_backend(self) -> None:
        spec = (REPO_ROOT / "OWNEX-Backend.spec").read_text(encoding="utf-8")
        assert 'name="ownex-backend"' in spec, "sidecar exe name must match externalBin"
        # Onefile contract: a top-level EXE with all blobs, no COLLECT().
        assert "COLLECT(" not in spec, (
            "ONEFILE required: Tauri copies a single file per target-triple "
            "(the Gen2 ONEDIR MSI shipped without _internal/ for weeks)"
        )

    def test_entry_accepts_port_host_data_dir(self) -> None:
        entry = (REPO_ROOT / "src-tauri" / "binaries" / "start_backend.py").read_text(encoding="utf-8")
        for arg in ("--port", "--host", "--data-dir", "--log-level"):
            assert f'"{arg}"' in entry, f"sidecar entry must accept {arg}"

    def test_launcher_forces_desktop_posture(self) -> None:
        entry = (REPO_ROOT / "src-tauri" / "binaries" / "start_backend.py").read_text(encoding="utf-8")
        assert 'os.environ["OWNEX_DESKTOP"] = "1"' in entry

    def test_ci_guard_rejects_stub_sidecar(self) -> None:
        """CI validates the built exe is >= 50MB (the 19.91MB stub incident)."""
        workflow = (REPO_ROOT / ".github" / "workflows" / "ownex-tauri-windows.yml").read_text(encoding="utf-8")
        assert "50" in workflow and ("Validate sidecar" in workflow or "minimum" in workflow.lower())


class TestVersionSync:
    def test_versions_agree_across_manifests(self, tauri_conf: dict) -> None:
        version = tauri_conf["version"]
        cargo = (REPO_ROOT / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8")
        pkg = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        assert f'version = "{version}"' in cargo
        assert pkg["version"] == version
