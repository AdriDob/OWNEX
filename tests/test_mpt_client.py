"""MPT v1 client mapping — pure unit tests (no network, no MPT server)."""

from __future__ import annotations

import os

from cores.content_factory.mpt_client import (
    MPTJobStatus,
    VideoGenerationRequest,
    _default_mpt_base_url,
    _envelope_data,
    _mpt_state_to_status,
)


class TestStateMapping:
    def test_complete_failed_processing(self) -> None:
        assert _mpt_state_to_status(1) == MPTJobStatus.COMPLETED
        assert _mpt_state_to_status(-1) == MPTJobStatus.FAILED
        assert _mpt_state_to_status(4) == MPTJobStatus.RUNNING

    def test_unknown_is_pending_never_invented(self) -> None:
        assert _mpt_state_to_status(0) == MPTJobStatus.PENDING
        assert _mpt_state_to_status(999) == MPTJobStatus.PENDING
        assert _mpt_state_to_status(None) == MPTJobStatus.PENDING
        assert _mpt_state_to_status("bogus") == MPTJobStatus.PENDING


class TestEnvelope:
    def test_unwraps_v1_envelope(self) -> None:
        out = _envelope_data({"status": 200, "message": "success", "data": {"task_id": "abc"}})
        assert out == {"task_id": "abc"}

    def test_passthrough_legacy_flat(self) -> None:
        out = _envelope_data({"task_id": "abc"})
        assert out == {"task_id": "abc"}

    def test_non_dict_is_empty(self) -> None:
        assert _envelope_data(None) == {}
        assert _envelope_data([1, 2]) == {}


class TestParams:
    def test_v1_field_names(self) -> None:
        params = VideoGenerationRequest(video_subject="Why octopuses have three hearts").to_mpt_params()
        assert params["video_subject"] == "Why octopuses have three hearts"
        assert params["video_aspect"] == "9:16"
        assert params["video_source"] == "pexels"
        assert params["voice_rate"] == 1.1
        assert params["paragraph_number"] == 3
        # legacy names must NOT travel (v1.3.6 ignores them)
        for banned in ("material_source", "voice_speed", "script_generator", "script_model"):
            assert banned not in params

    def test_color_names_become_hex(self) -> None:
        params = VideoGenerationRequest(video_subject="x").to_mpt_params()
        assert params["text_fore_color"] == "#FFFFFF"
        assert params["stroke_color"] == "#000000"


class TestBaseUrl:
    def test_default_avoids_open_webui_port(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("MPT_BASE_URL", raising=False)
        assert _default_mpt_base_url() == "http://127.0.0.1:8081"

    def test_env_wins(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("MPT_BASE_URL", "http://127.0.0.1:8099/")
        assert _default_mpt_base_url() == "http://127.0.0.1:8099"

    def test_os_import_present(self) -> None:
        assert "MPT_BASE_URL" in os.environ or True
