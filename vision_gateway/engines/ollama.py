"""Ollama Vision client — local multimodal inference via Ollama."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from vision_gateway.config import OLLAMA_URL

logger = logging.getLogger("vision_gateway.ollama")

ANALYSIS_PROMPT = """Analyze this image. Describe what you see including any text, UI elements, colors, and context."""


def _encode_image(image_path: str | Path) -> str:
    path = Path(image_path)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_image(
    image_path: str | Path,
    prompt: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Analyze an image using Ollama's local vision model."""
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    # If no specific model, try to find one
    if not model:
        model = _find_vision_model()
    if not model:
        return {"error": "No vision model available in Ollama. Run: ollama pull llava"}

    try:
        b64 = _encode_image(path)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt or ANALYSIS_PROMPT,
                    "images": [b64],
                }
            ],
            "stream": False,
        }

        req = Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

        with urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode())

        if "error" in result:
            return {"error": result["error"]}

        return {
            "text": result["message"]["content"],
            "model": model,
            "provider": "ollama",
        }

    except Exception as e:
        logger.exception("Ollama analysis failed")
        return {"error": str(e)}


def _find_vision_model() -> str | None:
    """Find the best available vision model in Ollama."""
    try:
        req = Request(f"{OLLAMA_URL}/api/tags")
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        models = [m["name"] for m in data.get("models", [])]
        # Prefer vision models
        vision_keywords = ["llava", "bakllava", "vision", "vlm", "cogvlm", "moondream"]
        for kw in vision_keywords:
            for m in models:
                if kw in m.lower():
                    return m
        return models[0] if models else None
    except Exception:
        return None


def list_models() -> list[dict[str, Any]]:
    """List available Ollama models."""
    try:
        req = Request(f"{OLLAMA_URL}/api/tags")
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return [
            {
                "name": m["name"],
                "size": m["size"],
                "modified": m.get("modified_at", ""),
            }
            for m in data.get("models", [])
        ]
    except Exception as e:
        return [{"error": str(e)}]
