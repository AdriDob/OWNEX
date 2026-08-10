# Extension SDK — Building ORION Extensions

## Architecture

Extensions live in `extensions/<name>/` and are auto-discovered on startup.
Each extension declares a `manifest.py` that defines its capabilities,
hooks, settings, and dependencies.

```
extensions/
├── my_extension/
│   ├── manifest.py        # Required — declares the extension
│   ├── hooks.py           # Hook handlers
│   ├── settings.py        # (optional) Default values
│   └── __init__.py        # (optional) Init logic
└── another_ext/
    └── manifest.py
```

## Minimal Extension

```python
# extensions/hello/manifest.py
from core.extension import (
    ExtensionManifest,
    TextField,
    Capability,
)

manifest = ExtensionManifest(
    id="hello",
    name="Hello World",
    version="1.0.0",
    description="A minimal example extension",
    author="You",
    capabilities=[Capability("example", "greeting")],
    settings=[
        TextField(key="greeting", label="Greeting Text", default="Hello, ORION!"),
    ],
)
```

## Hook Points

Hooks are synchronous callbacks that run at specific lifecycle points.

```python
# extensions/my_ext/hooks.py
from core.extension.hooks import on_hook


@on_hook("before_scan")
def warn_before_scan(target_id, scan_type):
    print(f"About to scan {target_id} with {scan_type}")
    # Return False to cancel the operation
    return True


@on_hook("after_report")
def log_after_report(report_id):
    print(f"Report {report_id} generated")
```

### Available Hook Points

| Hook | Context | Description |
|---|---|---|
| `before_scan` | target_id, scan_type | Before a scan starts |
| `after_scan` | target_id, findings_count | After a scan completes |
| `before_hypothesis` | target_id, evidence | Before hypothesis generation |
| `after_hypothesis` | hypothesis | After hypothesis generated |
| `before_report` | finding_ids | Before report generation |
| `after_report` | report_id | After report generated |
| `before_publish` | report_id | Before publishing |
| `after_publish` | report_id, response | After publishing |
| `before_ai_reasoning` | prompt, tools | Before AI agent reasons |
| `after_ai_reasoning` | response, tokens_used | After AI agent reasons |
| `before_publish_event` | event, data | Before EventBus publish |
| `after_publish_event` | event, data | After EventBus publish |
| `before_shutdown` | reason | Before system shutdown |
| `after_startup` | apps_count | After system startup |

## Capabilities

Extensions declare what they can do via `Capability` objects.

```python
Capability(domain="scanner", name="subdomain")
Capability(domain="ai_model", name="gemini")
Capability(domain="exporter", name="pdf")
Capability(domain="connector", name="binance")
Capability(domain="widget", name="portfolio-value")
Capability(domain="notification", name="telegram")
```

Other extensions can query capabilities:

```python
from core.extension.capabilities import get_capability_registry

reg = get_capability_registry()
who = reg.who_can("scanner", "subdomain")
# Returns extension ID or None
```

## Declarative Settings

Settings fields auto-generate a settings UI in the frontend.

```python
from core.extension import (
    TextField,
    ApiKeyField,
    SwitchField,
    NumberField,
    SelectField,
)

settings = [
    TextField(key="server_url", label="Server URL", placeholder="https://..."),
    ApiKeyField(key="api_key", label="API Key", required=True),
    SwitchField(key="enabled", label="Enable Feature", default=True),
    NumberField(key="timeout", label="Timeout (seconds)", default=30, min_value=1, max_value=300),
    SelectField(key="mode", label="Mode", options=["fast", "balanced", "deep"], default="balanced"),
]
```

## Dependencies

Extensions can declare dependencies on other apps or capabilities:

```python
manifest = ExtensionManifest(
    id="advanced-scanner",
    name="Advanced Scanner",
    ...
    dependencies=[
        "scanner:subdomain",    # Requires a subdomain scanner capability
        "hermes",               # Requires the Hermes app to be loaded
    ],
)
```

The system will refuse to load an extension with unmet dependencies.

## Scheduler Jobs

Extensions can register periodic jobs:

```python
manifest = ExtensionManifest(
    id="health-reporter",
    ...
    scheduler_jobs=[
        {
            "job_id": "health_report",
            "app_id": "health-reporter",
            "handler": "hooks.generate_report",
            "trigger": "interval",
            "seconds": 3600,  # Every hour
        },
    ],
)
```

## Error Isolation

If an extension's hook handler raises an exception:
- The exception is logged
- The hook chain continues to the next handler
- The extension is NOT unloaded
- The system continues normally

If an extension's `manifest.py` fails to load:
- The extension is skipped
- The error is recorded in `ExtensionRegistry.get_errors()`
- The system continues normally

## Testing

```python
# tests/test_extensions.py
from core.extension.registry import get_extension_registry


def test_extension_discovery():
    registry = get_extension_registry()
    manifests = registry.discover()
    assert len(manifests) >= 0  # May be empty
```
