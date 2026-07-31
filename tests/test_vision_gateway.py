"""Tests for Vision Gateway — OCR, Gemini, MCP server, CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


def _skip_if_external_api_down(result):
    """Skip when failure is an external outage (quota/network), not a code bug."""
    error = result.get("error", "") if isinstance(result, dict) else ""
    markers = ("quota", "Quota", "billing", "429", "RESOURCE_EXHAUSTED", "connection", "timed out")
    if any(m in error for m in markers):
        pytest.skip(f"External API unavailable: {error[:120]}")

# ── Fixtures ──────────────────────────────────────────────────────

HERE = Path(__file__).parent
VG = [sys.executable, "-m", "vision_gateway"]


@pytest.fixture(scope="session")
def test_image(tmp_path_factory):
    """Create a test image with known text."""
    img = Image.new("RGB", (800, 200), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "ORION Vision Gateway", fill=(0, 255, 100))
    draw.text((50, 120), "Rastro CATEYE v4.6.0", fill=(100, 200, 255))
    path = tmp_path_factory.mktemp("images") / "test.png"
    img.save(path)
    return path


@pytest.fixture(scope="session")
def test_image_spanish(tmp_path_factory):
    """Test image with Spanish text."""
    img = Image.new("RGB", (600, 150), color=(20, 20, 30))
    draw = ImageDraw.Draw(img)
    draw.text((30, 50), "Sistema de inteligencia operativa", fill=(0, 255, 0))
    draw.text((30, 100), "Bug Bounty Automation", fill=(200, 200, 200))
    path = tmp_path_factory.mktemp("images") / "spanish.png"
    img.save(path)
    return path


# ── CLI Tests ─────────────────────────────────────────────────────


def test_cli_help():
    result = subprocess.run([*VG, "--help"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "Vision Gateway v0.1.0" in result.stdout


def test_cli_metadata(test_image):
    result = subprocess.run([*VG, "metadata", str(test_image)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["width"] == 800
    assert data["height"] == 200
    assert data["format"] == "PNG"


def test_cli_metadata_not_found():
    result = subprocess.run([*VG, "metadata", "/nonexistent/image.png"], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "error" in data


def test_cli_unsupported_format(tmp_path):
    fake = tmp_path / "test.txt"
    fake.write_text("not an image")
    result = subprocess.run([*VG, "metadata", str(fake)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0


def test_cli_ocr_no_tesseract(test_image):
    """OCR should return a clear message if tesseract not installed."""
    result = subprocess.run([*VG, "ocr", str(test_image)], capture_output=True, text=True, timeout=10)
    # Without tesseract, should give clear message
    output = result.stdout.strip()
    assert result.returncode == 0
    assert output.startswith("[") or "ORION" in output or "Gateway" in output


# ── Gemini Engine Tests ───────────────────────────────────────────


def test_gemini_analyze(test_image):
    from vision_gateway.engines.gemini import analyze_image

    result = analyze_image(str(test_image))
    _skip_if_external_api_down(result)
    assert "error" not in result, result["error"]
    assert "text" in result
    assert "ORION" in result["text"]
    assert result["provider"] == "gemini"


@pytest.mark.skipif("GEMINI_API_KEY" not in __import__("os").environ, reason="No GEMINI_API_KEY")
def test_gemini_ocr_text(test_image):
    from vision_gateway.engines.gemini import extract_text

    result = extract_text(str(test_image))
    assert "error" not in result, result["error"]
    assert "ORION" in result["text"] or "Vision" in result["text"]


@pytest.mark.skipif("GEMINI_API_KEY" not in __import__("os").environ, reason="No GEMINI_API_KEY")
def test_gemini_spanish(test_image_spanish):
    from vision_gateway.engines.gemini import analyze_image

    result = analyze_image(str(test_image_spanish))
    _skip_if_external_api_down(result)
    assert "error" not in result, result["error"]
    assert "text" in result
    assert len(result["text"]) > 20


def test_gemini_no_key(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENERATIVE_AI_API_KEY", raising=False)
    # Force get_api_key to return None by patching the .env check
    import vision_gateway.engines.gemini as gemini_mod

    monkeypatch.setattr(gemini_mod, "get_api_key", lambda: None)
    from vision_gateway.engines.gemini import analyze_image, get_api_key

    key = get_api_key()
    assert key is None, f"Key should be None but found: {key[:8] if key else 'None'}..."

    img = tmp_path / "test.png"
    Image.new("RGB", (10, 10)).save(img)
    result = analyze_image(str(img))
    assert "error" in result
    assert "No Gemini API key found" in result["error"]


# ── Core analysis function ────────────────────────────────────────


def test_analyze_image_not_found():
    from vision_gateway.server import analyze_image

    result = analyze_image("/nonexistent.png")
    assert "error" in result


def test_analyze_image_unsupported(tmp_path):
    fake = tmp_path / "test.txt"
    fake.write_text("data")
    from vision_gateway.server import analyze_image

    result = analyze_image(str(fake))
    assert "error" in result


def test_analyze_image_success(test_image):
    from vision_gateway.server import analyze_image

    result = analyze_image(str(test_image))
    _skip_if_external_api_down(result)
    assert "error" not in result, result.get("error", "")
    assert "text" in result
    # Can be "gemini" or "ocr" depending on fallback
    assert result.get("provider") in ("gemini", "ocr")


def test_analyze_image_with_prompt(test_image):
    from vision_gateway.server import analyze_image

    result = analyze_image(str(test_image), prompt="What colors are used?")
    assert "error" not in result, result.get("error", "")
    assert "text" in result


# ── MCP Server Tests ──────────────────────────────────────────────


def _mcp_call(args: list[str], stdin_data: str, timeout: int = 15) -> dict:
    proc = subprocess.Popen(
        [*VG, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    proc.stdin.write(stdin_data)
    proc.stdin.flush()
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"error": "timeout", "stderr": proc.stderr.read()}
    if "Content-Length:" not in out:
        return {"error": f"No Content-Length in response. stderr: {err[:500]}", "raw": out[:500]}
    # Split on double CRLF or double LF
    delim = "\r\n\r\n" if "\r\n\r\n" in out else "\n\n"
    parts = out.split(delim, 1)
    if len(parts) < 2:
        return {"error": "Malformed MCP response", "raw": out[:500]}
    try:
        return json.loads(parts[1])
    except json.JSONDecodeError as e:
        return {"error": str(e), "raw": parts[1][:500]}


def test_mcp_initialize():
    msg = json.dumps({"id": 1, "method": "initialize", "params": {}})
    header = f"Content-Length: {len(msg)}\r\n\r\n{msg}"
    result = _mcp_call(["--mcp"], header)
    assert "error" not in result, result
    assert result["result"]["serverInfo"]["name"] == "vision-gateway"


def test_mcp_list_tools():
    msg = json.dumps({"id": 2, "method": "list_tools", "params": {}})
    header = f"Content-Length: {len(msg)}\r\n\r\n{msg}"
    result = _mcp_call(["--mcp"], header)
    assert "error" not in result, result
    tools = result["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "describe_image" in names
    assert "ocr_image" in names
    assert "analyze_image" in names
    assert "extract_pdf_text" in names
    assert "image_metadata" in names


def test_mcp_describe_image(test_image):
    msg = json.dumps(
        {
            "id": 3,
            "method": "call_tool",
            "params": {"name": "describe_image", "arguments": {"path": str(test_image)}},
        }
    )
    header = f"Content-Length: {len(msg)}\r\n\r\n{msg}"
    result = _mcp_call(["--mcp"], header)
    assert "error" not in result, result
    content = result["result"]["content"][0]["text"]
    data = json.loads(content)
    _skip_if_external_api_down(data)
    assert "text" in data
    assert "ORION" in data["text"]


def test_mcp_image_metadata(test_image):
    msg = json.dumps(
        {
            "id": 4,
            "method": "call_tool",
            "params": {"name": "image_metadata", "arguments": {"path": str(test_image)}},
        }
    )
    header = f"Content-Length: {len(msg)}\r\n\r\n{msg}"
    result = _mcp_call(["--mcp"], header)
    assert "error" not in result, result
    content = json.loads(result["result"]["content"][0]["text"])
    assert content["width"] == 800
    assert content["height"] == 200


# ── Config Tests ──────────────────────────────────────────────────


def test_supported_extensions():
    from vision_gateway.config import SUPPORTED_EXTENSIONS, SUPPORTED_MIMETYPES

    assert ".png" in SUPPORTED_EXTENSIONS
    assert ".jpg" in SUPPORTED_EXTENSIONS
    assert "image/png" in SUPPORTED_MIMETYPES
    assert "image/jpeg" in SUPPORTED_MIMETYPES


def test_config_defaults():
    from vision_gateway.config import HOST, MAX_FILE_SIZE, PORT

    assert HOST == "127.0.0.1"
    assert isinstance(PORT, int)
    assert MAX_FILE_SIZE > 0
