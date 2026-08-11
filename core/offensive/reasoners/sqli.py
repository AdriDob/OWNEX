from __future__ import annotations

import logging
import re
from typing import Any

from core.offensive.models import EndpointInfo, Hypothesis
from core.offensive.reasoners.base import BaseReasoner
from core.offensive.templates import SQLI_ALTERNATIVES

logger = logging.getLogger("orion.core.offensive.reasoners.sqli")

SQLI_KEYWORDS: dict[str, float] = {
    "id": 0.7,
    "user_id": 0.65,
    "userId": 0.65,
    "category": 0.6,
    "product": 0.55,
    "order": 0.6,
    "search": 0.7,
    "query": 0.7,
    "q": 0.65,
    "filter": 0.6,
    "sort": 0.5,
    "page": 0.4,
    "limit": 0.4,
    "offset": 0.4,
    "where": 0.65,
    "select": 0.7,
    "from": 0.5,
    "table": 0.6,
    "column": 0.55,
    "value": 0.4,
    "username": 0.6,
    "email": 0.6,
    "password": 0.55,
}

NUMERIC_VALUE_PATTERN = re.compile(r"^\d+$")
SQL_ERROR_INDICATORS = re.compile(
    r"SQL syntax|mysql_fetch|ORA-[0-9]|PostgreSQL.*ERROR|"
    r"Warning.*sql|unclosed quotation|Incorrect syntax near|"
    r"SQLite3::|mysql error|driver error|odbc_exec",
    re.IGNORECASE,
)
SQL_INJECTION_PATTERNS = re.compile(r"['\"\\;%]|(--|#|/\*)")


class SQLiReasoner(BaseReasoner):
    @property
    def vulnerability_type(self) -> str:
        return "sqli"

    def supported_methods(self) -> list[str]:
        return ["GET", "POST", "PUT", "PATCH"]

    def analyze(self, endpoint: EndpointInfo) -> list[Hypothesis]:
        signals: list[str] = []
        confidence = 0.0
        params_of_interest: list[str] = []

        # Signal 1: SQL-relevant parameter names
        for pname in endpoint.params:
            score = SQLI_KEYWORDS.get(pname.lower(), 0.0)
            if score >= 0.6:
                signals.append(f"SQL-relevant parameter: {pname}")
                params_of_interest.append(pname)
                confidence += score * 0.3
            elif score >= 0.4:
                signals.append(f"Query parameter that may hit database: {pname}")
                params_of_interest.append(pname)
                confidence += score * 0.2

        # Signal 2: Numeric values in parameters (likely DB lookup)
        for pname, pval in endpoint.params.items():
            if isinstance(pval, str) and NUMERIC_VALUE_PATTERN.match(pval):
                signals.append(f"Numeric value in {pname} — likely database query parameter")
                params_of_interest.append(pname)
                confidence += 0.2

        # Signal 3: SQL injection characters in existing values
        for pname, pval in endpoint.params.items():
            if isinstance(pval, str) and SQL_INJECTION_PATTERNS.search(pval):
                signals.append(f"SQL injection characters found in {pname}")
                params_of_interest.append(pname)
                confidence += 0.35

        # Signal 4: Error-based SQL indicator
        if endpoint.response_sample:
            sample_str = str(endpoint.response_sample)
            if SQL_ERROR_INDICATORS.search(sample_str):
                signals.append("SQL error detected in response — potential SQL injection point")
                confidence += 0.5
            # Check if param values appear in response
            for pname, pval in endpoint.params.items():
                if isinstance(pval, str) and len(pval) > 2 and pval in sample_str:
                    signals.append(f"Parameter {pname} value reflected in response")
                    params_of_interest.append(pname)
                    confidence += 0.15

        # Signal 5: Path-based SQL indicators
        path_lower = endpoint.path.lower()
        if "search" in path_lower or "query" in path_lower:
            signals.append("Search/query path — high likelihood of database interaction")
            confidence += 0.2
        if "api" in path_lower and any(p in path_lower for p in ["user", "product", "order", "item"]):
            signals.append("API resource path with database-backed entity")
            confidence += 0.1

        # Signal 6: POST body with SQL injection potential
        if endpoint.body:
            body_str = str(endpoint.body)
            if SQL_ERROR_INDICATORS.search(body_str):
                signals.append("SQL error detected in request body")
                confidence += 0.4
            body_keys_str = " ".join(str(k) for k in (endpoint.body.keys() if isinstance(endpoint.body, dict) else []))
            for keyword in ["where", "filter", "query", "search"]:
                if keyword in body_keys_str.lower():
                    signals.append(f"SQL-related key in body: {keyword}")
                    confidence += 0.2

        if confidence < 0.1:
            return []

        confidence = min(confidence, 1.0)
        method = endpoint.method.upper()
        severity = self._compute_severity(confidence, method)

        hypothesis = Hypothesis(
            vulnerability_type="sqli",
            endpoint=endpoint.path,
            method=endpoint.method,
            confidence=confidence,
            severity=severity,
            summary=self._build_summary(endpoint, params_of_interest),
            description=self._build_description(endpoint, params_of_interest, method),
            why_human_would_investigate=self._build_triager_justification(
                endpoint, params_of_interest, method, signals
            ),
            parameters_of_interest=params_of_interest,
            signals=signals,
            test_instructions=self._build_test_instructions(endpoint, params_of_interest, method),
            alternative_explanations=self._build_alternatives(),
            scope_check=self._scope_check(endpoint),
            reproducibility_notes=self._reproducibility_notes(method, params_of_interest),
        )

        return [hypothesis]

    def _compute_severity(self, confidence: float, method: str) -> str:
        if confidence >= 0.65:
            return "critical"
        if confidence >= 0.4:
            return "high"
        return "medium"

    def _build_summary(self, endpoint: EndpointInfo, params: list[str]) -> str:
        refs = ", ".join(params[:3])
        return f"Potential SQL injection via {refs} on {endpoint.method} {endpoint.path}"

    def _build_description(self, endpoint: EndpointInfo, params: list[str], method: str) -> str:
        refs = ", ".join(params[:4])
        return (
            f"The endpoint {endpoint.method} {endpoint.path} accepts parameters ({refs}) "
            f"that are likely used in database queries. If input is not properly parameterized, "
            f"an attacker could inject SQL commands to extract, modify, or delete database contents. "
            f"SQL injection can lead to complete data compromise, authentication bypass, "
            f"and in some cases remote code execution."
        )

    def _build_triager_justification(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} uses parameters ({params[0] if params else 'unknown'}) "
            f"that likely interact with a database. The endpoint has {len(signals)} SQL injection "
            f"indicators. SQL injection is one of the highest-impact vulnerabilities."
        )

    def _build_test_instructions(self, endpoint: EndpointInfo, params: list[str], method: str) -> list[str]:
        instructions = []
        for param in params[:2]:
            instructions.extend(
                [
                    f"Try setting {param} to a single quote (') and observe the response for SQL errors.",
                    f"Try setting {param} to ' OR '1'='1 and check for different responses.",
                    f"Try setting {param} to ' AND SLEEP(5)-- for time-based detection.",
                    f"Try setting {param} to ' UNION SELECT NULL-- to enumerate columns.",
                ]
            )
        instructions.append(
            "If direct SQLi is blocked, try: blind SQLi (boolean/time-based), "
            "NoSQL injection ({'$gt': ''}), second-order injection, "
            "and WAF bypass techniques (encoding, case variation, comments)."
        )
        return instructions

    def _build_alternatives(self) -> list[dict[str, Any]]:
        return [
            {"label": alt["label"], "description": alt["description"], "how_to_rule_out": alt["how_to_rule_out"]}
            for alt in SQLI_ALTERNATIVES
        ]

    def _scope_check(self, endpoint: EndpointInfo) -> str:
        return (
            f"Verify that {endpoint.path} is within scope. "
            f"Check if SQL injection is explicitly in scope. "
            f"Confirm time-based testing is permitted (some programs restrict it). "
            f"Verify rate limits that may affect blind SQL injection testing."
        )

    @staticmethod
    def _reproducibility_notes(method: str, params: list[str]) -> str:
        param = params[0] if params else "the parameter"
        return (
            f"Send {method} request with {param}' (single quote appended). "
            f"If the server returns a database error message, SQL injection is likely. "
            f"Then confirm with boolean/time-based techniques. "
            f"Provide exact payload and response for reproduction."
        )

    def _build_triager_rejection(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        rejections = []
        if not endpoint.headers:
            rejections.append("No authentication or authorization headers present")
        if any("time-based" in s for s in signals):
            rejections.append("Complex blind SQLi requires program approval")
        if len(signals) < 2:
            rejections.append("Insufficient SQL injection indicators")
        if method.upper() in ["GET", "POST"] and not any("'" in str(s) for s in signals):
            rejections.append("Basic SQLi blocked by simple input validation")
        return ". ".join(rejections)

    def _build_triager_justification(
        self, endpoint: EndpointInfo, params: list[str], method: str, signals: list[str]
    ) -> str:
        return (
            f"A human triager would investigate this because: "
            f"{endpoint.method} {endpoint.path} uses parameters ({params[0] if params else 'unknown'}) "
            f"that likely interact with a database. The endpoint has {len(signals)} SQL injection "
            f"indicators. SQL injection is one of the highest-impact vulnerabilities."
        )
