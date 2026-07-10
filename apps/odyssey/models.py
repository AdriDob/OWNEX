"""ODYSSEY — database models for gambling analytics.

Analytical only — tracks performance, never executes bets.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Bankroll(Base):
    """Bankroll — tracks capital across platforms."""

    __tablename__ = "odyssey_bankrolls"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    platform = Column(String(64))  # polymarket, betfair, pinnacle, manual
    balance = Column(Float, default=0.0)
    currency = Column(String(4), default="USD")
    risk_level = Column(String(16), default="medium")  # low, medium, high
    max_stake_percent = Column(Float, default=5.0)
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Bet(Base):
    """Bet — individual wager record."""

    __tablename__ = "odyssey_bets"

    id = Column(Integer, primary_key=True)
    bankroll_id = Column(Integer, nullable=False)
    event = Column(String(256))
    market = Column(String(256))
    platform = Column(String(64))  # polymarket, betfair, pinnacle, stake, manual
    bet_type = Column(String(32))  # yes/no, moneyline, spread, over/under, parlay
    odds = Column(Float)  # Decimal odds (e.g. 2.50)
    stake = Column(Float)
    outcome = Column(String(16))  # win, loss, push, pending
    payout = Column(Float, default=0.0)
    roi = Column(Float, default=0.0)
    ev = Column(Float, default=0.0)  # Expected Value at time of bet
    closing_line = Column(Float)  # Closing odds for CLV calculation
    clv = Column(Float)  # Closing Line Value
    tags = Column(String(256))  # comma-separated tags
    notes = Column(Text)
    placed_at = Column(DateTime)
    settled_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Strategy(Base):
    """Strategy — betting strategy configuration."""

    __tablename__ = "odyssey_strategies"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    bankroll_id = Column(Integer, nullable=False)
    kelly_fraction = Column(Float, default=0.25)  # Fractional Kelly (0.0-1.0)
    max_stake = Column(Float, default=100.0)
    min_odds = Column(Float, default=1.5)
    max_odds = Column(Float, default=10.0)
    min_ev = Column(Float, default=0.05)
    sports = Column(String(512))  # comma-separated
    platforms = Column(String(512))
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
