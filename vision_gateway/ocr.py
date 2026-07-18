"""OCR pipeline — pytesseract (lightweight) with clear fallback messaging.

Requires tesseract-ocr binary installed on the system:
  Ubuntu/Debian: sudo apt install tesseract-ocr
  macOS: brew install tesseract
  Windows: download from https://github.com/UB-Mannheim/tesseract/wiki
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image

logger = logging.getLogger("vision_gateway.ocr")

_HAS_TESSERACT: bool | None = None
_HAS_PDF2IMAGE: bool | None = None


def _check_tesseract() -> bool:
    global _HAS_TESSERACT
    if _HAS_TESSERACT is not None:
        return _HAS_TESSERACT
    _HAS_TESSERACT = shutil.which("tesseract") is not None
    if not _HAS_TESSERACT:
        logger.warning("tesseract binary not found. Install: sudo apt install tesseract-ocr")
    return _HAS_TESSERACT


def _check_pdf2image() -> bool:
    global _HAS_PDF2IMAGE
    if _HAS_PDF2IMAGE is not None:
        return _HAS_PDF2IMAGE
    try:
        import pdf2image  # noqa: F401

        _HAS_PDF2IMAGE = True
    except ImportError:
        _HAS_PDF2IMAGE = False
        logger.warning("pdf2image not installed. pip install pdf2image")
    return _HAS_PDF2IMAGE


def extract_text(image_path: str | Path) -> str:
    """Extract all text from an image using Tesseract OCR."""
    if not _check_tesseract():
        return "[Tesseract OCR not available. Install: sudo apt install tesseract-ocr]"

    path = Path(image_path)
    if not path.exists():
        return f"[File not found: {path}]"

    try:
        import pytesseract

        with Image.open(path) as img:
            text = pytesseract.image_to_string(img)
        return text.strip() or "[No text detected]"
    except Exception as e:
        logger.exception("OCR failed for %s", path)
        return f"[OCR error: {e}]"


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract text from PDF by converting pages to images and running OCR."""
    if not _check_tesseract():
        return "[Tesseract not available]"
    if not _check_pdf2image():
        return "[pdf2image not available. Install: pip install pdf2image]"

    path = Path(pdf_path)
    if not path.exists():
        return f"[File not found: {path}]"

    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(path), dpi=200)
    except Exception as e:
        logger.exception("PDF conversion failed for %s", path)
        return f"[PDF conversion error: {e}]"

    import pytesseract

    texts = []
    for i, img in enumerate(images):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            with Image.open(f.name) as fi:
                text = pytesseract.image_to_string(fi).strip()
            Path(f.name).unlink(missing_ok=True)
            if text:
                texts.append(f"--- Page {i + 1} ---\n{text}")

    return "\n\n".join(texts) if texts else "[No text detected in PDF]"


def get_image_metadata(image_path: str | Path) -> dict[str, Any]:
    """Extract image metadata."""
    path = Path(image_path)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    try:
        with Image.open(path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": path.stat().st_size,
            }
    except Exception as e:
        return {"error": str(e)}
