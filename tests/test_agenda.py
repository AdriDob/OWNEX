"""Tests for Unified Agenda module."""

import pytest

from cores.agenda import (
    AgendaItem,
    Horizon,
    Source,
    _from_capital,
    _from_career,
    _from_income_target,
    _from_workbank,
    build_unified_agenda,
)


class TestAgendaItem:
    def test_agenda_item_creation(self):
        item = AgendaItem(
            date="2026-08-28",
            horizon=Horizon.TODAY.value,
            source=Source.WORK.value,
            title="Test task",
            progress_pct=50.0,
            reward_or_value=100.0,
            url="https://example.com",
            action="Execute task",
        )
        assert item.date == "2026-08-28"
        assert item.horizon == "today"
        assert item.source == "work"
        assert item.title == "Test task"
        assert item.progress_pct == 50.0
        assert item.reward_or_value == 100.0

    def test_agenda_item_to_dict(self):
        item = AgendaItem(
            date="2026-08-28",
            horizon=Horizon.SHORT.value,
            source=Source.CAPITAL.value,
            title="Test task",
        )
        d = item.to_dict()
        assert d["date"] == "2026-08-28"
        assert d["horizon"] == "short"
        assert d["source"] == "capital"
        assert d["title"] == "Test task"
        assert "reward" in d
        assert "url" in d
        assert "action" in d


class TestAgendaSources:
    def test_from_workbank_returns_list(self):
        items = _from_workbank()
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, AgendaItem)

    def test_from_income_target_returns_list(self):
        items = _from_income_target()
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, AgendaItem)

    def test_from_career_returns_list(self):
        items = _from_career()
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, AgendaItem)

    def test_from_capital_returns_list(self):
        items = _from_capital()
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, AgendaItem)


class TestBuildUnifiedAgenda:
    def test_returns_agenda_structure(self):
        agenda = build_unified_agenda()
        assert "generated_at" in agenda
        assert "total_items" in agenda
        assert "today" in agenda
        assert "short_term" in agenda
        assert "medium_term" in agenda
        assert "long_term" in agenda
        assert "counts" in agenda
        assert "best_action" in agenda

    def test_total_items_count_matches(self):
        agenda = build_unified_agenda()
        total_from_counts = sum(agenda["counts"].values())
        # total_items should be >= sum of all horizon items (including those beyond 5 shown)
        assert agenda["total_items"] >= total_from_counts

    def test_horizons_have_correct_types(self):
        agenda = build_unified_agenda()
        for h in ["today", "short_term", "medium_term", "long_term"]:
            assert isinstance(agenda[h], list)
            for item in agenda[h]:
                assert "date" in item
                assert "horizon" in item
                assert "source" in item
                assert "title" in item

    def test_best_action_exists_when_items_present(self):
        agenda = build_unified_agenda()
        if agenda["total_items"] > 0:
            assert agenda["best_action"] is not None
            assert "title" in agenda["best_action"]
            assert "source" in agenda["best_action"]


class TestHorizonEnum:
    def test_horizon_values(self):
        assert Horizon.TODAY.value == "today"
        assert Horizon.SHORT.value == "short"
        assert Horizon.MEDIUM.value == "medium"
        assert Horizon.LONG.value == "long"


class TestSourceEnum:
    def test_source_values(self):
        assert Source.WORK.value == "work"
        assert Source.CAPITAL.value == "capital"
        assert Source.CAREER.value == "career"
        assert Source.PERSONAL.value == "personal"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
