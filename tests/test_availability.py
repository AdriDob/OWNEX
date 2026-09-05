"""Tests para Availability Intelligence."""

from datetime import UTC, datetime, timedelta

import pytest

from cores.direct_work_engine.availability import (
    AvailabilityEngine,
    AvailabilitySnapshot,
    can_accommodate_task,
    get_availability_engine,
    get_availability_snapshot,
    get_available_hours,
    recommend_max_task_hours,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def engine(temp_data_dir):
    return AvailabilityEngine(data_dir=temp_data_dir)


class TestAvailabilityEngine:
    def test_snapshot_without_calendar_uses_profile_kit(self, engine, monkeypatch):
        """Sin calendario, usa Profile Kit y distribuye horas equitativamente."""
        # Mock Profile Kit
        from cores.direct_work_engine.profile_kit import ProfileKitEngine

        def mock_get(*args, **kwargs):
            return {
                "name": "Test",
                "country": "Argentina",
                "skills": ["Python"],
                "languages": ["es"],
                "experience_level": "mid",
                "availability_hours": 20.0,
            }

        monkeypatch.setattr(ProfileKitEngine, "get", mock_get)
        monkeypatch.setattr(ProfileKitEngine, "profile_from_dict", lambda d: type("P", (), d)())

        snap = engine.get_snapshot()

        assert isinstance(snap, AvailabilitySnapshot)
        assert snap.hours_this_week == 20.0
        assert snap.hours_today == 4.0  # 20/5
        assert snap.hours_this_month == pytest.approx(20.0 * 4.33, rel=0.01)
        assert snap.source == "profile_kit"

    def test_get_available_hours_today(self, engine, monkeypatch):
        from cores.direct_work_engine.profile_kit import ProfileKitEngine

        monkeypatch.setattr(ProfileKitEngine, "get", lambda *a, **k: {"availability_hours": 30.0})
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 30.0})(),
        )

        hours = engine.get_available_hours("today")
        assert hours == 6.0  # 30/5

    def test_get_available_hours_week(self, engine, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 25.0})(),
        )

        hours = engine.get_available_hours("this_week")
        assert hours == 25.0

    def test_get_available_hours_month(self, engine, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 20.0})(),
        )

        hours = engine.get_available_hours("this_month")
        assert hours == pytest.approx(20.0 * 4.33, rel=0.01)

    def test_can_accommodate_task_fits(self, engine, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 40.0})(),
        )

        fits, remaining = engine.can_accommodate(5.0, "today")
        assert fits is True
        assert remaining == 3.0  # 40/5 = 8h/day, 8 - 5 = 3

    def test_can_accommodate_task_not_fits(self, engine, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 10.0})(),
        )

        fits, remaining = engine.can_accommodate(5.0, "today")
        assert fits is False
        assert remaining == -3.0  # 2h/day - 5h = -3

    def test_recommend_max_task_hours(self, engine, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 40.0})(),
        )

        max_h = engine.recommend_max_task_hours("today")
        assert max_h == 6.4  # 8h * 0.8

    def test_default_blocks_no_calendar(self, engine):
        """Default blocks distribuye horas en días laborables."""
        blocks = engine.get_time_blocks(10)
        # Solo días laborables (lun-vie)
        available_blocks = [b for b in blocks if b.type == "available"]
        assert len(available_blocks) > 0
        for b in available_blocks:
            assert b.type == "available"
            assert b.title == "work"

    def test_add_busy_block(self, engine):
        start = datetime.now(UTC) + timedelta(hours=2)
        end = start + timedelta(hours=2)
        engine.add_busy_block(start, end, "Meeting")

        # Verificar que se guardó
        events = engine._load_calendar()
        assert len(events) == 1
        assert events[0]["type"] == "busy"
        assert events[0]["title"] == "Meeting"

    def test_add_available_block(self, engine):
        start = datetime.now(UTC) + timedelta(hours=3)
        end = start + timedelta(hours=3)
        engine.add_available_block(start, end, "Deep work")

        events = engine._load_calendar()
        assert len(events) == 1
        assert events[0]["type"] == "available"
        assert events[0]["title"] == "Deep work"

    def test_singleton_get_availability_engine(self, temp_data_dir):
        e1 = get_availability_engine(temp_data_dir)
        e2 = get_availability_engine(temp_data_dir)
        assert e1 is e2


class TestConvenienceFunctions:
    def test_get_availability_snapshot(self, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 20.0})(),
        )

        snap = get_availability_snapshot()
        assert isinstance(snap, AvailabilitySnapshot)
        assert snap.hours_this_week == 20.0

    def test_get_available_hours(self, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 30.0})(),
        )

        h = get_available_hours("today")
        assert h == 6.0

    def test_can_accommodate_task(self, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 20.0})(),
        )

        fits, rem = can_accommodate_task(2.0, "today")
        assert fits is True
        assert rem == 2.0  # 4h/day - 2h = 2h

    def test_recommend_max_task_hours(self, monkeypatch):
        monkeypatch.setattr(
            "cores.direct_work_engine.availability.ProfileKitEngine.profile_from_dict",
            lambda d: type("P", (), {"availability_hours": 40.0})(),
        )

        m = recommend_max_task_hours("today")
        assert m == 6.4


class TestSnapshotWithCalendar:
    def test_snapshot_uses_calendar_when_exists(self, engine, monkeypatch):
        # Crear calendario con bloques disponibles que incluyen la hora actual
        # Usa un rango amplio para asegurar que siempre haya horas disponibles
        now = datetime.now(UTC)
        # Empezar 2 horas antes de ahora, terminar 2 horas después
        start = now - timedelta(hours=2)
        end = now + timedelta(hours=2)
        events = [
            {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "type": "available",
                "title": "Focus",
            }
        ]
        engine._save_calendar(events)

        snap = engine.get_snapshot()

        assert snap.source == "calendar"
        assert snap.hours_today >= 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
