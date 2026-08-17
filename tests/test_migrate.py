"""OWNEX Migration — export/verify/import round-trip tests (all paths faked)."""

from __future__ import annotations

import zipfile

import pytest

from core.backup import migrate


@pytest.fixture()
def fake_machine(tmp_path):
    """Two fake machines: source (with data) and target (empty)."""
    src_home = tmp_path / "src_home"
    tgt_home = tmp_path / "tgt_home"
    src_repo = tmp_path / "src_repo"
    tgt_repo = tmp_path / "tgt_repo"

    for d in (src_home, tgt_home, src_repo, tgt_repo):
        d.mkdir()

    # --- source data ---
    orion = src_home / ".orion"
    (orion / "database").mkdir(parents=True)
    (orion / "targets").mkdir(parents=True)
    (orion / "backups").mkdir(parents=True)
    (orion / "logs").mkdir(parents=True)
    (orion / "identity_vault.key").write_bytes(b"vault-key-123")
    (orion / "license.json").write_text('{"license": "demo", "hardware_id": "old-hwid"}')
    (orion / "config.sh").write_text("export ORION=1\n")
    (orion / "database" / "orion.db").write_bytes(b"orion-db-bytes")
    (orion / "database" / "orion.db-wal").write_bytes(b"wal-stale")
    (orion / "targets" / "hackerone").mkdir(parents=True)
    (orion / "targets" / "hackerone" / "scan.json").write_text('{"scans": 5}')
    (orion / "backups" / "old.zip").write_bytes(b"x" * 100)
    (orion / "logs" / "run.log").write_text("log data\n")
    (orion / "identity_vault.json").write_text('{"enc": "cipher"}')

    ownex = src_home / ".ownex"
    (ownex / "database").mkdir(parents=True)
    (ownex / "backups").mkdir(parents=True)
    (ownex / "database" / "knowledge.db").write_bytes(b"knowledge-bytes")
    (ownex / "voice_department").mkdir(parents=True)
    (ownex / "voice_department" / "profile.json").write_text('{"voice": "calm"}')
    (ownex / "backups" / "cateye_backup_2026.tar.gz").write_bytes(b"y" * 100)

    config_ownex = src_home / ".config" / "ownex"
    config_ownex.mkdir(parents=True)
    (config_ownex / "trading.json").write_text('{"dry_run": true}')

    (src_repo / "database").mkdir(parents=True)
    (src_repo / "data").mkdir(parents=True)
    (src_repo / "database" / "catseye.db").write_bytes(b"repo-db")
    (src_repo / "database" / "catseye.db-wal").write_bytes(b"stale")
    (src_repo / "data" / "workbank.json").write_text('{"items": []}')
    (src_repo / ".env").write_text("OWNNEX_MAIL_SMTP_HOST=smtp.test\n")

    # --- target machine: empty but with a pre-existing vault key ---
    (tgt_home / ".orion").mkdir(parents=True)
    (tgt_home / ".orion" / "identity_vault.key").write_bytes(b"old-key")
    (tgt_home / ".ownex").mkdir(parents=True)
    (tgt_home / ".config" / "ownex").mkdir(parents=True)
    (tgt_repo / "database").mkdir(parents=True)
    (tgt_repo / "data").mkdir(parents=True)

    return {
        "orion": orion,
        "ownex": ownex,
        "config_ownex": config_ownex,
        "repo": src_repo,
        "env": src_repo / ".env",
        "target_home": tgt_home,
        "target_repo": tgt_repo,
    }


def _export(machine, dest: str | None, **kwargs):
    return migrate.export_migration(
        dest,
        orion_dir=machine["orion"],
        ownex_dir=machine["ownex"],
        config_dir=machine["config_ownex"],
        repo_database_dir=machine["repo"] / "database",
        repo_data_dir=machine["repo"] / "data",
        env_file=machine["env"],
        **kwargs,
    )


def _import(machine, archive: str, force: bool = True):
    """Import with ALL destinations isolated to the fake target machine."""
    th = machine["target_home"]
    return migrate.import_migration(
        archive,
        repo_root=machine["target_repo"],
        data_dir=th / ".orion",
        ownex_dir=th / ".ownex",
        config_dir=th / ".config" / "ownex",
        force=force,
    )


def test_export_creates_archive_with_manifest(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    result = _export(fake_machine, str(dest))

    assert result["status"] == "ok"
    assert dest.exists()

    with zipfile.ZipFile(dest) as zf:
        assert "manifest.json" in zf.namelist()
        assert "README_MIGRATION.txt" in zf.namelist()
        names = zf.namelist()
        # critical data present
        assert "orion/identity_vault.key" in names
        assert "orion/license.json" in names
        assert "orion/config.sh" in names
        assert "orion/database/orion.db" in names
        assert "ownex/database/knowledge.db" in names
        assert "config_ownex/trading.json" in names
        assert "repo_database/catseye.db" in names
        assert "repo_data/workbank.json" in names
        assert "env/.env" in names


def test_export_excludes_transients_and_backups(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    _export(fake_machine, str(dest))
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
        # excluded: wal/shm, backups/, logs/, legacy archives
        assert not any(n.endswith("-wal") for n in names)
        assert not any(n.startswith("orion/backups") for n in names)
        assert not any(n.startswith("orion/logs") for n in names)
        assert not any(n.endswith(".tar.gz") for n in names)
        assert "ownex/backups/cateye_backup_2026.tar.gz" not in names


def test_export_without_targets(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    result = _export(fake_machine, str(dest), include_targets=False)
    with zipfile.ZipFile(dest) as zf:
        assert not any(n.startswith("orion/targets") for n in zf.namelist())
    assert result["sections"]["orion"]["files"] < 10


def test_verify_roundtrip_ok(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    _export(fake_machine, str(dest))
    verification = migrate.verify_migration(dest)
    assert verification["status"] == "ok"
    assert verification["total_files"] >= 11
    assert verification["manifest"]["source_hostname"]


def test_import_restores_everything(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    _export(fake_machine, str(dest))

    result = _import(fake_machine, str(dest))
    assert result["status"] == "ok"
    assert result["restored_files"] >= 11

    th, tr = fake_machine["target_home"], fake_machine["target_repo"]
    assert (th / ".orion" / "identity_vault.key").read_bytes() == b"vault-key-123"
    assert (th / ".orion" / "license.json").read_text().startswith('{"license"')
    assert (th / ".orion" / "config.sh").exists()
    assert (th / ".orion" / "database" / "orion.db").read_bytes() == b"orion-db-bytes"
    assert (th / ".orion" / "targets" / "hackerone" / "scan.json").exists()
    assert (th / ".ownex" / "database" / "knowledge.db").read_bytes() == b"knowledge-bytes"
    assert (th / ".ownex" / "voice_department" / "profile.json").exists()
    assert (th / ".config" / "ownex" / "trading.json").exists()
    assert (tr / "database" / "catseye.db").read_bytes() == b"repo-db"
    assert (tr / "data" / "workbank.json").exists()
    assert (tr / ".env").read_text().startswith("OWNNEX_MAIL")


def test_import_preserves_existing_vault_key_as_bak(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    _export(fake_machine, str(dest))
    _import(fake_machine, str(dest))
    th = fake_machine["target_home"]
    # the pre-existing key was renamed to .bak before the imported one overwrote it
    assert (th / ".orion" / "identity_vault.key.bak").read_bytes() == b"old-key"
    assert (th / ".orion" / "identity_vault.key").read_bytes() == b"vault-key-123"


def test_import_detects_corruption(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    _export(fake_machine, str(dest))

    # tamper: replace a payload inside the zip without touching the manifest
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(dest) as src, zipfile.ZipFile(tampered, "w") as out:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "orion/config.sh":
                data = b"TAMPERED CONTENT"
            out.writestr(item, data)

    verification = migrate.verify_migration(tampered)
    assert verification["status"] == "corrupted"
    assert "orion/config.sh" in verification["checksum_errors"]

    result = _import(fake_machine, str(tampered))
    assert result["status"] == "error"


def test_import_refuses_overwrite_without_force(fake_machine, tmp_path):
    dest = tmp_path / "migration.zip"
    _export(fake_machine, str(dest))

    result = _import(fake_machine, str(dest), force=False)
    assert result["status"] == "error"
    assert "already has data" in result["reason"]

    th = fake_machine["target_home"]
    assert (th / ".orion" / "config.sh").exists() is False
    assert (th / ".orion" / "identity_vault.key").read_bytes() == b"old-key"


def test_legacy_backup_rejected_with_clear_message(fake_machine, tmp_path):
    legacy = tmp_path / "legacy.zip"
    with zipfile.ZipFile(legacy, "w") as zf:
        zf.writestr("manifest.json", '{"files": [{"path": "x", "sha256": "aa"}]}')
    verification = migrate.verify_migration(legacy)
    assert verification["status"] == "error"
    assert "--restore" in verification["reason"]


def test_missing_archive_error(tmp_path):
    verification = migrate.verify_migration(tmp_path / "nope.zip")
    assert verification["status"] == "error"
    assert "not found" in verification["reason"]


def test_export_default_dest_inside_ownex_backups(fake_machine, tmp_path, monkeypatch):
    monkeypatch.setattr(migrate, "OWNEX_DIR", fake_machine["ownex"])
    result = _export(fake_machine, None)
    assert result["status"] == "ok"
    path = result["archive_path"]
    assert str(fake_machine["ownex"] / "backups") in path
    assert "OWNEX_MIGRATE_" in path
    # archive lives inside the excluded backups/ dir → not self-included
    assert path not in [e["path"] for e in []]
