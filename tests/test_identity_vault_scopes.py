"""Phase 1: IdentityVault workspace isolation + storage hygiene.

Isolated via tmp HOME (never touches ~/.orion real).
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture()
def vault_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    import cores.identity_vault as iv

    iv._VAULT_PATH = None
    iv._VAULT_DATA = {}
    iv._VAULT_INSTANCE = None
    import cores.vault_crypto as vc

    vc._VAULT_KEY = None
    yield iv
    iv._VAULT_PATH = None
    iv._VAULT_DATA = {}
    iv._VAULT_INSTANCE = None
    vc._VAULT_KEY = None


class TestWorkspaceIsolation:
    def test_scoped_entry_invisible_to_other_workspace(self, vault_env):
        v = vault_env.get_identity_vault()
        v.store_credentials("dataannotation", "a@x.com", password="pw1", workspace="PUBLIC_WORK")
        assert v.get_credentials("dataannotation", "PUBLIC_WORK")["password"] == "pw1"
        assert vault_env.get_identity_vault().get_credentials("dataannotation", "CAPITAL") == {}
        assert vault_env.get_identity_vault().get_credentials("dataannotation") == {}

    def test_unscoped_legacy_entry_strict_namespaces(self, vault_env):
        # Strict: a scoped query never sees the legacy unscoped namespace.
        # Migration path is explicit re-store with workspace=....
        v = vault_env.get_identity_vault()
        v.store_credentials("outlier", "b@x.com", password="pw2")
        assert v.get_credentials("outlier")["password"] == "pw2"
        assert v.get_credentials("outlier", "PUBLIC_WORK") == {}

    def test_workspaces_do_not_share(self, vault_env):
        v = vault_env.get_identity_vault()
        v.store_credentials("x", "e", token="t-drop", workspace="DROPPINGLABEL")
        v.store_credentials("x", "e", token="t-meli", workspace="MERCADO_LIBRE")
        assert v.get_credentials("x", "DROPPINGLABEL")["token"] == "t-drop"
        assert v.get_credentials("x", "MERCADO_LIBRE")["token"] == "t-meli"

    def test_workspace_field_persisted(self, vault_env, tmp_path):
        v = vault_env.get_identity_vault()
        v.store_credentials("y", "e@y.com", password="pw", workspace="CAPITAL")
        raw = json.loads((tmp_path / ".orion" / "identity_vault.json").read_text(encoding="utf-8"))
        assert raw["CAPITAL::y"]["workspace"] == "CAPITAL"

    def test_scoped_remove_does_not_touch_other_workspace(self, vault_env):
        v = vault_env.get_identity_vault()
        v.store_credentials("x", "e", token="t-a", workspace="A")
        v.store_credentials("x", "e", token="t-b", workspace="B")
        v.remove_credentials("x", "A")
        assert v.get_credentials("x", "A") == {}
        assert v.get_credentials("x", "B")["token"] == "t-b"


class TestStorageHygiene:
    def test_no_plaintext_secrets_on_disk(self, vault_env, tmp_path):
        v = vault_env.get_identity_vault()
        v.store_credentials("z", "e@z.com", token="super-secret-token", password="pw", workspace="CAPITAL")
        raw = (tmp_path / ".orion" / "identity_vault.json").read_text(encoding="utf-8")
        assert "super-secret-token" not in raw

    def test_vault_file_is_owner_only(self, vault_env, tmp_path):
        import os

        v = vault_env.get_identity_vault()
        v.store_credentials("z", "e@z.com", password="pw")
        mode = oct(os.stat(tmp_path / ".orion" / "identity_vault.json").st_mode & 0o777)
        assert mode == "0o600"
