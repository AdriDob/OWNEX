"""Tests for core/secrets/ — Secrets Manager."""

from __future__ import annotations

import os

from core.secrets.manager import SecretsManager


class TestSecretsManager:
    def test_get_default(self):
        sm = SecretsManager()
        val = sm.get("NONEXISTENT_KEY", default="fallback")
        assert val == "fallback"

    def test_get_no_env_bypass(self):
        """get() does NOT fall back to env vars — only Vault."""
        sm = SecretsManager()
        os.environ["TEST_ORION_SECRET"] = "env-value"
        val = sm.get("TEST_ORION_SECRET", default="nope")
        assert val == "nope"  # env var is ignored
        del os.environ["TEST_ORION_SECRET"]

    def test_get_with_env_fallback(self):
        """Transitional API still supports env fallback."""
        sm = SecretsManager()
        os.environ["TEST_ORION_SECRET"] = "env-value"
        val = sm.get_with_env_fallback("TEST_ORION_SECRET", default="nope")
        assert val == "env-value"
        del os.environ["TEST_ORION_SECRET"]

    def test_set_and_get(self):
        sm = SecretsManager()
        sm.set("TEST_ORION_KEY", "stored-value")
        val = sm.get("TEST_ORION_KEY")
        assert val == "stored-value"

    def test_delete(self):
        sm = SecretsManager()
        sm.set("TEST_ORION_DELETE", "to-delete")
        sm.delete("TEST_ORION_DELETE")
        val = sm.get("TEST_ORION_DELETE", default="")
        assert val == ""

    def test_get_or_raise(self):
        sm = SecretsManager()
        sm.set("TEST_ORION_EXISTS", "here")
        val = sm.get_or_raise("TEST_ORION_EXISTS")
        assert val == "here"

    def test_get_or_raise_missing(self):
        sm = SecretsManager()
        try:
            sm.get_or_raise("TEST_ORION_MISSING")
            raise AssertionError("Expected KeyError")
        except KeyError:
            pass

    def test_use_cache(self):
        sm = SecretsManager()
        sm.set("TEST_ORION_CACHE", "cached")
        assert sm.get("TEST_ORION_CACHE") == "cached"
        assert sm.get("TEST_ORION_CACHE", use_cache=False) == ""

    def test_health(self):
        sm = SecretsManager()
        h = sm.health()
        assert "vault_available" in h
        assert "cached_keys" in h
        assert "total_keys" in h

    def test_list_keys(self):
        sm = SecretsManager()
        sm.set("TEST_ORION_LIST_1", "a")
        sm.set("TEST_ORION_LIST_2", "b")
        keys = sm.list_keys()
        assert "TEST_ORION_LIST_1" in keys
        assert "TEST_ORION_LIST_2" in keys
        sm.delete("TEST_ORION_LIST_1")
        sm.delete("TEST_ORION_LIST_2")

    def test_import_env_vars(self):
        sm = SecretsManager()
        os.environ["TEST_ORION_IMPORT_1"] = "val1"
        os.environ["TEST_ORION_IMPORT_2"] = "val2"
        count = sm.import_env_vars(prefix="TEST_ORION_IMPORT_")
        assert count == 2
        assert sm.get("TEST_ORION_IMPORT_1") == "val1"
        assert sm.get("TEST_ORION_IMPORT_2") == "val2"
        del os.environ["TEST_ORION_IMPORT_1"]
        del os.environ["TEST_ORION_IMPORT_2"]
