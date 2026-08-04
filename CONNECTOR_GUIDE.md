# Connector Guide — Integrating External Services

## Overview

Connectors bridge ORION with external platforms (exchanges, scanners,
notification services, AI models). A connector is simply an extension
that declares a `Capability(domain="connector", name="<service>")`.

## Creating a Connector

```python
# extensions/binance_connector/manifest.py
from core.extension import (
    ExtensionManifest,
    Capability,
    ApiKeyField,
    SwitchField,
)

manifest = ExtensionManifest(
    id="binance-connector",
    name="Binance Connector",
    version="1.0.0",
    capabilities=[Capability("connector", "binance", "Binance exchange integration")],
    settings=[
        ApiKeyField(key="BINANCE_API_KEY", label="API Key", required=True),
        ApiKeyField(key="BINANCE_SECRET_KEY", label="Secret Key", required=True),
        SwitchField(key="testnet", label="Use Testnet", default=True),
    ],
    scheduler_jobs=[
        {
            "job_id": "sync_balances",
            "app_id": "binance-connector",
            "handler": "hooks.sync_balances",
            "trigger": "interval",
            "seconds": 300,
        },
    ],
)
```

```python
# extensions/binance_connector/hooks.py
from core.secrets.manager import get_secrets_manager


def sync_balances():
    secrets = get_secrets_manager()
    api_key = secrets.get("BINANCE_API_KEY")
    secret_key = secrets.get("BINANCE_SECRET_KEY")
    if not api_key or not secret_key:
        return {"error": "API keys not configured"}
    # ... sync logic ...
    return {"status": "ok", "balances": [...]}
```

## Using Secrets in a Connector

Never hardcode API keys. Always use the Secrets Manager:

```python
from core.secrets.manager import get_secrets_manager

sm = get_secrets_manager()

# With fallback
api_key = sm.get("MY_API_KEY", default="")

# Raise if missing
try:
    api_key = sm.get_or_raise("MY_API_KEY")
except KeyError:
    # Handle missing key
    pass

# Store programmatically
sm.set("MY_API_KEY", "actual-key-value")
```

## Supported Connector Types

| Domain | Description | Examples |
|---|---|---|
| `connector:exchange` | Cryptocurrency exchanges | binance, coinbase, kraken |
| `connector:scanner` | External security scanners | nuclei, zap, custom |
| `connector:notifier` | Notification channels | telegram, slack, email |
| `connector:ai` | External AI models | gemini, claude, local |
| `connector:storage` | External storage | s3, ipfs, local |
| `connector:publisher` | Bug bounty platforms | hackerone, bugcrowd |

## Best Practices

1. **Always use Secrets Manager** — Never read env vars directly
2. **Declare all settings** — Users configure via Settings UI
3. **Handle disconnection gracefully** — Log warnings, don't crash
4. **Rate limit yourself** — Don't rely on external rate limiting
5. **Test with testnet/sandbox first** — Use a SwitchField for this
