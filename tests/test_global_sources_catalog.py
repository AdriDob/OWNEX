"""Invariants for the canonical source catalog.

``cores/opportunity/global_sources.py`` is the single source of truth for the
curated work sources, and it grew by hand three times before anyone pinned its
shape. Two classes of defect shipped silently that way:

- three sources (Superteam Earn, GitHub bounty labels, Polar) were listed in
  both ``BUG_BOUNTY_SOURCES`` and ``DEV_BOUNTY_SOURCES``, so scans saw them
  twice and per-category counts double-counted them;
- the copies inside ``BUG_BOUNTY_SOURCES`` declared ``category=dev_bounty``,
  which made a category filter disagree with the list the entry lived in.

The tests below fail on both, plus on un-normalized fields (bad urls, unknown
``type``, non-ISO ``last_verified``, tags that are empty/uppercase/repeated,
out-of-range quality scores). They are cheap and they encode the review that
used to be manual.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from cores.opportunity.global_sources import (
    AI_TRAINING_SOURCES,
    BUG_BOUNTY_SOURCES,
    DATA_ENTRY_SOURCES,
    DEV_BOUNTY_SOURCES,
    OpportunityCategory,
    SourceDefinition,
)

#: Every catalog list paired with the category its entries must declare.
CATALOG_LISTS = {
    "bug_bounty": (BUG_BOUNTY_SOURCES, OpportunityCategory.bug_bounty),
    "dev_bounty": (DEV_BOUNTY_SOURCES, OpportunityCategory.dev_bounty),
    "data_entry": (DATA_ENTRY_SOURCES, OpportunityCategory.data_entry),
    "ai_evaluation": (AI_TRAINING_SOURCES, OpportunityCategory.ai_evaluation),
}

#: Documented ``SourceDefinition.type`` values. A new platform kind has to be
#: added here deliberately instead of arriving as a typo or a stray enum value.
DOCUMENTED_TYPES = frozenset({"aggregator", "api", "direct_api", "direct_message", "forum", "job_board", "platform"})

#: Documented ``SourceDefinition.apply_method`` values.
DOCUMENTED_APPLY_METHODS = frozenset({"profile_only", "profile_email"})


def _all_sources() -> list[SourceDefinition]:
    return [s for sources, _ in CATALOG_LISTS.values() for s in sources]


def test_catalog_is_not_empty() -> None:
    assert len(_all_sources()) > 100


@pytest.mark.parametrize("list_name", CATALOG_LISTS)
def test_no_duplicate_names_within_a_list(list_name: str) -> None:
    sources, _ = CATALOG_LISTS[list_name]
    names = [s.name for s in sources]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    assert not duplicates, f"{list_name} repeats {duplicates}"


def test_no_duplicate_names_across_lists() -> None:
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for list_name, (sources, _) in CATALOG_LISTS.items():
        for source in sources:
            owner = seen.get(source.name)
            if owner is not None and owner != list_name:
                collisions.append(f"{source.name} ({owner} + {list_name})")
            seen[source.name] = list_name
    assert not collisions, f"source listed twice: {sorted(set(collisions))}"


@pytest.mark.parametrize("list_name", CATALOG_LISTS)
def test_each_source_declares_the_category_of_its_list(list_name: str) -> None:
    sources, category = CATALOG_LISTS[list_name]
    mismatched = [f"{s.name} -> {s.category}" for s in sources if s.category is not category]
    assert not mismatched, f"{list_name} holds foreign categories: {mismatched}"


@pytest.mark.parametrize("source", _all_sources(), ids=lambda s: s.name)
def test_type_and_apply_method_are_documented(source: SourceDefinition) -> None:
    assert source.type in DOCUMENTED_TYPES, f"{source.name} has type={source.type!r}"
    assert source.apply_method in DOCUMENTED_APPLY_METHODS, f"{source.name} has apply_method={source.apply_method!r}"


@pytest.mark.parametrize("source", _all_sources(), ids=lambda s: s.name)
def test_url_is_absolute_https(source: SourceDefinition) -> None:
    assert source.url.startswith("https://"), f"{source.name} has url={source.url!r}"


@pytest.mark.parametrize("source", _all_sources(), ids=lambda s: s.name)
def test_quality_score_is_a_ratio(source: SourceDefinition) -> None:
    assert 0.0 <= source.quality_score <= 1.0, f"{source.name} has quality_score={source.quality_score!r}"


@pytest.mark.parametrize("source", _all_sources(), ids=lambda s: s.name)
def test_last_verified_is_an_iso_date(source: SourceDefinition) -> None:
    try:
        date.fromisoformat(source.last_verified)
    except ValueError as exc:
        raise AssertionError(f"{source.name} has last_verified={source.last_verified!r} ({exc})") from exc


@pytest.mark.parametrize("source", _all_sources(), ids=lambda s: s.name)
def test_tags_are_lowercase_unique_and_present(source: SourceDefinition) -> None:
    assert source.tags, f"{source.name} has no tags"
    assert all(tag == tag.lower() for tag in source.tags), f"{source.name} has uppercase tags"
    assert all(tag.strip() for tag in source.tags), f"{source.name} has blank tags"
    assert len(source.tags) == len(set(source.tags)), f"{source.name} repeats a tag"


@pytest.mark.parametrize("source", _all_sources(), ids=lambda s: s.name)
def test_descriptive_fields_are_filled(source: SourceDefinition) -> None:
    assert source.description.strip(), f"{source.name} has no description"
    assert source.name == source.name.strip(), f"{source.name!r} has padding"
    assert source.priority >= 0, f"{source.name} has negative priority"


def test_entries_are_immutable() -> None:
    source = _all_sources()[0]
    with pytest.raises(FrozenInstanceError):
        source.name = "mutated"  # type: ignore[misc]
