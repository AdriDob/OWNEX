from __future__ import annotations

import pytest

from core.copilot.vision import analyze_image, describe_for_prompt, img_to_base64


def test_analyze_nonexistent():
    result = analyze_image("/tmp/nonexistent_image_xyz.png")
    assert result["exists"] is False
    assert result["file"] == "/tmp/nonexistent_image_xyz.png"


def test_img_to_base64_nonexistent():
    with pytest.raises(FileNotFoundError):
        img_to_base64("/tmp/nonexistent_image_xyz.png")


def test_describe_nonexistent():
    result = describe_for_prompt("/tmp/nonexistent_image_xyz.png")
    assert "Image Analysis" in result


def test_analyze_has_keys():
    result = analyze_image("/tmp/nonexistent_image_xyz.png")
    assert "ocr" in result
    assert "dimensions" in result
    assert "color_stats" in result
    assert "edge_density" in result
    assert "face_count" in result


def test_describe_no_image():
    text = describe_for_prompt("/dev/null")
    assert isinstance(text, str)
