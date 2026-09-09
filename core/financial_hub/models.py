"""Financial Hub — SQLAlchemy models for persistent financial intelligence."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from database.db import Base


class KYCRecord(Base):
    """Tracks KYC/verification status per platform."""

    __tablename__ = "kyc_records"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, nullable=False, unique=True, index=True)
    platform_name = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="not_started"
    )  # not_started, in_progress, completed, expired, failed
    kyc_level = Column(String, nullable=False, default="")  # email, dni, passport, etc.
    documents_required = Column(Text, nullable=False, default="[]")  # JSON list
    documents_submitted = Column(Text, nullable=False, default="[]")
    notes = Column(Text, nullable=False, default="")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PayoutDocument(Base):
    """Checklist of documents needed for payouts."""

    __tablename__ = "payout_documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String, nullable=False, default="general")  # identity, tax, bank, platform, crypto
    is_required = Column(Boolean, nullable=False, default=True)
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=False, default="")
    platforms = Column(Text, nullable=False, default="[]")  # JSON list of applicable platforms
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WithdrawalRoute(Base):
    """Configured withdrawal routes for converting payouts to local currency."""

    __tablename__ = "withdrawal_routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=False, default="")
    route_type = Column(String, nullable=False)  # crypto_exchange, p2p, bank_transfer, wallet, defi
    source_currency = Column(String, nullable=False, default="USD")
    target_currency = Column(String, nullable=False, default="ARS")
    fee_percent = Column(Float, nullable=False, default=0.0)
    fee_fixed = Column(Float, nullable=False, default=0.0)
    arrival_days = Column(String, nullable=False, default="1-3")
    is_active = Column(Boolean, nullable=False, default=True)
    is_emergency = Column(Boolean, nullable=False, default=False)
    priority = Column(Integer, nullable=False, default=0)
    steps = Column(Text, nullable=False, default="[]")  # JSON list of step descriptions
    requirements = Column(Text, nullable=False, default="[]")  # JSON list
    notes = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaxRecord(Base):
    """Tax reference notes per country/platform."""

    __tablename__ = "tax_records"

    id = Column(Integer, primary_key=True, index=True)
    country = Column(String, nullable=False, default="AR")
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String, nullable=False, default="general")  # general, regulation, form, deadline, exemption
    platforms = Column(Text, nullable=False, default="[]")
    reference_url = Column(String, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
