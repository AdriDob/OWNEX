"""Vision Gateway configuration."""

from __future__ import annotations

import os
from pathlib import Path

# ── Server ────────────────────────────────────────────────────────
HOST = os.getenv("VISION_GATEWAY_HOST", "127.0.0.1")
PORT = int(os.getenv("VISION_GATEWAY_PORT", "8765"))

# ── OpenRouter ────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("VISION_OPENROUTER_MODEL", "google/gemini-2.5-flash")

# ── Ollama ────────────────────────────────────────────────────────
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("VISION_OLLAMA_MODEL", "")

# ── Google Gemini ─────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ── OCR ───────────────────────────────────────────────────────────
OCR_ENGINE = os.getenv("VISION_OCR_ENGINE", "paddle")  # paddle | easyocr | tesseract

# ── Cache ─────────────────────────────────────────────────────────
CACHE_DIR = Path(os.getenv("VISION_CACHE_DIR", str(Path.home() / ".orion" / "vision_cache")))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL = int(os.getenv("VISION_CACHE_TTL", "3600"))  # 1 hour

# ── Supported formats ─────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".svg"}
SUPPORTED_MIMETYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/svg+xml",
}

MAX_FILE_SIZE = int(os.getenv("VISION_MAX_FILE_SIZE", str(20 * 1024 * 1024)))  # 20MB
