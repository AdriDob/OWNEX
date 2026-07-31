"""ATLAS — database models for investment portfolio tracking."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Portfolio(Base):
    __tablename__ = "atlas_portfolios"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    currency = Column(String(4), default="USD")
    initial_capital = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class Asset(Base):
    __tablename__ = "atlas_assets"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, nullable=False)
    symbol = Column(String(32), nullable=False)
    name = Column(String(256))
    asset_type = Column(String(32))  # stock, crypto, etf, bond, cash, commodity
    quantity = Column(Float, default=0.0)
    avg_price = Column(Float, default=0.0)
    currency = Column(String(4), default="USD")
    exchange = Column(String(64))
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class Transaction(Base):
    __tablename__ = "atlas_transactions"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, nullable=False)
    asset_id = Column(Integer, nullable=False)
    tx_type = Column(String(16))  # buy, sell, transfer, deposit, withdrawal
    quantity = Column(Float)
    price = Column(Float)
    fees = Column(Float, default=0.0)
    total = Column(Float)
    notes = Column(Text)
    executed_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))


class Wallet(Base):
    __tablename__ = "atlas_wallets"

    id = Column(Integer, primary_key=True)
    name = Column(String(128))
    wallet_type = Column(String(32))  # exchange, defi, hardware, software
    address = Column(String(256))
    chain = Column(String(32))  # ethereum, solana, bitcoin, polygon
    balance = Column(Float, default=0.0)
    currency = Column(String(16))
    provider = Column(String(64))  # binance, metamask, ledger, etc.
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
