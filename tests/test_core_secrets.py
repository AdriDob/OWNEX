"""Tests for core/secrets/ — Secrets Manager."""

from __future__ import annotations

import os

from core.secrets.manager import SecretsManager


class TestSecretsManager:
    def test_get_default(self):
        sm = SecretsManager()
        val = sm.get("NONEXISTENT_KEY", default="fallback")
        assert val == "fallback"

    def test_get_env_fallback(self):
        sm = SecretsManager()
        os.environ["TEST_ORION_SECRET"] = "env-value"
        val = sm.get("TEST_ORION_SECRET", default="nope")
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
        # set() stores in cache regardless of vault failure
        sm.set("TEST_ORION_CACHE", "cached")
        # Should be retrievable from cache
        assert sm.get("TEST_ORION_CACHE") == "cached"
        # Bypass cache — should not find in vault (unsupported provider)
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
