"""Tests for the Guided Assistance System (mode switcher)."""

from __future__ import annotations

from cores.direct_work_engine.assistance_mode import (
    GUIDANCE,
    AssistanceMode,
    get_guidance,
    get_mode,
    set_mode,
)


def test_default_mode_is_assisted() -> None:
    assert get_mode() == AssistanceMode.ASSISTED


def test_set_mode_persists() -> None:
    set_mode("guided")
    assert get_mode() == AssistanceMode.GUIDED
    set_mode("assisted")


def test_set_mode_invalid_raises() -> None:
    try:
        set_mode("invalid_mode_xyz")
    except ValueError as exc:
        assert "Invalid mode" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_guidance_has_all_modes() -> None:
    for mode in AssistanceMode:
        g = GUIDANCE[mode.value]
        assert g["label"]
        assert g["description"]
        assert isinstance(g["explain_plan"], bool)
        assert isinstance(g["auto_approve"], bool)
        assert g["next_button_text"]


def test_mode_progression() -> None:
    set_mode("guided")
    g = get_guidance()
    assert g["explain_plan"] is True
    assert g["auto_approve"] is False

    set_mode("autonomous")
    g = get_guidance()
    assert g["explain_plan"] is False
    assert g["auto_approve"] is True

    set_mode("expert")
    g = get_guidance()
    assert g["show_technical_details"] is True
    assert g["explain_plan"] is False


def test_get_guidance_with_explicit_mode() -> None:
    g = get_guidance(AssistanceMode.EXPERT)
    assert g["show_technical_details"] is True


def test_mode_info_from_current() -> None:
    from cores.direct_work_engine.assistance_mode import ModeInfo

    set_mode("assisted")
    info = ModeInfo.from_current()
    assert info.current == "assisted"
    assert info.label == "Assisted"
    assert info.auto_approve is False
    assert "Review" in info.next_button_text


def test_mode_survives_re_read() -> None:
    set_mode("autonomous")
    assert get_mode() == AssistanceMode.AUTONOMOUS
    set_mode("assisted")
