"""Minimal ORION extension — Hello World."""

from core.extension import (
    Capability,
    ExtensionManifest,
    SwitchField,
    TextField,
)

manifest = ExtensionManifest(
    id="hello",
    name="Hello World",
    version="1.0.0",
    description="Minimal example extension for ORION Platform",
    author="ORION Team",
    capabilities=[
        Capability("example", "greeting", "Greets the user on startup"),
    ],
    hooks={
        "after_startup": "hooks.on_startup",
    },
    settings=[
        TextField(key="greeting_text", label="Greeting", default="Hello, ORION!"),
        SwitchField(key="verbose", label="Verbose logging", default=False),
    ],
    hot_reloadable=True,
)
