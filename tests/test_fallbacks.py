"""Fallback chain tests — Income Multiplier Fase F (spec §22)."""

from __future__ import annotations

from cores.direct_work_engine.fallbacks import build_fallback_chain


def _item(rank: int, platform: str, title: str = "T") -> dict:
    return {
        "rank": rank,
        "platform": platform,
        "title": title,
        "opportunity": {"platform": platform, "title": title},
        "expected_cash": {"expected_date": "2026-09-01"},
        "confidence_band": "HIGH",
    }


class TestChainSelection:
    def test_primary_plus_diversified_fallbacks(self) -> None:
        chain = build_fallback_chain(
            [
                _item(1, "outlier"),
                _item(2, "algora"),
                _item(3, "mindrift"),
                _item(4, "alignerr"),
            ]
        )
        assert chain.primary is not None and chain.primary.platform == "outlier"
        assert [f.platform for f in chain.fallbacks] == ["algora", "mindrift", "alignerr"]
        assert all("fallback #" in f.trigger for f in chain.fallbacks)

    def test_same_platform_skipped_as_single_point_of_failure(self) -> None:
        chain = build_fallback_chain([_item(1, "outlier"), _item(2, "outlier"), _item(3, "algora")])
        platforms = [f.platform for f in chain.as_list()]
        assert platforms.count("outlier") == 1
        assert chain.fallbacks[0].platform == "algora"

    def test_max_fallbacks_respected(self) -> None:
        items = [_item(i + 1, f"p{i}") for i in range(6)]
        chain = build_fallback_chain(items)
        assert len(chain.fallbacks) == 3

    def test_ranks_renumbered_in_chain(self) -> None:
        chain = build_fallback_chain([_item(7, "a"), _item(9, "b"), _item(11, "c")])
        assert [e.rank for e in chain.as_list()] == [1, 2, 3]


class TestHonestyEdges:
    def test_empty_input(self) -> None:
        chain = build_fallback_chain([])
        assert chain.primary is None
        assert chain.warnings

    def test_single_item_warns_no_alternatives(self) -> None:
        chain = build_fallback_chain([_item(1, "outlier")])
        assert len(chain.fallbacks) == 0
        assert chain.primary is not None
        assert any("dependencia única" in w for w in chain.warnings)

    def test_does_not_invent_scores(self) -> None:
        """Pure selección: los items entran sin rank → van al final, no se puntúan."""
        chain = build_fallback_chain([_item(99, "zeta"), _item(50, "alpha")])
        assert chain.primary.platform == "alpha"
