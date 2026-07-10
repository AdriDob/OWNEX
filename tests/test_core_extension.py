"""Tests for core/extension/ — Extension SDK."""

from __future__ import annotations

from core.extension.capabilities import Capability, CapabilityRegistry
from core.extension.hooks import HookRegistry, get_hook_registry, on_hook
from core.extension.manifest import ExtensionManifest
from core.extension.registry import ExtensionRegistry
from core.extension.settings import ApiKeyField, NumberField, SelectField, SwitchField, TextField


class TestSettingsField:
    def test_text_field(self):
        f = TextField(key="name", label="Name", default="world")
        assert f.key == "name"
        assert f.field_type == "text"
        assert f.default == "world"

    def test_api_key_field(self):
        f = ApiKeyField(key="key", label="API Key", required=True)
        assert f.field_type == "password"
        assert f.required is True

    def test_switch_field(self):
        f = SwitchField(key="enabled", label="Enabled")
        assert f.field_type == "switch"
        assert f.default is False

    def test_number_field(self):
        f = NumberField(key="count", label="Count", min_value=0, max_value=100)
        assert f.field_type == "number"
        assert f.min_value == 0
        assert f.max_value == 100

    def test_select_field(self):
        f = SelectField(key="mode", label="Mode", options=["a", "b", "c"])
        assert f.field_type == "select"
        assert f.options == ["a", "b", "c"]

    def test_to_dict(self):
        f = TextField(key="name", label="Name")
        d = f.to_dict()
        assert d["key"] == "name"
        assert d["field_type"] == "text"


class TestCapabilities:
    def test_register_and_find(self):
        reg = CapabilityRegistry()
        reg.register("ext1", Capability("scanner", "subdomain"))
        reg.register("ext1", Capability("scanner", "port"))
        reg.register("ext2", Capability("notifier", "telegram"))

        assert reg.find("scanner") == ["ext1", "ext1"]
        assert reg.find("scanner", "subdomain") == ["ext1"]
        assert reg.find("notifier", "telegram") == ["ext2"]
        assert reg.find("scanner", "nonexistent") == []

    def test_who_can(self):
        reg = CapabilityRegistry()
        reg.register("ext1", Capability("scanner", "subdomain"))
        assert reg.who_can("scanner", "subdomain") == "ext1"
        assert reg.who_can("scanner", "missing") is None

    def test_has(self):
        reg = CapabilityRegistry()
        reg.register("ext1", Capability("ai", "gemini"))
        assert reg.has("ai", "gemini") is True
        assert reg.has("ai", "claude") is False

    def test_unregister(self):
        reg = CapabilityRegistry()
        reg.register("ext1", Capability("scanner", "subdomain"))
        reg.unregister("ext1")
        assert reg.find("scanner") == []

    def test_list_capabilities(self):
        reg = CapabilityRegistry()
        reg.register("ext1", Capability("scanner", "subdomain"))
        caps = reg.list_capabilities()
        assert any(c["domain"] == "scanner" and c["name"] == "subdomain" for c in caps)


class TestHookRegistry:
    def test_register_and_run(self):
        reg = HookRegistry()
        results = []

        def handler(**ctx):
            results.append(ctx["value"])
            return ctx["value"]

        reg.register_handler("before_scan", "test_ext", handler)
        out = reg.run("before_scan", value=42)
        assert out == [42]
        assert results == [42]

    def test_unknown_hook(self):
        reg = HookRegistry()
        ok = reg.register_handler("nonexistent", "ext", lambda: None)
        assert ok is False

    def test_multiple_handlers(self):
        reg = HookRegistry()
        calls = []

        def h1(**ctx):
            calls.append("h1")

        def h2(**ctx):
            calls.append("h2")

        reg.register_handler("after_startup", "ext1", h1)
        reg.register_handler("after_startup", "ext2", h2)
        reg.run("after_startup")
        assert calls == ["h1", "h2"]

    def test_short_circuit(self):
        reg = HookRegistry()
        calls = []

        def h1(**ctx):
            calls.append("h1")
            return False

        def h2(**ctx):
            calls.append("h2")

        reg.register_handler("before_scan", "ext1", h1)
        reg.register_handler("before_scan", "ext2", h2)
        reg.run("before_scan")
        assert calls == ["h1"]

    def test_handler_exception(self):
        reg = HookRegistry()
        calls = []

        def h1(**ctx):
            raise ValueError("boom")

        def h2(**ctx):
            calls.append("h2")

        reg.register_handler("after_startup", "ext1", h1)
        reg.register_handler("after_startup", "ext2", h2)
        reg.run("after_startup")
        assert calls == ["h2"]

    def test_unregister_extension(self):
        reg = HookRegistry()
        reg.register_handler("before_scan", "ext1", lambda **kw: 1)
        reg.unregister_extension("ext1")
        assert reg.get("before_scan").handler_count == 0

    def test_list_hooks(self):
        reg = HookRegistry()
        hooks = reg.list_hooks()
        assert len(hooks) > 0
        assert any(h["name"] == "before_scan" for h in hooks)

    def test_on_hook_decorator(self):
        reg = get_hook_registry()
        reg.unregister_extension("decorator_test")

        @on_hook("after_startup", extension_id="decorator_test")
        def decorated(**ctx: dict) -> str:
            return "decorated"

        result = reg.run("after_startup")
        assert "decorated" in result

        reg.unregister_extension("decorator_test")


class TestExtensionRegistry:
    def test_register_extension(self):
        reg = ExtensionRegistry()
        m = ExtensionManifest(
            id="test-ext",
            name="Test Extension",
            version="1.0.0",
            capabilities=[Capability("test", "mock")],
        )
        reg._extensions[m.id] = m
        assert reg.get("test-ext") is m
        assert reg.count == 1

    def test_load_and_unload(self):
        reg = ExtensionRegistry()
        m = ExtensionManifest(
            id="test-ext",
            name="Test Extension",
            version="1.0.0",
        )
        reg._extensions[m.id] = m
        ok = reg.load("test-ext")
        assert ok is True
        ok = reg.unload("test-ext")
        assert ok is True

    def test_load_nonexistent(self):
        reg = ExtensionRegistry()
        ok = reg.load("nonexistent")
        assert ok is False

    def test_status(self):
        reg = ExtensionRegistry()
        m = ExtensionManifest(id="test-ext", name="Test", version="1.0.0", capabilities=[Capability("x", "y")])
        reg._extensions[m.id] = m
        status = reg.status()
        assert "test-ext" in status
        assert status["test-ext"]["name"] == "Test"

    def test_get_errors_on_fresh(self):
        reg = ExtensionRegistry()
        assert reg.get_errors() == {}

    def test_discover_no_directory(self):
        reg = ExtensionRegistry()
        manifests = reg.discover()
        assert isinstance(manifests, dict)
