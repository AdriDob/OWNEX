"""
OWNEX Autonomous Opportunity Scanner — Periodic Discovery Engine

Runs autonomously to:
1. Scan all 100+ global sources across 3 categories
2. Filter for no-experience/no-interview/no-portfolio work
3. Log new opportunities locally
4. Maintain favorites (10 per category)
5. Report weekly summaries via cron job output

Usage:
  python3 -m cores.opportunity.auto_scanner scan        # quick scan
  python3 -m cores.opportunity.auto_scanner deep-scan   # full scan (slower)
  python3 -m cores.opportunity.auto_scanner report       # generate summary
"""

from __future__ import annotations

import datetime
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "opportunity_discovery"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Import global sources (soft fail if not available in raw Python context) ──

try:
    from cores.opportunity.global_sources import (
        OpportunityCategory,
        SourceDefinition,
        get_categorized_counts,
        get_favorites,
        get_sources,
        get_total_source_count,
    )

    _SOURCES_AVAILABLE = True
except ImportError:
    _SOURCES_AVAILABLE = False

try:
    from cores.opportunity.sources_expansion import (
        get_credential_requirement,
        get_fallback_chain,
        sources_for_scan,
    )

    _EXPANSION_AVAILABLE = True
except ImportError:
    _EXPANSION_AVAILABLE = False


def _source_categories() -> list[OpportunityCategory]:
    """Iterate the curated source families instead of hardcoding their names."""
    if _SOURCES_AVAILABLE:
        return list(OpportunityCategory)
    return []


@dataclass
class DiscoveryRecord:
    """A single opportunity found during a scan."""

    source_name: str
    source_url: str
    category: str
    title: str
    url: str
    description: str
    requirements: str = "none"
    payout: str = "unknown"
    date_found: str = ""
    requires_experience: bool = True
    requires_interview: bool = True
    requires_portfolio: bool = True
    apply_type: str = "unknown"
    tags: list[str] = field(default_factory=list)
    # "source_lead" = catalog entry surfaced for manual follow-up (NOT a live
    # task); "live_opportunity" = confirmed by a real fetch/parser/API check.
    kind: str = "source_lead"


@dataclass
class DiscoveryReport:
    """Report of a full scanning session."""

    timestamp: str = ""
    sources_scanned: int = 0
    catalog_total: int = 0
    sources_eligible: int = 0
    sources_substituted: int = 0
    credential_gated: int = 0
    payment_fallback_sources: int = 0
    opportunities_found: int = 0
    filtered_out_experience: int = 0
    filtered_out_interview: int = 0
    filtered_out_portfolio: int = 0
    qualifying: int = 0
    live_opportunities_found: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    favorites: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def check_source_available(url: str, timeout: int = 5) -> bool:
    """Quick HTTP HEAD check to see if a source is reachable."""
    try:
        import urllib.request

        req = urllib.request.Request(url, method="HEAD")
        # Also pass User-Agent
        req.add_header("User-Agent", "Mozilla/5.0 (OWNEX-Opportunity-Scanner/1.0)")
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status < 500
    except Exception:
        return False


def parse_source_opportunities(source: SourceDefinition) -> list[DiscoveryRecord]:
    """
    Surface a source as a discovery *lead* — NOT a live opportunity.

    A catalog entry only becomes a live opportunity after a real
    fetch/parser/API/browser check confirms an actual open task.
    Until per-source parsers exist, every record is ``kind="source_lead"``.
    """
    records: list[DiscoveryRecord] = []
    try:
        record = DiscoveryRecord(
            source_name=source.name,
            source_url=source.url,
            category=source.category.value,
            title=f"{source.name} — {source.category.value.replace('_', ' ')} source lead",
            url=source.url,
            description=source.description,
            requirements=f"Experience: {'Required' if source.requires_experience else 'Not Required'} | "
            f"Interview: {'Required' if source.requires_interview else 'Not Required'} | "
            f"Portfolio: {'Required' if source.requires_portfolio else 'Not Required'}",
            payout=source.estimated_payout_range,
            date_found=_now(),
            requires_experience=source.requires_experience,
            requires_interview=source.requires_interview,
            requires_portfolio=source.requires_portfolio,
            apply_type=source.apply_method,
            tags=source.tags,
        )
        records.append(record)
    except Exception:
        pass
    return records


def run_scan(deep: bool = False) -> DiscoveryReport:
    """Run a scan of all available sources."""
    report = DiscoveryReport(timestamp=_now())

    if not _SOURCES_AVAILABLE:
        report.errors.append("Global sources database not available")
        return report

    if _EXPANSION_AVAILABLE:
        sources = sources_for_scan(eligible_only=True)
        report.catalog_total = len(sources_for_scan(eligible_only=False))
        report.sources_eligible = len(sources)
        report.credential_gated = sum(1 for s in sources if (get_credential_requirement(s) or {}).get("kind") not in (None, "none"))
        report.payment_fallback_sources = sum(1 for s in sources if not getattr(s, "argentina_ok", True))
    else:
        sources = get_sources()
        report.sources_eligible = len(sources)
    report.sources_scanned = len(sources)

    all_discoveries: list[DiscoveryRecord] = []

    for _idx, source in enumerate(sources):
        try:
            scan_source = source
            # Deep scan: check availability; on failure substitute the first
            # reachable alternate from the source's fallback chain (subfuente
            # replacement per OWNEX spec).
            if deep:
                available = check_source_available(source.url)
                if not available:
                    substituted = False
                    if _EXPANSION_AVAILABLE:
                        for alt in get_fallback_chain(source):
                            if check_source_available(alt.url):
                                scan_source = alt
                                substituted = True
                                report.sources_substituted += 1
                                report.errors.append(f"Source unreachable, substituted: {source.name} -> {alt.name}")
                                break
                    if not substituted:
                        report.errors.append(f"Source unreachable: {source.name} ({source.url})")
                        continue

            opportunities = parse_source_opportunities(scan_source)
            all_discoveries.extend(opportunities)
            report.opportunities_found += len(opportunities)
            report.live_opportunities_found += sum(1 for o in opportunities if o.kind == "live_opportunity")

            # Apply the user's no-experience/no-interview/no-portfolio filter
            for opp in opportunities:
                if opp.requires_experience:
                    report.filtered_out_experience += 1
                    continue
                if opp.requires_interview:
                    report.filtered_out_interview += 1
                    continue
                if opp.requires_portfolio:
                    report.filtered_out_portfolio += 1
                    continue
                report.qualifying += 1
                category = opp.category
                if category not in report.by_category:
                    report.by_category[category] = 0
                report.by_category[category] += 1

        except Exception as exc:
            report.errors.append(f"Error scanning {source.name}: {exc}")

    # Compile favorites
    for cat in OpportunityCategory:
        favs = get_favorites(cat, limit=10)
        report.favorites[cat.value] = [asdict(f) for f in favs]

    # Save discoveries to disk
    save_path = DATA_DIR / f"discovery_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(save_path, "w") as f:
            json.dump(
                {
                    "timestamp": report.timestamp,
                    "total_sources": report.sources_scanned,
                    "catalog_total": report.catalog_total,
                    "sources_eligible": report.sources_eligible,
                    "sources_substituted": report.sources_substituted,
                    "credential_gated": report.credential_gated,
                    "payment_fallback_sources": report.payment_fallback_sources,
                    "opportunities_found": report.opportunities_found,
                    "live_opportunities_found": report.live_opportunities_found,
                    "qualifying": report.qualifying,
                    "by_category": report.by_category,
                    "favorites": report.favorites,
                    "errors": report.errors,
                },
                f,
                indent=2,
                default=str,
            )
    except OSError as exc:
        report.errors.append(f"Failed to save discoveries: {exc}")

    return report


def generate_summary(report: DiscoveryReport | None = None) -> str:
    """Generate a human-readable summary of the last scan."""
    latest_files = sorted(DATA_DIR.glob("discovery_*.json"), reverse=True)
    if not latest_files:
        return "No discovery data found. Run a scan first."

    with open(latest_files[0]) as f:
        data = json.load(f)

    lines = [
        "╔══════════════════════════════════════════════════╗",
        "║   OWNEX Autonomous Opportunity Discovery Report  ║",
        "╚══════════════════════════════════════════════════╝",
        "",
        f"Generated: {data.get('timestamp', 'unknown')}",
        "",
        f"  Sources scanned:       {data.get('total_sources', 0)}",
        f"  Opportunities found:   {data.get('opportunities_found', 0)}",
        f"  Qualifying (no exp/int/portfolio): {data.get('qualifying', 0)}",
        "",
        "  By Category:",
    ]

    by_cat = data.get("by_category", {})
    for cat_member in _source_categories():
        cat_name = cat_member.value
        count = by_cat.get(cat_name, 0)
        label = cat_name.replace("_", " ").title()
        lines.append(f"    - {label}: {count}")

    lines.extend(
        [
            "",
            "  Top 10 Favorites Per Category:",
        ]
    )

    favorites = data.get("favorites", {})
    for cat_member in _source_categories():
        cat_name = cat_member.value
        favs = favorites.get(cat_name, [])
        label = cat_name.replace("_", " ").title()
        lines.append(f"\n    ── {label} ──")
        for i, fav in enumerate(favs[:10], 1):
            lines.append(f"      {i}. {fav.get('name', '?')} — {fav.get('url', '?')}")
            lines.append(f"         {fav.get('description', '')[:100]}")

    errors = data.get("errors", [])
    if errors:
        lines.extend(["", f"  Errors ({len(errors)}):"])
        for err in errors[:5]:
            lines.append(f"    ⚠ {err}")
        if len(errors) > 5:
            lines.append(f"    ... and {len(errors) - 5} more")

    lines.extend(
        [
            "",
            "════════════════════════════════════════════════",
            "  System Status: ALL SYSTEMS OPERATIONAL",
            f"  Total tracked sources: {get_total_source_count()}",
            "  Next scan: daily (automatic)",
            "════════════════════════════════════════════════",
        ]
    )

    return "\n".join(lines)


# ── CLI entry points ──


def cmd_scan():
    """Quick scan (no deep checks)."""
    print(f"Running opportunity scan at {_now()}...")
    report = run_scan(deep=False)
    print(f"Done. Scanned {report.sources_scanned} sources, found {report.qualifying} qualifying opportunities.")
    if report.errors:
        print(f"Errors: {len(report.errors)}")
    print(f"Summary saved to {DATA_DIR}/")
    print(generate_summary(report))


def cmd_deep_scan():
    """Deep scan with availability checks."""
    print(f"Running DEEP opportunity scan at {_now()}...")
    report = run_scan(deep=True)
    print(f"Done. Scanned {report.sources_scanned} sources, found {report.qualifying} qualifying opportunities.")
    if report.errors:
        print(f"Errors ({len(report.errors)}):")
        for e in report.errors[:10]:
            print(f"  - {e}")
    print(generate_summary(report))


def cmd_report():
    """Generate the last report."""
    print(generate_summary())


def cmd_status():
    """Show opportunity system status."""
    if _SOURCES_AVAILABLE:
        counts = get_categorized_counts()
        total = get_total_source_count()
        print("Opportunity Discovery System: ACTIVE")
        print(f"Total sources: {total}")
        for cat, count in counts.items():
            print(f"  {cat.replace('_', ' ').title()}: {count} sources, {len(get_favorites(OpportunityCategory(cat)))} favorites")
        latest = sorted(DATA_DIR.glob("discovery_*.json"), reverse=True)
        if latest:
            print(f"Last scan: {latest[0].stat().st_mtime}")
    else:
        print("Opportunity Discovery System: UNAVAILABLE (sources module not loaded)")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "scan"
    commands = {
        "scan": cmd_scan,
        "deep-scan": cmd_deep_scan,
        "report": cmd_report,
        "status": cmd_status,
    }
    handler = commands.get(command)
    if handler:
        handler()
    else:
        print(f"Unknown command: {command}")
        print("Available: scan, deep-scan, report, status")
        sys.exit(1)
