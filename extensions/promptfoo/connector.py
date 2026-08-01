from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from core.interfaces.connector import ConnectorHealth, IConnector

logger = logging.getLogger("ownex.promptfoo.connector")

_PROMPTFOO_AVAILABLE = importlib.util.find_spec("promptfoo") is not None


class PromptFooConnector(IConnector):
    """Connector to PromptFoo LLM evaluation platform.

    Automates prompt testing, regression detection, and red-teaming
    for every agent prompt in OWNEX. Runs as part of the CI/eval
    pipeline to ensure quality regressions are caught immediately.
    """

    connector_id = "promptfoo_evaluator"
    app_id = "ownex"
    display_name = "PromptFoo Eval"

    def __init__(self) -> None:
        self._connected = False

    async def connect(self) -> bool:
        if not _PROMPTFOO_AVAILABLE:
            logger.warning("promptfoo not installed")
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def health(self) -> ConnectorHealth:
        return ConnectorHealth(connected=self._connected)

    def get_config_fields(self) -> list[dict]:
        return []

    async def evaluate_prompt(
        self,
        prompt: str,
        provider: str = "openai:gpt-4o-mini",
        tests: list[dict] | None = None,
    ) -> dict:
        """Evaluate a single prompt against test cases."""
        if not _PROMPTFOO_AVAILABLE:
            return {"error": "promptfoo not installed"}
        try:
            config = {
                "prompts": [prompt],
                "providers": [provider],
                "tests": tests or [{"assert": [{"type": "contains-any", "value": ["yes"]}]}],
            }
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                dir=os.environ.get("OWNEX_TMP_DIR", tempfile.gettempdir()),
            ) as f:
                json.dump(config, f)
                config_path = f.name

            result = subprocess.run(
                ["npx", "promptfoo", "eval", "--config", config_path, "--output", "eval_results.json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            Path(config_path).unlink(missing_ok=True)

            # Parse results
            output_path = Path("eval_results.json")
            if output_path.exists():
                data = json.loads(output_path.read_text())
                output_path.unlink(missing_ok=True)
                return {"status": "ok", "results": data}
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500],
            }
        except subprocess.TimeoutExpired:
            return {"error": "eval timed out"}
        except Exception as exc:
            logger.error("PromptFoo eval failed: %s", exc)
            return {"error": str(exc)}

    async def run_test_suite(self, config_path: str) -> dict:
        """Run a full PromptFoo test suite from a configuration file."""
        if not _PROMPTFOO_AVAILABLE:
            return {"error": "promptfoo not installed"}
        try:
            result = subprocess.run(
                ["npx", "promptfoo", "eval", "--config", config_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:500],
            }
        except subprocess.TimeoutExpired:
            return {"error": "eval timed out"}
        except Exception as exc:
            logger.error("PromptFoo suite run failed: %s", exc)
            return {"error": str(exc)}


async def on_evaluate_prompt(event: object) -> None:
    if not _PROMPTFOO_AVAILABLE:
        return
    connector = PromptFooConnector()
    await connector.connect()
    prompt = getattr(event, "prompt", "") or getattr(event, "data", "")
    if prompt:
        result = await connector.evaluate_prompt(prompt)
        if result and hasattr(event, "set_result"):
            event.set_result(result)


async def on_eval_run(event: object) -> None:
    if not _PROMPTFOO_AVAILABLE:
        return
    connector = PromptFooConnector()
    await connector.connect()
    config = getattr(event, "config", "")
    if config:
        result = await connector.run_test_suite(config)
        if result and hasattr(event, "set_result"):
            event.set_result(result)
