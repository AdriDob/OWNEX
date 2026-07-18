"""Vision Gateway — Local multimodal vision service for the ORION ecosystem.

A unified vision analysis gateway that provides:
  - REST API (FastAPI) for MERLIN, CATEYE agents
  - MCP server (stdio) for OpenCode integration
  - Multiple vision backends (OpenRouter, Ollama, PaddleOCR)

Usage:
    # Start REST API server
    python -m vision_gateway.server

    # Start MCP server (for OpenCode)
    python -m vision_gateway.server --mcp

    # CLI mode
    python -m vision_gateway describe image.png
    python -m vision_gateway ocr image.png
    python -m vision_gateway analyze image.png
"""

from __future__ import annotations

__version__ = "0.1.0"
