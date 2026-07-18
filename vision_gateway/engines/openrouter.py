"""OpenRouter Vision API client — multimodal image analysis via OpenRouter."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from vision_gateway.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

logger = logging.getLogger("vision_gateway.openrouter")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

ANALYSIS_PROMPT = """Analyze this image comprehensively. Describe:
1. What is shown (main subject, composition, context)
2. ALL visible text (transcribe exactly, preserve language)
3. Colors, visual style, design elements
4. Technical details (UI components, code, diagrams, charts)
5. Purpose and function of what's shown

Be precise and objective."""


def _encode_image(image_path: str | Path) -> str:
    path = Path(image_path)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _get_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }.get(ext, "image/png")


def analyze_image(
    image_path: str | Path,
    prompt: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Analyze an image using OpenRouter multimodal model."""
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY not configured"}

    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    try:
        b64 = _encode_image(path)
        mime = _get_mime(path)

        payload = {
            "model": model or OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt or ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
        }

        req = Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/AdriDob/Rastro",
            },
        )

        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        if "error" in result:
            return {"error": result["error"].get("message", str(result["error"]))}

        content = result["choices"][0]["message"]["content"]
        return {
            "text": content,
            "model": result.get("model", model or OPENROUTER_MODEL),
            "provider": "openrouter",
        }

    except Exception as e:
        logger.exception("OpenRouter analysis failed")
        return {"error": str(e)}
