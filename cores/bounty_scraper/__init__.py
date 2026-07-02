"""
core_engines.bounty_scraper — Autonomous program discovery.

Scrapes public bug bounty program listings from HackerOne, Bugcrowd,
Intigriti, and other platforms. Each discovered program is converted
into a target in the database with its scope document parsed.

Flow:
  1. discover() → fetch all public programs from all platforms
  2. enrich() → for each program, download + parse scope document
  3. convert() → create/update Target + ScopeDocument in DB
  4. prioritize() → rank by estimated payout, freshness, competition
"""

from cores.bounty_scraper.scraper import BountyScraper, ScrapedProgram, get_bounty_scraper

__all__ = [
    "BountyScraper",
    "ScrapedProgram",
    "get_bounty_scraper",
]
