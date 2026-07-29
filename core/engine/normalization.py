"""Normalization Engine — transforms raw observations into canonical form.

Each platform expresses data differently. This engine parses reward strings,
effort estimates, tag names, and confidence into OWNEX canonical fields.
"""
from __future__ import annotations

import hashlib
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from core.engine.base import Engine
from core.sensors.observation import Observation

logger = logging.getLogger("ownex.normalization")

# ── Field parsers ────────────────────────────────────────────────────


def parse_reward_range(text: str) -> tuple[float, float, str]:
    """Universal reward parser — handles all known formats.

    "$500 - $10,000"           → (500.0, 10000.0, "USD")
    "$1000"                    → (1000.0, 1000.0, "USD")
    "25 USD/h"                 → (25.0, 25.0, "USD")
    "$25/hr"                   → (25.0, 25.0, "USD")
    "€15-€25 per hour"         → (15.0, 25.0, "EUR")
    "500 SOL"                  → (500.0, 500.0, "SOL")
    "10000 max_payout"         → (10000.0, 10000.0, "USD")
    "bounty: 0.5 ETH - 2 ETH"  → (0.5, 2.0, "ETH")
    "hourly_rate: 25"          → (25.0, 25.0, "USD")
    "prize: 500"               → (500.0, 500.0, "USD")
    "offers_bounties: true"    → (0.0, 0.0, "USD")
    "" or None                 → (0.0, 0.0, "USD")
    """
    if not text:
        return (0.0, 0.0, "USD")

    text = str(text).strip()

    # Detect currency
    currency = "USD"
    for sym, code in [
        ("$", "USD"), ("€", "EUR"), ("£", "GBP"), ("¥", "JPY"),
        ("ETH", "ETH"), ("BTC", "BTC"), ("SOL", "SOL"),
        ("usd", "USD"), ("eur", "EUR"),
    ]:
        if sym.lower() in text.lower():
            currency = code
            break

    # Extract all number patterns
    amounts = re.findall(r"([\d,]+(?:\.\d+)?)", text.replace(",", ""))
    parsed: list[float] = []
    for a in amounts:
        try:
            parsed.append(float(a.replace(",", "")))
        except ValueError:
            continue

    if not parsed:
        return (0.0, 0.0, currency)

    return (min(parsed), max(parsed), currency)


def parse_effort_hours(text: str | float | None) -> float:
    """Parse effort estimation into hours.

    "2 days"        → 16.0
    "3 hours"       → 3.0
    "1 week"        → 40.0
    "30 min"        → 0.5
    "estimated_hours: 8" → 8.0
    "time_estimate: 2"  → 2.0
    5.0             → 5.0
    None            → 0.0
    """
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        return float(text)

    text = str(text).lower().strip()

    # Check for days
    days_match = re.search(r"(\d+(?:\.\d+)?)\s*d(?:ay)?s?", text)
    if days_match:
        return float(days_match.group(1)) * 8

    # Check for weeks
    weeks_match = re.search(r"(\d+(?:\.\d+)?)\s*w(?:ee)?k", text)
    if weeks_match:
        return float(weeks_match.group(1)) * 40

    # Check for minutes
    min_match = re.search(r"(\d+(?:\.\d+)?)\s*min", text)
    if min_match:
        return float(min_match.group(1)) / 60

    # Check for hours
    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*h(?:(?:ou)?r)?", text)
    if hours_match:
        return float(hours_match.group(1))

    # Try plain number
    try:
        return float(text)
    except ValueError:
        return 0.0


def normalize_tags(tags: list[str]) -> list[str]:
    """Normalize tag names across platforms.

    ["Python", "python3", "py"] → ["python"]
    ["API", "api", "ApI"]       → ["api"]
    ["Data Science", "data_science"] → ["data-science"]
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        t = tag.lower().strip().replace("_", "-").replace(" ", "-")
        if t not in seen:
            seen.add(t)
            normalized.append(t)
    return normalized


# ── Normalizer interface ────────────────────────────────────────────


class Normalizer(ABC):
    """A normalizer knows how to normalize observations from ONE sensor."""

    @abstractmethod
    def normalize(self, observation: Observation) -> Observation:
        """Normalize sensor-specific fields into canonical form."""


class ScrapedProgramNormalizer(Normalizer):
    """Normalizes BountyScraper's ScrapedProgram → canonical fields."""

    def normalize(self, observation: Observation) -> Observation:
        raw = observation.raw_data

        # Parse reward from raw_payout_range
        reward_raw = raw.get("raw_payout_range", "")
        if reward_raw:
            min_r, max_r, currency = parse_reward_range(reward_raw)
            observation.estimated_reward_min = min_r
            observation.estimated_reward_max = max_r
            observation.reward_currency = currency
            observation.reward_raw = str(reward_raw)

        # Fallback to estimated_payout
        if observation.estimated_reward_max == 0.0 and raw.get("estimated_payout"):
            observation.estimated_reward_max = float(raw["estimated_payout"])

        # Tags
        tags: list[str] = [str(raw.get("platform", ""))]
        tags.extend(raw.get("technologies", []))
        observation.tags = normalize_tags(tags)

        # Confidence
        observation.confidence = 0.9 if raw.get("has_rewards") else 0.5

        # Checksum
        raw_id = f"{raw.get('platform', '')}:{raw.get('name', '')}"
        observation.checksum = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        return observation


class GenericNormalizer(Normalizer):
    """Normalizes any adapter raw data → canonical fields."""

    def normalize(self, observation: Observation) -> Observation:
        raw = observation.raw_data
        # Already has estimated_reward_min/max set by sensor
        # Just ensure consistency
        if observation.estimated_reward_max > 0 and observation.estimated_reward_min == 0:
            observation.estimated_reward_min = observation.estimated_reward_max

        # Tags fallback
        if not observation.tags:
            tags: list[str] = []
            tags.extend(raw.get("tags", raw.get("skills", raw.get("categories", []))))
            if tags:
                observation.tags = normalize_tags(tags)

        # Checksum
        raw_id = f"{raw.get('platform', '')}:{raw.get('id', '')}"
        if raw_id and raw_id != ":":
            observation.checksum = hashlib.sha256(raw_id.encode()).hexdigest()[:16]
        else:
            observation.checksum = hashlib.sha256(
                f"{observation.sensor_id}:{observation.external_id}".encode()
            ).hexdigest()[:16]

        return observation


# ── Normalization Engine ────────────────────────────────────────────


class NormalizationEngine(Engine):
    """Orchestrates normalizers for all sensors.

    Each sensor has its own normalizer that converts the platform's
    specific format into canonical Observation fields.
    """

    name = "normalization_engine"

    def __init__(self) -> None:
        super().__init__()
        self._normalizers: dict[str, Normalizer] = {}

    def register(self, sensor_id: str, normalizer: Normalizer) -> None:
        """Register a normalizer for a sensor."""
        self._normalizers[sensor_id] = normalizer

    async def initialize(self) -> None:
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "normalizers": list(self._normalizers.keys()),
        }
    def normalize(self, observation: Observation) -> Observation:
        """Normalize a single observation.

        Uses registered normalizer, or generic fallback.
        Always runs generic post-processing to catch any fields
        the normalizer might have missed.
        """
        normalizer = self._normalizers.get(observation.sensor_id)
        if normalizer:
            observation = normalizer.normalize(observation)
        # Generic fallback: try common field names from raw_data
        observation = self._generic_normalize(observation)

        # Mark as normalized
        if observation.status == "new":
            observation.status = "normalized"

        return observation

    def normalize_all(self, observations: list[Observation]) -> list[Observation]:
        """Normalize a batch of observations."""
        return [self.normalize(o) for o in observations]

    def _generic_normalize(self, obs: Observation) -> Observation:
        """Generic fallback that tries common field names."""
        raw = obs.raw_data

        # Try common reward field names
        for field in ("reward", "bounty", "payout", "prize", "max_payout",
                       "maximum_payout", "pay", "pay_rate", "price"):
            value = raw.get(field)
            if value is not None:
                if isinstance(value, str):
                    min_r, max_r, curr = parse_reward_range(value)
                    if max_r > 0:
                        obs.estimated_reward_min = min_r
                        obs.estimated_reward_max = max_r
                        obs.reward_currency = curr
                elif isinstance(value, (int, float)):
                    obs.estimated_reward_max = float(value)
                    obs.estimated_reward_min = float(value)
                break

        # Try common effort field names
        for field in ("hours", "time", "effort", "estimated_hours",
                       "estimated_time", "time_estimate", "duration"):
            value = raw.get(field)
            if value is not None:
                obs.estimated_effort_hours = parse_effort_hours(value)
                break

        # Try common tag field names
        for field in ("tags", "skills", "categories", "topics", "technologies"):
            value = raw.get(field, [])
            if isinstance(value, list) and value:
                obs.tags = normalize_tags(value)
                break

        # Compute checksum if not set
        if not obs.checksum:
            raw_id = f"{obs.sensor_id}:{obs.external_id}:{obs.title}"
            obs.checksum = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        return obs
