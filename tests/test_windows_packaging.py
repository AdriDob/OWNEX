"""Unit checks for Windows packaging path selection and overwrite safety."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import scripts.install_windows as installer


def test_version_comes_from_canonical_version_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    version_file = tmp_path / "VERSION"
    version_file.write_text("9.0.0\n", encoding="utf-8")
    monkeypatch.setattr(installer, "VERSION_FILE", version_file)

    assert installer._get_version() == "9.0.0"


def test_frontend_package_is_rebuilt_even_if_old_dist_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frontend = tmp_path / "frontend"
    (frontend / "dist").mkdir(parents=True)
    (frontend / "dist" / "index.html").write_text("stale", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, **kwargs):
        calls.append(cmd)
        if cmd == ["npm", "run", "build"]:
            (frontend / "dist" / "index.html").write_text("fresh", encoding="utf-8")

    monkeypatch.setattr(installer, "FRONTEND", frontend)
    monkeypatch.setattr(installer, "_run", fake_run)

    installer._ensure_frontend_built()

    assert calls == [["npm", "ci"], ["npm", "run", "build"]]
    assert (frontend / "dist" / "index.html").read_text(encoding="utf-8") == "fresh"


def test_pyinstaller_uses_existing_spec_and_dist_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path

    def fake_run(cmd: list[str], cwd: Path | None = None, **kwargs):
        exe = root / "dist" / "CATEYE" / "CATEYE"
        exe.parent.mkdir(parents=True)
        exe.touch()

    monkeypatch.setattr(installer, "ROOT", root)
    monkeypatch.setattr(installer, "_run", fake_run)
    monkeypatch.setattr(installer.sys, "platform", "linux")

    assert installer._run_pyinstaller() == root / "dist"


def test_portable_assembly_refuses_to_overwrite_existing_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "dist" / "install-windows"
    bundle = output / "CATEYE-9.0.0-win64"
    bundle.mkdir(parents=True)
    marker = bundle / "user.txt"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(installer, "OUTPUT", output)

    with pytest.raises(FileExistsError):
        installer._assemble_portable("9.0.0", tmp_path / "missing-build")

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_windows_installer_refuses_to_run_under_wsl_or_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer.sys, "platform", "linux")
    monkeypatch.setattr(sys, "argv", ["install_windows.py"])
    monkeypatch.setattr(installer, "_ensure_frontend_built", lambda: pytest.fail("build must not start on Linux"))

    with pytest.raises(SystemExit) as exc:
        installer.main()

    assert exc.value.code == 2
