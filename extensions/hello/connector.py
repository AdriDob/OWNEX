from __future__ import annotations

from core.interfaces.connector import ConnectorHealth, IConnector


class HelloConnector(IConnector):
    connector_id = "hello_greeter"
    app_id = "ownex"
    display_name = "Hello World Connector"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return [
            {"key": "greeting_text", "label": "Greeting", "type": "text", "default": "Hello, ORION!"},
        ]
