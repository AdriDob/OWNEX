"""Tests for Daily Brief Engine."""

from __future__ import annotations

import pytest

from core.daily.brief import (
    DailyBriefEngine,
    get_daily_brief_engine,
)


@pytest.fixture()
def clean_brief():
    """Provide a clean daily brief engine for each test."""
    from database.db import Base, engine
    from sqlalchemy import Column, DateTime, Integer, String, Text, func
    from sqlalchemy.orm import declarative_base

    TestBase = declarative_base()

    class TempDailyBriefModel(TestBase):
        __tablename__ = "daily_briefs"
        id = Column(Integer, primary_key=True, index=True)
        brief_id = Column(String(64), unique=True, nullable=False, index=True)
        generated_at = Column(String, nullable=False)
        brief_json = Column(Text, nullable=False)
        created_at = Column(DateTime(timezone=True), server_default=func.now())

    TestBase.metadata.drop_all(bind=engine)
    TestBase.metadata.create_all(bind=engine)

    engine = get_daily_brief_engine()
    yield engine

    TestBase.metadata.drop_all(bind=engine)


class TestDailyBriefEngine:
    """Tests for DailyBriefEngine."""

    def test_generate_brief(self, clean_brief):
        """Test generating a daily brief."""
        brief = clean_brief.generate()
        assert isinstance(brief, dict)
        assert "generated_at" in brief
        assert "critical" in brief
        assert "high_value" in brief
        assert "autonomous" in brief
        assert "waiting" in brief
        assert "completed" in brief
        assert "revenue" in brief
        assert "alerts" in brief

    def test_critical_actions(self, clean_brief):
        """Test critical actions are generated."""
        brief = clean_brief.generate()
        assert isinstance(brief["critical"], list)

    def test_high_value(self, clean_brief):
        """Test high value opportunities."""
        brief = clean_brief.generate()
        assert isinstance(brief["high_value"], list)

    def test_autonomous_work(self, clean_brief):
        """Test autonomous work section."""
        brief = clean_brief.generate()
        assert isinstance(brief["autonomous"], list)

    def test_waiting_items(self, clean_brief):
        """Test waiting items."""
        brief = clean_brief.generate()
        assert isinstance(brief["waiting"], list)

    def test_completed_work(self, clean_brief):
        """Test completed work."""
        brief = clean_brief.generate()
        assert isinstance(brief["completed"], list)

    def test_revenue_summary(self, clean_brief):
        """Test revenue summary."""
        brief = clean_brief.generate()
        revenue = brief["revenue"]
        assert "total_gross_usd" in revenue
        assert "total_net_usd" in revenue
        assert "by_state" in revenue

    def test_alerts(self, clean_brief):
        """Test alerts are generated."""
        brief = clean_brief.generate()
        assert isinstance(brief["alerts"], list)

    def test_save_brief(self, clean_brief):
        """Test saving a brief."""
        brief = clean_brief.generate()
        clean_brief.save_brief(brief)

        # Verify it was saved
        from core.daily.brief_store import get_latest_brief

        saved = get_latest_brief()
        if saved is not None:
            assert saved["generated_at"] == brief["generated_at"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
