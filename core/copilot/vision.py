from __future__ import annotations

import base64
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.vision")

_HAS_CV2 = False
_HAS_PYTESSERACT = False
_HAS_TESSERACT = False

try:
    import cv2 as _cv2

    _HAS_CV2 = True
except ImportError:
    _cv2 = None

try:
    import pytesseract

    _HAS_PYTESSERACT = True
    try:
        pytesseract.get_tesseract_version()
        _HAS_TESSERACT = True
    except Exception:
        _HAS_TESSERACT = False
except ImportError:
    pytesseract = None


def _get_image(image_source: str | Path | bytes) -> Any | None:
    if _cv2 is None:
        return None
    if isinstance(image_source, bytes):
        import numpy as np

        arr = np.frombuffer(image_source, dtype=np.uint8)
        return _cv2.imdecode(arr, _cv2.IMREAD_COLOR)
    else:
        path = Path(image_source)
        if not path.exists():
            return None
        return _cv2.imread(str(path))


def analyze_image(image_path: str | Path) -> dict[str, Any]:
    """Full image analysis: metadata, OCR, layout, color, edge detection.

    Gracefully degrades when dependencies are missing.
    """
    path = Path(image_path)
    result: dict[str, Any] = {
        "file": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "format": path.suffix.lower(),
        "ocr": {"text": "", "confidence": 0.0},
        "dimensions": None,
        "color_stats": None,
        "edge_density": None,
        "face_count": 0,
        "vision_analysis": None,
    }

    if not result["exists"]:
        return result

    img = _get_image(image_path)
    if img is None:
        return result

    h, w = img.shape[:2]
    result["dimensions"] = {"width": w, "height": h, "aspect_ratio": round(w / h, 3) if h > 0 else 0}

    result["color_stats"] = _analyze_colors(img)

    result["edge_density"] = _edge_density(img)

    result["face_count"] = _detect_faces(img)

    result["ocr"] = _do_ocr(img)

    result["vision_analysis"] = _ollama_vision(str(path))

    return result


def _analyze_colors(img: Any) -> dict[str, Any]:
    if _cv2 is None:
        return {"error": "OpenCV not available"}
    try:
        gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
        hsv = _cv2.cvtColor(img, _cv2.COLOR_BGR2HSV)
        return {
            "mean_brightness": round(float(gray.mean()), 1),
            "std_brightness": round(float(gray.std()), 1),
            "mean_saturation": round(float(hsv[:, :, 1].mean()), 1),
            "is_dark": float(gray.mean()) < 80,
            "is_high_contrast": float(gray.std()) > 60,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _edge_density(img: Any) -> float:
    if _cv2 is None:
        return 0.0
    try:
        gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
        edges = _cv2.Canny(gray, 50, 150)
        return round(float(edges.mean()) / 255.0, 3)
    except Exception:
        return 0.0


def _detect_faces(img: Any) -> int:
    if _cv2 is None:
        return 0
    try:
        gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
        # Use OpenCV's built-in Haar cascade
        cascade = _cv2.CascadeClassifier(_cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, 1.1, 5)
        return len(faces)
    except Exception:
        return 0


def _do_ocr(img: Any) -> dict[str, Any]:
    if not _HAS_TESSERACT:
        return {"text": "", "confidence": 0.0, "error": "tesseract binary not installed"}
    try:
        text = pytesseract.image_to_string(img, lang="spa+eng")
        data = pytesseract.image_to_data(img, lang="spa+eng", output_type=pytesseract.Output.DICT)
        confs = [c for c in data.get("conf", []) if isinstance(c, (int, float)) and c > 0]
        avg_conf = round(sum(confs) / len(confs), 1) if confs else 0.0
        return {"text": text.strip(), "confidence": avg_conf, "word_count": len(text.split())}
    except Exception as exc:
        return {"text": "", "confidence": 0.0, "error": str(exc)}


def _ollama_vision(image_path: str, model: str = "moondream") -> dict[str, Any] | None:
    """Analyze image via Ollama vision model (moondream, llava, etc.)."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if model not in result.stdout:
            return {"available": False, "error": f"model '{model}' not pulled", "hint": f"run: ollama pull {model}"}

        import base64 as b64

        with open(image_path, "rb") as f:
            b64_img = b64.b64encode(f.read()).decode()

        prompt = "Describe this image in detail. What do you see? If there is text, read it. If it's a UI design or diagram, explain the layout, elements, colors, and flow."
        payload = json.dumps({"model": model, "prompt": prompt, "images": [b64_img], "stream": False})

        proc = subprocess.run(["ollama", "run", model], input=payload, capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout)
                return {"available": True, "description": data.get("response", "").strip()}
            except json.JSONDecodeError:
                return {"available": True, "description": proc.stdout.strip()}
        return {"available": True, "error": proc.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "model timed out"}
    except FileNotFoundError:
        return {"available": False, "error": "ollama not found"}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def img_to_base64(image_path: str | Path) -> str:
    """Convert image to base64 for embedding or API calls."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def save_clipboard_image(output_path: str | Path = "/tmp/pasted_image.png") -> Path | None:
    """Save clipboard image to disk (Linux: xclip, wl-paste; macOS: osascript)."""
    import shutil

    path = Path(output_path)

    if shutil.which("wl-paste"):
        try:
            with open(path, "wb") as f:
                subprocess.run(["wl-paste", "--type", "image/png"], stdout=f, check=True, timeout=5)
            if path.exists() and path.stat().st_size > 0:
                return path
        except Exception:
            pass

    if shutil.which("xclip"):
        try:
            with open(path, "wb") as f:
                subprocess.run(
                    ["xclip", "-selection", "clipboard", "-t", "image/png", "-o"], stdout=f, check=True, timeout=5
                )
            if path.exists() and path.stat().st_size > 0:
                return path
        except Exception:
            pass

    if shutil.which("osascript"):
        try:
            script = (
                'set img to (the clipboard as picture)\nset fileRef to open for access POSIX file "'
                + str(path)
                + '" with write permission\nwrite img to fileRef\nclose access fileRef'
            )
            subprocess.run(["osascript", "-e", script], check=True, timeout=5)
            if path.exists() and path.stat().st_size > 0:
                return path
        except Exception:
            pass

    return None


def describe_for_prompt(image_path: str | Path) -> str:
    """Generate a prompt-friendly description of an image.

    Returns a text block describing what the image contains,
    suitable for injecting into an LLM prompt.
    """
    analysis = analyze_image(image_path)
    lines = ["## Image Analysis", ""]

    dims = analysis.get("dimensions")
    if dims:
        lines.append(f"Dimensions: {dims['width']}x{dims['height']} ({dims['aspect_ratio']} aspect)")

    fmt = analysis.get("format", "")
    size_kb = analysis.get("size_bytes", 0) / 1024
    lines.append(f"Format: {fmt} | Size: {size_kb:.1f}KB")

    colors = analysis.get("color_stats")
    if colors and "error" not in colors:
        lines.append(
            f"Brightness: {colors.get('mean_brightness', '?')}/255 ({'dark' if colors.get('is_dark') else 'normal'})"
        )
        lines.append(f"Saturation: {colors.get('mean_saturation', '?')}/255")
        lines.append(f"Contrast: {'high' if colors.get('is_high_contrast') else 'normal'}")

    edge = analysis.get("edge_density")
    if edge is not None:
        lines.append(f"Edge density: {edge:.1%} ({'complex/detailed' if edge > 0.1 else 'simple/flat'})")

    faces = analysis.get("face_count", 0)
    if faces > 0:
        lines.append(f"Faces detected: {faces}")

    lines.append("")

    ocr = analysis.get("ocr", {})
    if ocr.get("text"):
        lines.append("### Extracted Text")
        lines.append(ocr["text"])
        lines.append(f"(OCR confidence: {ocr.get('confidence', 0)}%)")
        lines.append("")

    vision = analysis.get("vision_analysis")
    if vision and vision.get("available") and vision.get("description"):
        lines.append("### Vision Model Description")
        lines.append(vision["description"])
        lines.append("")

    if not vision or not vision.get("available"):
        lines.append("(No vision model available. Use the attached image for visual reference.)")

    return "\n".join(lines)
