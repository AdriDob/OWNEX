"""Discovery Importer — bridges BountyScraper → Program table + Assets + Knowledge Graph.

The scraper finds 1000+ programs but they sit in memory as ScrapedProgram
dataclasses. This module auto-imports them into the Program table (for
scoring, opportunity intelligence, and reporting), the Asset table (for
individual scope items), and the Knowledge Graph (for relationship queries).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from database.db import SessionLocal
from database.models_assets import Asset
from database.models_economic import Program

logger = logging.getLogger("orion.core.discovery.importer")


def import_program(
    program_data: dict[str, Any],
    session: Any | None = None,
    kg: Any | None = None,
) -> dict[str, Any]:
    """Import or update a program from scraped data into the Program + Asset + KG.

    Args:
        program_data: Dict with keys: name, platform, program_url, description,
            domains, wildcards, technologies, estimated_payout, source, confidence,
            scope_url, raw_payout_range.
        session: Optional DB session (creates one if not provided).
        kg: Optional KnowledgeGraph instance for recording nodes/edges.

    Returns:
        Dict with 'program_id', 'assets_created', 'is_new'.
    """
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        name = program_data.get("name", "").strip()
        platform = program_data.get("platform", "").strip().lower()
        if not name or not platform:
            return {"error": "name and platform are required"}

        program_url = program_data.get("program_url", "")

        existing = (
            session.query(Program)
            .filter(
                Program.platform == platform,
                Program.name.ilike(name),
            )
            .first()
        )

        if existing:
            program = existing
            is_new = False
            program.updated_at = datetime.now(timezone.utc)
        else:
            program = Program(
                name=name,
                platform=platform,
                program_url=program_url,
                status="active",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(program)
            session.flush()
            is_new = True

        technologies = program_data.get("technologies", [])
        if technologies:
            program.technologies = json.dumps(technologies)

        rewards_text = program_data.get("raw_payout_range", "")
        if rewards_text:
            program.rewards_text = rewards_text

        description = program_data.get("description", "")
        if description:
            program.scope_summary = description[:2000]

        assets_created = _import_assets(
            session=session,
            program_id=program.id,
            domains=program_data.get("domains", []),
            wildcards=program_data.get("wildcards", []),
            scope_url=program_data.get("scope_url", ""),
            source=program_data.get("source", platform),
            confidence=program_data.get("confidence", 0.8),
        )

        if kg is not None:
            _record_in_kg(kg, program, program_data, assets_created)

        session.commit()

        return {
            "program_id": program.id,
            "name": program.name,
            "platform": program.platform,
            "is_new": is_new,
            "assets_created": assets_created,
        }
    except Exception as exc:
        session.rollback()
        logger.error("[IMPORTER] Failed to import program %s: %s", program_data.get("name"), exc)
        return {"error": str(exc)}
    finally:
        if close_session:
            session.close()


def bulk_import(programs: list[dict[str, Any]], kg: Any | None = None) -> list[dict[str, Any]]:
    """Import multiple programs in a single session.

    Args:
        programs: List of program data dicts.
        kg: Optional KnowledgeGraph instance.

    Returns:
        List of result dicts, one per program.
    """
    session = SessionLocal()
    results = []
    try:
        for pd in programs:
            result = import_program(pd, session=session, kg=kg)
            results.append(result)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return results


def _import_assets(
    session: Any,
    program_id: Any,
    domains: list[str],
    wildcards: list[str],
    scope_url: str = "",
    source: str = "",
    confidence: float = 0.8,
) -> int:
    """Extract and persist scope assets for a program.

    Returns count of new assets created.
    """
    created = 0
    now = datetime.now(timezone.utc)

    for domain in domains:
        domain = domain.strip().lower()
        if not domain:
            continue
        existing = (
            session.query(Asset)
            .filter(
                Asset.program_id == program_id,
                Asset.asset_type == "domain",
                Asset.value == domain,
            )
            .first()
        )
        if not existing:
            session.add(
                Asset(
                    program_id=program_id,
                    asset_type="domain",
                    value=domain,
                    protocol="https",
                    is_active=True,
                    is_in_scope=True,
                    source=source or "discovery",
                    confidence=confidence,
                    discovered_at=now,
                )
            )
            created += 1

    for wc in wildcards:
        wc = wc.strip().lower()
        if not wc:
            continue
        existing = (
            session.query(Asset)
            .filter(
                Asset.program_id == program_id,
                Asset.asset_type == "wildcard",
                Asset.value == wc,
            )
            .first()
        )
        if not existing:
            session.add(
                Asset(
                    program_id=program_id,
                    asset_type="wildcard",
                    value=wc,
                    protocol="https",
                    is_active=True,
                    is_in_scope=True,
                    source=source or "discovery",
                    confidence=confidence,
                    discovered_at=now,
                )
            )
            created += 1

    if scope_url and not domains and not wildcards:
        existing = (
            session.query(Asset)
            .filter(
                Asset.program_id == program_id,
                Asset.asset_type == "url",
                Asset.value == scope_url,
            )
            .first()
        )
        if not existing:
            session.add(
                Asset(
                    program_id=program_id,
                    asset_type="url",
                    value=scope_url,
                    is_active=True,
                    is_in_scope=True,
                    source=source or "discovery",
                    confidence=confidence * 0.7,
                    discovered_at=now,
                )
            )
            created += 1

    return created


def _record_in_kg(kg: Any, program: Program, program_data: dict[str, Any], assets_created: int) -> None:
    """Record program and its assets in the Knowledge Graph."""
    try:
        from core.knowledge.graph import NodeTypes

        kg.add_node(
            node_id=f"program:{program.platform}:{program.id}",
            node_type=NodeTypes.PROGRAM,
            name=program.name,
            display_label=f"{program.platform}/{program.name}",
            properties={
                "platform": program.platform,
                "program_url": program.program_url or "",
                "source": program_data.get("source", program.platform),
                "assets_count": assets_created,
            },
            source="discovery_importer",
        )
        logger.debug("[KG] Recorded program node: %s", program.name)
    except Exception as exc:
        logger.warning("[KG] Failed to record program node: %s", exc)
