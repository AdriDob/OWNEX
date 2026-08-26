"""Tests for Creative Hypothesis Generator."""

import pytest

from cores.engine.hypothesis.creative_generator import (
    _parse_llm_hypotheses,
    _summarize_endpoints,
    generate_creative_hypotheses,
)


class TestCreativeGenerator:
    def test_empty_endpoints_returns_empty(self):
        assert generate_creative_hypotheses(1, "test", [], {}) == []

    def test_parse_valid_json_hypotheses(self):
        text = """[{"title": "IDOR on /api/users", "vulnerability_type": "business_logic",
                   "endpoint": "/api/users/123", "method": "GET",
                   "likelihood": 0.8, "impact": 0.9,
                   "reasoning": "test", "suggested_test": "try other IDs"}]"""
        result = _parse_llm_hypotheses(text, 1, "target1")
        assert len(result) == 1
        assert result[0].likelihood == 0.8

    def test_parse_malformed_json_returns_empty(self):
        assert _parse_llm_hypotheses("not json at all", 1, "t") == []
        assert _parse_llm_hypotheses('{"key": "not array"}', 1, "t") == []

    def test_parse_wrapped_in_code_block(self):
        text = '```json\n[{"title": "Test", "vulnerability_type": "auth_chain", "endpoint": "/", "method": "POST", "likelihood": 0.7, "impact": 0.8, "reasoning": "r", "suggested_test": "t"}]\n```'
        result = _parse_llm_hypotheses(text, 1, "t")
        assert len(result) == 1

    def test_summarize_endpoints(self):
        eps = [
            {"path": "/api/users", "method": "GET", "params": ["id"]},
            {"path": "/api/orders", "method": "POST"},
        ]
        summary = _summarize_endpoints(eps)
        assert "GET /api/users" in summary
        assert "POST /api/orders" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
