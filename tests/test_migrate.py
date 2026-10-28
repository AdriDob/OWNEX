"""Tests for OWNEX Full Migration (cores/backup/migrate.py).

CRITICAL: all destinations injectable via tmp_path. Tests NEVER touch
the real home (~/.orion, ~/.ownex, ~/.config/ownex).
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from cores.backup.migrate import export_migration, import_migration, verify_migration


@pytest.fixture()
def fake_machine(tmp_path):
    """Fake source machine: orion/ownex/config dirs + repo database/data + .env."""
    src = tmp_path / "src"
    orion = src / "orion_home"
    ownex = src / "ownex_home"
    config = src / "config_home"
    repo_db = src / "repo" / "database"
    repo_data = src / "repo" / "data"
    for d in (orion, ownex, config, repo_db, repo_data):
        d.mkdir(parents=True)
    (orion / "config.sh").write_text("# fake config")
    (orion / "identity_vault.json").write_text("{}")
    (orion / "identity_vault.key").write_bytes(b"x" * 32)
    (orion / "license.json").write_text("{}")
    (orion / "database").mkdir()
    (orion / "database" / "orion.db").write_text("fake db")
    (config / "trading.json").write_text('{"dry_run": true}')
    (repo_db / "catseye.db").write_text("fake repo db")
    (repo_data / "workbank.json").write_text("[]")
    (src / "repo" / ".env").write_text("FOO=bar\n")
    # Legacy/transient junk that must be excluded.
    (orion / "old.tar.gz").write_text("legacy")
    (orion / "data.zip").write_text("legacy zip")
    (repo_db / "catseye.db-wal").write_text("wal transient")
    return {
        "orion": orion,
        "ownex": ownex,
        "config": config,
        "repo_db": repo_db,
        "repo_data": repo_data,
        "env": src / "repo" / ".env",
        "dest": tmp_path / "out.zip",
    }


def _export(fake_machine):
    fm = fake_machine
    return export_migration(
        fm["dest"],
        orion_dir=fm["orion"],
        ownex_dir=fm["ownex"],
        config_dir=fm["config"],
        repo_database_dir=fm["repo_db"],
        repo_data_dir=fm["repo_data"],
        env_file=fm["env"],
    )


class TestExport:
    def test_export_ok(self, fake_machine):
        result = _export(fake_machine)
        assert result["status"] == "ok"
        assert Path(result["archive_path"]).exists()
        assert result["total_files"] >= 8

    def test_manifest_sections(self, fake_machine):
        result = _export(fake_machine)
        assert result["status"] == "ok"
        with zipfile.ZipFile(result["archive_path"]) as zf:
            manifest = json.loads(zf.read("manifest.json"))
        assert manifest["tool"] == "ownex-migrate"
        assert set(manifest["sections"]) == {"orion", "ownex", "config_ownex", "repo_database", "repo_data", "env"}
        assert manifest["total_files"] == result["total_files"]
        assert "source_hwid" in manifest and "source_hostname" in manifest

    def test_excludes_legacy_and_transients(self, fake_machine):
        result = _export(fake_machine)
        with zipfile.ZipFile(result["archive_path"]) as zf:
            names = zf.namelist()
        assert not any(
            n.endswith((".tar.gz", ".zip")) and n != "manifest.json" for n in names if "old" in n or "data.zip" in n
        )
        assert not any(n.endswith("-wal") or n.endswith("-shm") for n in names)

    def test_exclude_targets(self, fake_machine, tmp_path):
        targets = fake_machine["orion"] / "targets" / "hackerone"
        targets.mkdir(parents=True)
        (targets / "scan.json").write_text("{}")
        result = export_migration(
            tmp_path / "notargets.zip",
            orion_dir=fake_machine["orion"],
            ownex_dir=fake_machine["ownex"],
            config_dir=fake_machine["config"],
            repo_database_dir=fake_machine["repo_db"],
            repo_data_dir=fake_machine["repo_data"],
            env_file=fake_machine["env"],
            include_targets=False,
        )
        assert result["status"] == "ok"
        with zipfile.ZipFile(result["archive_path"]) as zf:
            assert not any("targets/" in n for n in zf.namelist())


class TestVerify:
    def test_verify_ok(self, fake_machine):
        result = _export(fake_machine)
        v = verify_migration(result["archive_path"])
        assert v["status"] == "ok"
        assert v["total_files"] == result["total_files"]
        assert v["checksum_errors"] == []

    def test_verify_missing_file(self, tmp_path):
        v = verify_migration(tmp_path / "nope.zip")
        assert v["status"] == "error"

    def test_verify_rejects_legacy(self, tmp_path):
        legacy = tmp_path / "legacy.zip"
        with zipfile.ZipFile(legacy, "w") as zf:
            zf.writestr("something.txt", "x")
        v = verify_migration(legacy)
        assert v["status"] == "error"
        assert "--restore" in v["reason"]

    def test_corruption_detected(self, fake_machine, tmp_path):
        result = _export(fake_machine)
        # Corrupt one archived file by rewriting the zip with tampered content.
        src = Path(result["archive_path"])
        bad = tmp_path / "bad.zip"
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "manifest.json":
                    manifest = json.loads(data)
                    manifest["files"][0]["sha256"] = "0" * 64
                    data = json.dumps(manifest).encode()
                zout.writestr(item, data)
        v = verify_migration(bad)
        assert v["status"] == "corrupted"
        assert len(v["checksum_errors"]) >= 1


class TestImport:
    def _tgt(self, tmp_path):
        tgt = tmp_path / "tgt"
        tgt.mkdir()
        return tgt

    def test_import_refuses_overwrite_without_force(self, fake_machine, tmp_path):
        result = _export(fake_machine)
        tgt = self._tgt(tmp_path)
        (tgt / "existing.txt").write_text("do not touch")
        out = import_migration(
            result["archive_path"],
            repo_root=tgt,
            data_dir=tgt / "orion",
            ownex_dir=tgt / "ownex",
            config_dir=tgt / "config",
            force=False,
        )
        assert out["status"] == "error"
        assert "--force" in out["reason"]
        # Nothing was touched.
        assert (tgt / "existing.txt").read_text() == "do not touch"
        assert not (tgt / "orion").exists()

    def test_import_full_restore(self, fake_machine, tmp_path):
        result = _export(fake_machine)
        tgt = self._tgt(tmp_path)
        out = import_migration(
            result["archive_path"],
            repo_root=tgt,
            data_dir=tgt / "orion",
            ownex_dir=tgt / "ownex",
            config_dir=tgt / "config",
            force=True,
        )
        assert out["status"] == "ok"
        assert out["restored_files"] == result["total_files"]
        assert (tgt / "orion" / "config.sh").read_text() == "# fake config"
        assert (tgt / "orion" / "identity_vault.key").read_bytes() == b"x" * 32
        assert (tgt / "config" / "trading.json").read_text() == '{"dry_run": true}'
        assert (tgt / ".env").read_text() == "FOO=bar\n"
        assert (tgt / "database" / "catseye.db").exists()

    def test_key_bak_preserved(self, fake_machine, tmp_path):
        result = _export(fake_machine)
        tgt = self._tgt(tmp_path)
        orion_tgt = tgt / "orion"
        orion_tgt.mkdir()
        (orion_tgt / "identity_vault.key").write_bytes(b"y" * 32)
        out = import_migration(
            result["archive_path"],
            repo_root=tgt,
            data_dir=orion_tgt,
            ownex_dir=tgt / "ownex",
            config_dir=tgt / "config",
            force=True,
        )
        assert out["status"] == "ok"
        assert (orion_tgt / "identity_vault.key.bak").read_bytes() == b"y" * 32
        assert (orion_tgt / "identity_vault.key").read_bytes() == b"x" * 32
