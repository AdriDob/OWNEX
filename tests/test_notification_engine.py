"""Tests for the unified Notification Engine.

Covers:
- Notification creation and routing
- Priority engine (CRITICAL/HIGH/MEDIUM/LOW/INFO)
- Deduplication
- Grouping
- User preferences and quiet hours
- Category filtering
- CRUD operations (mark read, resolve, remove, clear)
- Statistics
- Daily action notifications
- Monthly report generation
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from cores.notifications.daily_action import DailyAction, DailyActionEngine
from cores.notifications.engine import (
    Notification,
    NotificationCategory,
    NotificationEngine,
    NotificationPreferences,
    NotificationPriority,
)
from cores.notifications.monthly_report import MonthlyReportData, MonthlyReportEngine

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def engine():
    """Fresh NotificationEngine for each test."""
    return NotificationEngine()


@pytest.fixture
def prefs():
    """Default notification preferences."""
    return NotificationPreferences()


# ── Notification Creation ─────────────────────────────────────────────────


class TestNotificationCreation:
    def test_basic_notification(self):
        n = Notification(title="Test", message="Body")
        assert n.title == "Test"
        assert n.message == "Body"
        assert n.priority == NotificationPriority.MEDIUM
        assert n.category == NotificationCategory.SYSTEM
        assert n.read is False
        assert n.resolved is False
        assert n.id  # UUID auto-generated

    def test_notification_to_dict(self):
        n = Notification(title="T", message="M", priority=NotificationPriority.HIGH)
        d = n.to_dict()
        assert d["title"] == "T"
        assert d["priority"] == "high"
        assert "created_at" in d
        assert d["read"] is False

    def test_notification_with_entity(self):
        n = Notification(
            title="Finding",
            entity_type="finding",
            entity_id="42",
            action_label="Review",
            action_route="/findings/42",
        )
        assert n.entity_type == "finding"
        assert n.entity_id == "42"
        assert n.action_label == "Review"


# ── Priority Engine ───────────────────────────────────────────────────────


class TestPriorityEngine:
    def test_all_priorities_exist(self):
        priorities = list(NotificationPriority)
        assert len(priorities) == 5
        assert NotificationPriority.CRITICAL in priorities
        assert NotificationPriority.HIGH in priorities
        assert NotificationPriority.MEDIUM in priorities
        assert NotificationPriority.LOW in priorities
        assert NotificationPriority.INFO in priorities

    def test_priority_values(self):
        assert NotificationPriority.CRITICAL.value == "critical"
        assert NotificationPriority.HIGH.value == "high"
        assert NotificationPriority.MEDIUM.value == "medium"
        assert NotificationPriority.LOW.value == "low"
        assert NotificationPriority.INFO.value == "info"

    def test_critical_notifies_when_critical_only(self, engine):
        prefs = NotificationPreferences(
            critical_enabled=True,
            high_enabled=False,
            medium_enabled=False,
            low_enabled=False,
            info_enabled=False,
        )
        engine.set_preferences(prefs)

        n_crit = Notification(title="Crit", priority=NotificationPriority.CRITICAL)
        n_high = Notification(title="High", priority=NotificationPriority.HIGH)

        assert engine.should_send(n_crit) is True
        assert engine.should_send(n_high) is False


# ── Deduplication ─────────────────────────────────────────────────────────


class TestDeduplication:
    def test_no_dedup_without_key(self, engine):
        n1 = Notification(title="A")
        n2 = Notification(title="B")
        assert engine.is_duplicate(n1) is False
        assert engine.is_duplicate(n2) is False

    def test_dedup_with_same_key(self, engine):
        n1 = Notification(title="A", dedup_key="dup-1")
        n2 = Notification(title="B", dedup_key="dup-1")
        assert engine.is_duplicate(n1) is False
        assert engine.is_duplicate(n2) is True

    def test_dedup_expires(self, engine):
        engine._dedup_window = 0.01  # 10ms
        n1 = Notification(title="A", dedup_key="dup-expire")
        engine.is_duplicate(n1)
        time.sleep(0.02)
        n2 = Notification(title="B", dedup_key="dup-expire")
        assert engine.is_duplicate(n2) is False

    def test_different_keys_not_deduped(self, engine):
        n1 = Notification(title="A", dedup_key="key-1")
        n2 = Notification(title="B", dedup_key="key-2")
        assert engine.is_duplicate(n1) is False
        assert engine.is_duplicate(n2) is False


# ── Grouping ──────────────────────────────────────────────────────────────


class TestGrouping:
    def test_no_grouping_without_key(self, engine):
        engine._preferences.grouping_enabled = True
        n = Notification(title="A")
        assert engine.should_group(n) is False

    def test_no_grouping_when_disabled(self, engine):
        engine._preferences.grouping_enabled = False
        n = Notification(title="A", group_key="grp")
        assert engine.should_group(n) is False

    def test_grouping_with_similar_key(self, engine):
        engine._preferences.grouping_enabled = True
        n1 = Notification(title="A", group_key="scan-target-1")
        n2 = Notification(title="B", group_key="scan-target-1")
        engine.add_to_group(n1)
        assert engine.should_group(n2) is True

    def test_grouped_count(self, engine):
        engine._preferences.grouping_enabled = True
        n1 = Notification(title="A", group_key="grp-count")
        n2 = Notification(title="B", group_key="grp-count")
        n3 = Notification(title="C", group_key="grp-count")
        engine.add_to_group(n1)
        engine.add_to_group(n2)
        engine.add_to_group(n3)
        grouped = engine.get_grouped_notifications("grp-count")
        assert len(grouped) == 3


# ── User Preferences ──────────────────────────────────────────────────────


class TestPreferences:
    def test_default_preferences(self, engine):
        prefs = engine.get_preferences()
        assert prefs.desktop_enabled is True
        assert prefs.mobile_enabled is True
        assert prefs.watch_enabled is True
        assert prefs.email_enabled is False  # Disabled by default
        assert prefs.quiet_hours_enabled is False

    def test_set_preferences(self, engine):
        new_prefs = NotificationPreferences(desktop_enabled=False, mobile_enabled=False)
        engine.set_preferences(new_prefs)
        assert engine.get_preferences().desktop_enabled is False

    def test_priority_filtering(self, engine):
        prefs = NotificationPreferences(
            critical_enabled=True,
            high_enabled=True,
            medium_enabled=False,
            low_enabled=False,
            info_enabled=False,
        )
        engine.set_preferences(prefs)

        assert engine.should_send(Notification(title="Crit", priority=NotificationPriority.CRITICAL)) is True
        assert engine.should_send(Notification(title="High", priority=NotificationPriority.HIGH)) is True
        assert engine.should_send(Notification(title="Med", priority=NotificationPriority.MEDIUM)) is False

    def test_quiet_hours_blocks_non_critical(self, engine):
        now = datetime.now(UTC)
        prefs = NotificationPreferences(
            quiet_hours_enabled=True,
            quiet_hours_start=(now - timedelta(hours=2)).strftime("%H:%M"),
            quiet_hours_end=(now + timedelta(hours=2)).strftime("%H:%M"),
            quiet_hours_allow_critical=False,
        )
        engine.set_preferences(prefs)

        n_high = Notification(title="H", priority=NotificationPriority.HIGH)
        n_crit = Notification(title="C", priority=NotificationPriority.CRITICAL)
        assert engine.should_send(n_high) is False
        assert engine.should_send(n_crit) is False

    def test_quiet_hours_allows_critical_when_configured(self, engine):
        now = datetime.now(UTC)
        prefs = NotificationPreferences(
            quiet_hours_enabled=True,
            quiet_hours_start=(now - timedelta(hours=2)).strftime("%H:%M"),
            quiet_hours_end=(now + timedelta(hours=2)).strftime("%H:%M"),
            quiet_hours_allow_critical=True,
        )
        engine.set_preferences(prefs)

        n_crit = Notification(title="C", priority=NotificationPriority.CRITICAL)
        n_high = Notification(title="H", priority=NotificationPriority.HIGH)
        assert engine.should_send(n_crit) is True
        assert engine.should_send(n_high) is False


# ── Send / Route ──────────────────────────────────────────────────────────


class TestSendRoute:
    def test_send_returns_notification(self, engine):
        n = Notification(title="Hello", message="World", channels=["web"])
        result = engine.send(n)
        assert result is not None
        assert result.title == "Hello"

    def test_send_filtered_by_preferences(self, engine):
        prefs = NotificationPreferences(medium_enabled=False)
        engine.set_preferences(prefs)
        n = Notification(title="Filtered", priority=NotificationPriority.MEDIUM)
        result = engine.send(n)
        assert result is None

    def test_send_deduped(self, engine):
        n1 = Notification(title="A", dedup_key="send-dedup")
        n2 = Notification(title="B", dedup_key="send-dedup")
        r1 = engine.send(n1)
        r2 = engine.send(n2)
        assert r1 is not None
        assert r2 is None

    def test_channel_handler_called(self, engine):
        handler_called = []
        engine.register_channel_handler("web", lambda n: handler_called.append(n.id))
        n = Notification(title="Handler test", channels=["web"])
        engine.send(n)
        assert len(handler_called) == 1

    def test_channel_handler_skipped_when_disabled(self, engine):
        prefs = NotificationPreferences(desktop_enabled=False)
        engine.set_preferences(prefs)
        handler_called = []
        engine.register_channel_handler("desktop", lambda n: handler_called.append(n.id))
        n = Notification(title="Skip", channels=["desktop"])
        engine.send(n)
        assert len(handler_called) == 0

    def test_listener_notified(self, engine):
        received = []
        engine.add_listener(lambda n: received.append(n))
        n = Notification(title="Listener", channels=["web"])
        engine.send(n)
        assert len(received) == 1


# ── CRUD Operations ───────────────────────────────────────────────────────


class TestCRUD:
    def _make(self, engine, **kwargs):
        defaults = {"title": "T", "message": "M", "channels": ["web"]}
        defaults.update(kwargs)
        return engine.send(Notification(**defaults))

    def test_get_notifications(self, engine):
        self._make(engine, title="A")
        self._make(engine, title="B")
        result = engine.get_notifications()
        assert len(result) == 2

    def test_get_notifications_by_category(self, engine):
        self._make(engine, title="Opp", category=NotificationCategory.OPPORTUNITIES)
        self._make(engine, title="Sys", category=NotificationCategory.SYSTEM)
        opps = engine.get_notifications(category=NotificationCategory.OPPORTUNITIES)
        assert len(opps) == 1
        assert opps[0].title == "Opp"

    def test_get_notifications_important(self, engine):
        self._make(engine, title="Crit", priority=NotificationPriority.CRITICAL, category=NotificationCategory.SYSTEM)
        self._make(engine, title="Low", priority=NotificationPriority.LOW, category=NotificationCategory.SYSTEM)
        important = engine.get_notifications(category=NotificationCategory.IMPORTANT)
        assert len(important) == 1
        assert important[0].title == "Crit"

    def test_mark_read(self, engine):
        n = self._make(engine)
        assert engine.mark_read(n.id) is True
        unread = engine.get_unread_count()
        assert unread == 0

    def test_mark_read_nonexistent(self, engine):
        assert engine.mark_read("nonexistent-id") is False

    def test_mark_all_read(self, engine):
        self._make(engine)
        self._make(engine)
        count = engine.mark_all_read()
        assert count == 2
        assert engine.get_unread_count() == 0

    def test_resolve(self, engine):
        n = self._make(engine)
        assert engine.resolve(n.id) is True
        stats = engine.get_stats()
        assert stats["resolved"] == 1

    def test_remove(self, engine):
        n = self._make(engine)
        assert engine.remove(n.id) is True
        assert len(engine.get_notifications()) == 0

    def test_clear_all(self, engine):
        self._make(engine)
        self._make(engine)
        self._make(engine)
        count = engine.clear_all()
        assert count == 3
        assert len(engine.get_notifications()) == 0


# ── Statistics ────────────────────────────────────────────────────────────


class TestStats:
    def test_empty_stats(self, engine):
        stats = engine.get_stats()
        assert stats["total"] == 0
        assert stats["unread"] == 0
        assert stats["resolved"] == 0

    def test_stats_after_send(self, engine):
        engine.send(
            Notification(title="A", priority=NotificationPriority.HIGH, category=NotificationCategory.OPPORTUNITIES)
        )
        engine.send(Notification(title="B", priority=NotificationPriority.LOW, category=NotificationCategory.SYSTEM))
        stats = engine.get_stats()
        assert stats["total"] == 2
        assert stats["unread"] == 2
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["low"] == 1
        assert stats["by_category"]["opportunities"] == 1

    def test_stats_after_read(self, engine):
        n1 = engine.send(Notification(title="Read"))
        engine.send(Notification(title="Unread"))
        engine.mark_read(n1.id)
        stats = engine.get_stats()
        assert stats["total"] == 2
        assert stats["unread"] == 1


# ── Expiry ────────────────────────────────────────────────────────────────


class TestExpiry:
    def test_cleanup_expired(self, engine):
        n = Notification(
            title="Expired",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        engine.send(n)
        assert len(engine.get_notifications()) == 1
        removed = engine.cleanup_expired()
        assert removed == 1
        assert len(engine.get_notifications()) == 0

    def test_cleanup_keeps_fresh(self, engine):
        n = Notification(
            title="Fresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        engine.send(n)
        removed = engine.cleanup_expired()
        assert removed == 0
        assert len(engine.get_notifications()) == 1


# ── Daily Action ──────────────────────────────────────────────────────────


class TestDailyAction:
    def test_daily_action_engine_imports(self):
        assert DailyActionEngine is not None
        assert DailyAction is not None

    def test_daily_action_to_dict(self):
        action = DailyAction(
            action="Validate API target X",
            reason="Highest EV/h currently available",
            ev_usd=420.0,
            ev_per_hour=180.0,
            time_estimate_minutes=140,
            priority="high",
            impact="Potential $420 bounty",
            entity_type="target",
            entity_id="123",
            action_route="/targets/123",
        )
        d = action.to_dict()
        assert d["action"] == "Validate API target X"
        assert d["ev_usd"] == 420.0
        assert d["time_estimate_minutes"] == 140

    def test_send_daily_notification(self):
        engine = NotificationEngine()
        daily_engine = DailyActionEngine()
        daily_engine._engine = engine

        action = DailyAction(
            action="Test action",
            reason="Test reason",
            ev_usd=100.0,
            ev_per_hour=50.0,
            time_estimate_minutes=120,
            priority="high",
            impact="Impact",
            entity_type="target",
            entity_id="1",
            action_route="/test",
        )
        result = daily_engine.send_daily_notification(action)
        assert result is not None
        assert "NEXT BEST ACTION" in result.title

    def test_send_no_action_notification(self):
        engine = NotificationEngine()
        daily_engine = DailyActionEngine()
        daily_engine._engine = engine

        result = daily_engine.send_no_action_notification()
        assert result is not None
        assert "NO ACTION REQUIRED" in result.title
        assert result.priority == NotificationPriority.INFO


# ── Monthly Report ────────────────────────────────────────────────────────


class TestMonthlyReport:
    def test_report_data_creation(self):
        data = MonthlyReportData(
            month="2026-08",
            year=2026,
            month_name="August",
            total_income=5000.0,
            income_target=10000.0,
            income_progress_pct=50.0,
            capital_accumulated=25000.0,
            goal_1m_progress_pct=2.5,
        )
        d = data.to_dict()
        assert d["total_income"] == 5000.0
        assert d["goal_1m_progress_pct"] == 2.5

    def test_generate_html(self):
        engine = MonthlyReportEngine()
        data = MonthlyReportData(
            month="2026-08",
            year=2026,
            month_name="August",
            total_income=5000.0,
        )
        html = engine.generate_report(data)
        assert "OWNEX Monthly Report" in html
        assert "August" in html
        assert "2026" in html

    def test_send_monthly_report(self):
        notif_engine = NotificationEngine()
        monthly_engine = MonthlyReportEngine()
        monthly_engine._engine = notif_engine

        data = MonthlyReportData(
            month="2026-08",
            year=2026,
            month_name="August",
            total_income=3500.0,
        )
        result = monthly_engine.send_monthly_report(data, "test@example.com")
        assert result is True
        assert notif_engine.get_unread_count() == 1


# ── Preferences to_dict ───────────────────────────────────────────────────


class TestPreferencesDict:
    def test_to_dict(self):
        prefs = NotificationPreferences()
        d = prefs.to_dict()
        assert d["desktop_enabled"] is True
        assert d["email_enabled"] is False
        assert d["quiet_hours_enabled"] is False
        assert d["retention_days"] == 30
        assert d["grouping_window_seconds"] == 300


# ── Categories ────────────────────────────────────────────────────────────


class TestCategories:
    def test_all_categories(self):
        cats = list(NotificationCategory)
        expected = [
            "all",
            "important",
            "opportunities",
            "work",
            "finance",
            "security",
            "agents",
            "system",
            "errors",
            "action_required",
        ]
        assert len(cats) == len(expected)
        for cat in cats:
            assert cat.value in expected
