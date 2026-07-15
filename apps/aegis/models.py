"""AEGIS — database models for offensive security operations."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AegisTarget(Base):
    __tablename__ = "aegis_targets"

    id = Column(Integer, primary_key=True)
    name = Column(String(256), nullable=False, index=True)
    domain = Column(String(256))
    scope = Column(Text)
    status = Column(String(32), default="pending")  # pending, active, completed, archived
    priority = Column(String(16), default="medium")
    tags = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class ScanResult(Base):
    __tablename__ = "aegis_scan_results"

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, nullable=False, index=True)
    scan_type = Column(String(64))  # subdomain, port, web, vuln, fuzz
    tool = Column(String(64))  # nuclei, amass, ffuf, etc.
    severity = Column(String(16))  # critical, high, medium, low, info
    title = Column(String(512))
    description = Column(Text)
    endpoint = Column(String(1024))
    cve = Column(String(32))
    cwe = Column(String(16))
    evidence = Column(Text)
    confidence = Column(Float, default=1.0)
    raw_output = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class VulnFinding(Base):
    __tablename__ = "aegis_vuln_findings"

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, nullable=False, index=True)
    scan_id = Column(Integer, nullable=False)
    title = Column(String(512), nullable=False)
    severity = Column(String(16))  # critical, high, medium, low, info
    cvss = Column(Float)
    cve = Column(String(32))
    cwe = Column(String(16))
    description = Column(Text)
    impact = Column(Text)
    remediation = Column(Text)
    poc = Column(Text)
    status = Column(String(32), default="open")  # open, confirmed, false_positive, fixed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


class ScanReport(Base):
    __tablename__ = "aegis_scan_reports"

    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, nullable=False, index=True)
    title = Column(String(512))
    format = Column(String(16), default="markdown")  # markdown, html, pdf
    content = Column(Text)
    findings_summary = Column(Text)
    severity_counts = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Payload(Base):
    __tablename__ = "aegis_payloads"

    id = Column(Integer, primary_key=True)
    name = Column(String(256))
    category = Column(String(64))  # xss, sqli, ssti, lfi, ssrf, etc.
    payload = Column(Text, nullable=False)
    description = Column(Text)
    tags = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class KnowHow(Base):
    __tablename__ = "aegis_knowhow"

    id = Column(Integer, primary_key=True)
    title = Column(String(512), nullable=False)
    category = Column(String(64))  # technique, tool, recon, exploit, reference
    content = Column(Text)
    tags = Column(Text)
    source = Column(String(256))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
