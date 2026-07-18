"""Vision Gateway — FastAPI REST API + MCP Server + CLI.

Single entry point serving three interfaces:
  1. REST API (FastAPI) — for MERLIN, CATEYE agents, dashboard
  2. MCP Server (stdio JSON-RPC) — for OpenCode integration
  3. CLI — direct commands for scripts and terminal
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from vision_gateway import __version__
from vision_gateway.config import (
    HOST,
    MAX_FILE_SIZE,
    PORT,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_MIMETYPES,
)
from vision_gateway.engines import ollama
from vision_gateway.engines.gemini import analyze_image as gemini_analyze
from vision_gateway.engines.openrouter import analyze_image as or_analyze
from vision_gateway.ocr import extract_text, extract_text_from_pdf, get_image_metadata

logger = logging.getLogger("vision_gateway")

# ── Core analysis function ────────────────────────────────────────

ENGINE_PREFERENCE = ["gemini", "openrouter", "ollama", "ocr"]


def analyze_image(
    image_path: str | Path,
    prompt: str | None = None,
    engine: str | None = None,
) -> dict[str, Any]:
    """Analyze an image using the best available engine.

    Tries engines in priority order: OpenRouter → Ollama → OCR-only.
    """
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return {"error": f"Unsupported format: {path.suffix}. Supported: {SUPPORTED_EXTENSIONS}"}

    engines_to_try = [engine] if engine else ENGINE_PREFERENCE

    for eng in engines_to_try:
        if eng == "gemini":
            result = gemini_analyze(path, prompt)
            if "error" not in result:
                return result
            logger.info("Gemini unavailable (%s), trying next engine", result["error"])
        elif eng == "openrouter":
            result = or_analyze(path, prompt)
            if "error" not in result:
                return result
            logger.info("OpenRouter unavailable (%s), trying next engine", result["error"])
        elif eng == "ollama":
            result = ollama.analyze_image(path, prompt)
            if "error" not in result:
                return result
            logger.info("Ollama unavailable (%s), trying next engine", result["error"])
        elif eng == "ocr":
            text = extract_text(path)
            meta = get_image_metadata(path)
            return {
                "text": text,
                "metadata": meta,
                "provider": "ocr",
                "note": "OCR-only mode — no LLM analysis available",
            }

    return {"error": "No vision engine available. Configure OPENROUTER_API_KEY or install Ollama vision model."}


# ── MCP Server (JSON-RPC stdio transport) ────────────────────────

MCP_TOOLS = [
    {
        "name": "describe_image",
        "description": "Describe an image file comprehensively (content, text, UI elements, colors)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the image file"},
                "prompt": {"type": "string", "description": "Optional custom prompt"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "ocr_image",
        "description": "Extract all text from an image using OCR",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the image file"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "analyze_image",
        "description": "Full analysis: describe + extract text + metadata",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the image file"},
                "prompt": {"type": "string", "description": "Optional custom analysis prompt"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "extract_pdf_text",
        "description": "Extract text from a PDF using OCR (page by page)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the PDF file"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "image_metadata",
        "description": "Get image metadata (dimensions, format, size, mode)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the image file"},
            },
            "required": ["path"],
        },
    },
]


def _mcp_respond(data: dict[str, Any]) -> None:
    msg = json.dumps(data)
    sys.stdout.write(f"Content-Length: {len(msg)}\r\n\r\n{msg}")
    sys.stdout.flush()


def run_mcp_server() -> None:
    """Run MCP server over stdio transport."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")

    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        if line.startswith("Content-Length:"):
            length = int(line.split(":")[1].strip())
            # Read empty line
            sys.stdin.readline()
            body = sys.stdin.read(length)
        else:
            body = line

        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            continue

        req_id = msg.get("id")
        method = msg.get("method")

        if method == "initialize":
            _mcp_respond(
                {
                    "id": req_id,
                    "result": {
                        "protocolVersion": "0.1.0",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "vision-gateway", "version": __version__},
                    },
                }
            )
        elif method == "list_tools":
            _mcp_respond({"id": req_id, "result": {"tools": MCP_TOOLS}})
        elif method == "call_tool":
            params = msg.get("params", {})
            name = params.get("name", "")
            args = params.get("arguments", {})
            result = _handle_mcp_tool(name, args)
            _mcp_respond(
                {"id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
            )
        elif method == "notifications/initialized":
            pass  # No response needed
        else:
            _mcp_respond({"id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})


def _handle_mcp_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", "")
    prompt = args.get("prompt")

    if name == "describe_image":
        return gemini_analyze(path, prompt or "Describe this image comprehensively.")
    elif name == "ocr_image":
        text = extract_text(path)
        return {"text": text}
    elif name == "analyze_image":
        return analyze_image(path, prompt)
    elif name == "extract_pdf_text":
        text = extract_text_from_pdf(path)
        return {"text": text}
    elif name == "image_metadata":
        return get_image_metadata(path)
    return {"error": f"Unknown tool: {name}"}


# ── CLI ──────────────────────────────────────────────────────────


def cli() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=f"Vision Gateway v{__version__}")
    parser.add_argument("--mcp", action="store_true", help="Run MCP server (stdio)")
    parser.add_argument("--api", action="store_true", help="Run REST API server")
    parser.add_argument("--host", default=HOST, help=f"Bind address (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    sub = parser.add_subparsers(dest="command")

    desc = sub.add_parser("describe", help="Describe an image")
    desc.add_argument("image", help="Path to image file")
    desc.add_argument("prompt", nargs="?", help="Optional custom prompt")

    ocr_p = sub.add_parser("ocr", help="OCR an image")
    ocr_p.add_argument("image", help="Path to image file")

    analyze = sub.add_parser("analyze", help="Full image analysis")
    analyze.add_argument("image", help="Path to image file")
    analyze.add_argument("prompt", nargs="?", help="Optional custom prompt")

    pdf = sub.add_parser("pdf", help="OCR a PDF")
    pdf.add_argument("file", help="Path to PDF file")

    meta = sub.add_parser("metadata", help="Get image metadata")
    meta.add_argument("image", help="Path to image file")

    models = sub.add_parser("models", help="List available Ollama vision models")

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")

    if args.mcp:
        run_mcp_server()
        return 0
    elif args.api:
        _run_api(args.host, args.port)
        return 0
    elif args.command == "describe":
        result = analyze_image(args.image, args.prompt)
        _print_result(result)
        return 0
    elif args.command == "ocr":
        text = extract_text(args.image)
        print(text)
        return 0
    elif args.command == "analyze":
        result = analyze_image(args.image, args.prompt)
        _print_result(result)
        return 0
    elif args.command == "pdf":
        text = extract_text_from_pdf(args.file)
        print(text)
        return 0
    elif args.command == "metadata":
        result = get_image_metadata(args.image)
        print(json.dumps(result, indent=2))
        return 0
    elif args.command == "models":
        models = ollama.list_models()
        for m in models:
            print(f"  {m.get('name', '?')}  ({m.get('size', 0) / 1e9:.1f}GB)")
        return 0
    else:
        parser.print_help()
        return 1


def _print_result(result: dict[str, Any]) -> None:
    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
    elif "text" in result:
        print(result["text"])
    else:
        print(json.dumps(result, indent=2))


def _run_api(host: str, port: int) -> None:
    """Start FastAPI REST API server."""
    try:
        from fastapi import FastAPI, File, HTTPException, UploadFile
        from fastapi.responses import JSONResponse

        app = FastAPI(title="Vision Gateway", version=__version__)

        @app.get("/health")
        def health():
            return {"status": "ok", "version": __version__}

        @app.post("/api/vision/analyze")
        async def api_analyze(file: UploadFile = File(...), prompt: str | None = None):
            if file.content_type and file.content_type not in SUPPORTED_MIMETYPES:
                raise HTTPException(400, f"Unsupported media type: {file.content_type}")
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(400, f"File too large: {len(content)} > {MAX_FILE_SIZE}")
            tmp = Path("/tmp") / f"vg_{int(time.time())}_{file.filename or 'image'}"
            tmp.write_bytes(content)
            try:
                result = analyze_image(str(tmp), prompt)
                return JSONResponse(result)
            finally:
                tmp.unlink(missing_ok=True)

        @app.post("/api/vision/ocr")
        async def api_ocr(file: UploadFile = File(...)):
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(400, f"File too large: {len(content)} > {MAX_FILE_SIZE}")
            tmp = Path("/tmp") / f"vg_{int(time.time())}_{file.filename or 'image'}"
            tmp.write_bytes(content)
            try:
                text = extract_text(str(tmp))
                return {"text": text}
            finally:
                tmp.unlink(missing_ok=True)

        @app.post("/api/vision/pdf")
        async def api_pdf(file: UploadFile = File(...)):
            content = await file.read()
            tmp = Path("/tmp") / f"vg_{int(time.time())}_{file.filename or 'doc'}"
            tmp.write_bytes(content)
            try:
                text = extract_text_from_pdf(str(tmp))
                return {"text": text}
            finally:
                tmp.unlink(missing_ok=True)

        import uvicorn

        uvicorn.run(app, host=host, port=port)

    except ImportError as e:
        logger.error("REST API requires FastAPI/uvicorn: %s", e)
        print("Install: pip install fastapi uvicorn")

    except Exception as e:
        logger.exception("API server failed")
        print(f"Server error: {e}")


if __name__ == "__main__":
    sys.exit(cli())
