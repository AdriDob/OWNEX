"""Google Gemini Vision API client — primary vision engine for Vision Gateway.

Uses Gemini 2.5 Flash (free tier, 1,500 requests/day, no credit card).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from vision_gateway.config import GOOGLE_API_KEY

logger = logging.getLogger("vision_gateway.gemini")

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

DESCRIBE_PROMPT = """Describe this image comprehensively. Include:
1. Main subject and composition
2. ALL visible text (transcribe exactly, preserve original language)
3. Colors, lighting, visual style, design elements
4. Technical details (UI components, code, diagrams, charts)
5. Context and purpose (UI screenshot, photo, diagram, document, etc.)

Be precise and objective."""

OCR_PROMPT = """Extract ALL text from this image EXACTLY as it appears.
Preserve the original language, capitalization, line breaks, and formatting.
Return ONLY the extracted text with no commentary."""


def get_api_key() -> str | None:
    if GOOGLE_API_KEY:
        return GOOGLE_API_KEY
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"):
        val = os.environ.get(var)
        if val:
            return val
    # Check .env files
    for env_file in (
        Path.home() / ".config" / "opencode" / ".env",
        Path.home() / ".env",
        Path.cwd() / ".env",
    ):
        if not env_file.exists():
            continue
        try:
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"):
                    logger.info("Found API key in %s", env_file)
                    return v
        except Exception:
            continue
    return None


def _encode_image(image_path: str | Path) -> tuple[str, str]:
    path = Path(image_path)
    b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    ext = path.suffix.lower()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".gif": "image/gif",
    }.get(ext, "image/png")
    return b64, mime


def _call_gemini(prompt: str, image_path: str | Path) -> dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        return {"error": "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in env/.env"}

    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    try:
        b64, mime = _encode_image(path)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": b64}},
                    ]
                }
            ],
            "safetySettings": [
                {"category": c, "threshold": "BLOCK_NONE"}
                for c in [
                    "HARM_CATEGORY_HARASSMENT",
                    "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "HARM_CATEGORY_DANGEROUS_CONTENT",
                ]
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192,
            },
        }

        req = Request(
            f"{GEMINI_URL}?key={api_key}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        if "error" in result:
            return {"error": result["error"].get("message", str(result["error"]))}

        candidates = result.get("candidates", [])
        if not candidates:
            return {"error": "No response from Gemini (content blocked?)"}

        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {
            "text": text,
            "model": GEMINI_MODEL,
            "provider": "gemini",
        }

    except HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return {"error": f"Gemini API error: {msg}"}

    except Exception as e:
        logger.exception("Gemini call failed")
        return {"error": str(e)}


def analyze_image(image_path: str | Path, prompt: str | None = None) -> dict[str, Any]:
    """Describe an image with Gemini Vision."""
    return _call_gemini(prompt or DESCRIBE_PROMPT, image_path)


def extract_text(image_path: str | Path) -> dict[str, Any]:
    """Extract text from an image."""
    return _call_gemini(OCR_PROMPT, image_path)
