"""Smart Mutation Engine.

Generates payload mutations for security testing using four strategies:

  1. Encoding Bypass        → double URL, unicode, case, mixed encoding
  2. HTTP Parameter Pollution → duplicates, array notation, null bytes
  3. Type Confusion          → string↔array, int↔string, null, boolean
  4. WAF Bypass              → comment injection, chunked, newlines,
                               alt content types, case switching

Usage:
    engine = SmartMutationEngine()
    plan = engine.plan("https://example.com/api/user?id=1", "GET", {"id": "1"})
    for mutated_params in plan.mutations_variants:
        # send request with mutated_params
"""

from __future__ import annotations

import logging
import random
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.execution.mutation_engine")


# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class MutationVariant:
    """A single parameter mutation variant."""

    strategy: str  # encoding_bypass | hpp | type_confusion | waf_bypass
    sub_strategy: str  # e.g. double_url_encode, duplicate_param, string_to_array
    params: dict[str, str | list[str]]
    description: str
    expected_behavior: str = ""


@dataclass
class SmartMutationPlan:
    """Complete mutation plan from the Smart Mutation Engine."""

    attack_vector: str = "generic"
    variants: list[MutationVariant] = field(default_factory=list)
    reasoning: str = ""


# ── Helpers ───────────────────────────────────────────────────────────


def _detect_attack_vector(params: dict[str, str], path: str) -> str:
    """Heuristically determine the most likely attack vector."""
    lower_path = path.lower()
    combined = " ".join(params.keys()).lower()

    if "redirect" in combined or "next" in combined or "return" in combined or "url" in combined:
        return "open_redirect"
    if "file" in combined or "path" in combined or "page" in combined or "view" in combined:
        return "path_traversal"
    if "search" in combined or "q" in combined or "query" in combined:
        return "sqli_xss"
    if "id" in combined or "uid" in combined or "user" in combined or "account" in combined:
        return "idor"
    if "url" in combined or "href" in combined or "src" in combined:
        return "ssrf"
    if "role" in combined or "admin" in combined or "permission" in combined:
        return "auth_bypass"
    if "api" in lower_path or "/v1/" in lower_path or "/graphql" in lower_path:
        return "api_security"
    return "generic"


def _param_value_type(value: str) -> str:
    """Classify a param value as int, bool, or string."""
    if value.isdigit():
        return "int"
    if value.lower() in ("true", "false", "0", "1"):
        return "bool"
    return "string"


# ── Strategy engines ──────────────────────────────────────────────────


class EncodingBypassEngine:
    """Encoding-based mutation strategies."""

    @staticmethod
    def double_url_encode(payload: str) -> str:
        """Double URL-encode special characters."""
        return urllib.parse.quote(urllib.parse.quote(payload, safe=""), safe="")

    @staticmethod
    def unicode_normalize(payload: str) -> str:
        """Unicode normalization bypass (e.g. / vs %2F, ' vs %27)."""
        replacements = {
            "/": "%2F",
            "'": "%27",
            '"': "%22",
            "<": "%3C",
            ">": "%3E",
            "=": "%3D",
            "(": "%28",
            ")": "%29",
            "&": "%26",
            "#": "%23",
        }
        for char, encoded in replacements.items():
            payload = payload.replace(char, encoded)
        return payload

    @staticmethod
    def case_swap(payload: str) -> str:
        """Randomly swap case of characters for keyword obfuscation."""
        result = []
        for ch in payload:
            if ch.isalpha() and random.random() < 0.5:
                result.append(ch.swapcase())
            else:
                result.append(ch)
        return "".join(result)

    @staticmethod
    def mixed_encoding(payload: str) -> str:
        """Mix hex encoding with URL encoding."""
        result = []
        for ch in payload:
            if ch.isalpha() and random.random() < 0.3:
                hex_encoded = f"%{ord(ch):02X}"
                result.append(hex_encoded)
            elif ch in ("'", '"', "<", ">", "/") and random.random() < 0.5:
                result.append(urllib.parse.quote(ch, safe=""))
            else:
                result.append(ch)
        return "".join(result)

    @classmethod
    def generate_variants(cls, param: str, value: str) -> list[MutationVariant]:
        """Generate encoding-based mutation variants for a single param."""
        variants: list[MutationVariant] = []
        for suffix, (method, desc) in {
            "_double_encoded": (cls.double_url_encode, "Double URL-encoded"),
            "_unicode": (cls.unicode_normalize, "Unicode normalization"),
            "_case": (cls.case_swap, "Case-swapped"),
            "_mixed": (cls.mixed_encoding, "Mixed encoding"),
        }.items():
            mutated_value = method(value)
            if mutated_value != value:
                variants.append(
                    MutationVariant(
                        strategy="encoding_bypass",
                        sub_strategy=suffix.lstrip("_"),
                        params={param: mutated_value},
                        description=desc,
                        expected_behavior="WAF may miss encoded payload",
                    )
                )
        return variants


class HPPEngine:
    """HTTP Parameter Pollution mutation strategies."""

    @staticmethod
    def generate_duplicate_variants(params: dict[str, str]) -> list[MutationVariant]:
        """Duplicate each param to create HPP variants."""
        variants: list[MutationVariant] = []
        for param, value in params.items():
            variants.append(
                MutationVariant(
                    strategy="hpp",
                    sub_strategy="duplicate_param",
                    params={param: value, f"{param}[dup]": value},
                    description=f"Duplicate param {param}={value}",
                    expected_behavior="Backend may interpret differently",
                )
            )
            null_value = value + "\x00"
            variants.append(
                MutationVariant(
                    strategy="hpp",
                    sub_strategy="null_byte_injection",
                    params={param: null_value},
                    description=f"Null byte injection in {param}",
                    expected_behavior="String truncation or error",
                )
            )
        return variants

    @staticmethod
    def array_notation(params: dict[str, str]) -> list[MutationVariant]:
        """Convert params to array notation (param[])."""
        variants: list[MutationVariant] = []
        for param, value in params.items():
            variants.append(
                MutationVariant(
                    strategy="hpp",
                    sub_strategy="array_notation",
                    params={f"{param}[]": value},
                    description=f"Array notation for {param}",
                    expected_behavior="Type confusion or parameter override",
                )
            )
            # Multiple values as array
            values = value.split(",")
            if len(values) > 1:
                variants.append(
                    MutationVariant(
                        strategy="hpp",
                        sub_strategy="multiple_values",
                        params={param: values},
                        description=f"Multiple values for {param}",
                        expected_behavior="Backend joins or errors",
                    )
                )
        return variants


class TypeConfusionEngine:
    """Type confusion mutation strategies."""

    @staticmethod
    def generate_variants(params: dict[str, str]) -> list[MutationVariant]:
        """Generate type-confusion variants based on value heuristics."""
        variants: list[MutationVariant] = []
        for param, value in params.items():
            vtype = _param_value_type(value)

            if vtype == "int":
                # String confusion
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="int_to_string",
                        params={param: f"{value}x"},
                        description=f"Int→string confusion for {param}",
                        expected_behavior="500 or type coercion",
                    )
                )
                # Overflow
                large_int = "999999999999999999999999999999"
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="integer_overflow",
                        params={param: large_int},
                        description=f"Integer overflow for {param}",
                        expected_behavior="Overflow error or default value",
                    )
                )
                # Negative
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="negative_number",
                        params={param: f"-{value}"},
                        description=f"Negative number for {param}",
                        expected_behavior="Boundary check bypass",
                    )
                )
                # Float
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="float_injection",
                        params={param: f"{value}.0"},
                        description=f"Float injection for {param}",
                        expected_behavior="Type coercion or error",
                    )
                )

            elif vtype == "bool":
                # String confusion for bool params
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="bool_to_string",
                        params={param: f"{value}_"},
                        description=f"Bool→string confusion for {param}",
                        expected_behavior="Backend may treat as false/true",
                    )
                )
                # Null injection
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="null_injection",
                        params={param: "null"},
                        description=f"Null injection for {param}",
                        expected_behavior="SQL NULL or JS null bypass",
                    )
                )

            else:  # string
                # Array injection
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="string_to_array",
                        params={param: [value]},
                        description=f"String→array confusion for {param}",
                        expected_behavior="500 or param ignored",
                    )
                )
                # Null injection
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="null_injection",
                        params={param: value + "\x00"},
                        description=f"Null byte injection for {param}",
                        expected_behavior="String truncation",
                    )
                )
                # Empty string
                variants.append(
                    MutationVariant(
                        strategy="type_confusion",
                        sub_strategy="empty_string",
                        params={param: ""},
                        description=f"Empty string for {param}",
                        expected_behavior="Validation bypass",
                    )
                )

        return variants


class WAFBypassEngine:
    """WAF bypass mutation strategies."""

    SQL_COMMENT_PATTERNS = [
        "/**/",
        "/***/",
        "/*!*/",
        "-- ",
        "#",
        "/*%00*/",
    ]

    @staticmethod
    def comment_injection(payload: str) -> str:
        """Inject SQL comments into payload to break WAF signatures."""
        if len(payload) < 3:
            return payload
        comment = random.choice(WAFBypassEngine.SQL_COMMENT_PATTERNS)
        # Insert comment at a random position
        pos = random.randint(1, len(payload) - 1)
        return payload[:pos] + comment + payload[pos:]

    @staticmethod
    def case_switching(payload: str) -> str:
        """Alternate case for SQL keywords in the payload."""
        keywords = {
            "select",
            "union",
            "from",
            "where",
            "and",
            "or",
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "sleep",
            "benchmark",
            "waitfor",
            "delay",
            "having",
            "group",
            "order",
            "by",
            "limit",
            "exec",
            "execute",
            "xp_cmdshell",
            "load_file",
            "into",
            "outfile",
            "dumpfile",
            "information_schema",
            "char",
            "concat",
            "group_concat",
            "substr",
            "alert",
            "script",
            "onerror",
            "onload",
        }
        result = payload
        for keyword in keywords:
            if keyword in result.lower():
                mutated = "".join(ch.upper() if random.random() < 0.5 else ch.lower() for ch in keyword)
                result = re.sub(rf"\b{keyword}\b", mutated, result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def newline_injection(payload: str) -> str:
        """Inject newlines/carriage returns into payload."""
        insertions = ["\n", "\r", "\r\n", "\\n", "\\r\\n", "%0a", "%0d%0a"]
        sep = random.choice(insertions)
        if len(payload) < 2:
            return payload
        pos = random.randint(1, len(payload) - 1)
        return payload[:pos] + sep + payload[pos:]

    @staticmethod
    def generate_alt_content_types() -> list[tuple[str, str, str]]:
        """Return (content_type, body_template, description)."""
        return [
            ("application/x-www-form-urlencoded", "{}", "Standard form encoding"),
            ("application/json", '{{"input":"{}"}}', "JSON encoding"),
            ("application/xml", "<root><input>{}</input></root>", "XML encoding"),
            (
                "multipart/form-data; boundary=BOUNDARY",
                '--BOUNDARY\r\nContent-Disposition: form-data; name="input"\r\n\r\n{}\r\n--BOUNDARY--\r\n',
                "Multipart encoding",
            ),
            ("text/plain", "{}", "Plain text encoding"),
        ]

    @classmethod
    def generate_variants(cls, param: str, value: str) -> list[MutationVariant]:
        """Generate WAF bypass variants for a single param."""
        variants: list[MutationVariant] = []

        # Comment injection (3 variants)
        for i in range(min(3, len(cls.SQL_COMMENT_PATTERNS))):
            mutated = cls.comment_injection(value)
            if mutated != value:
                variants.append(
                    MutationVariant(
                        strategy="waf_bypass",
                        sub_strategy="comment_injection",
                        params={param: mutated},
                        description=f"SQL comment injection variant {i + 1}",
                        expected_behavior="WAF regex broken",
                    )
                )

        # Case switching
        mutated = cls.case_switching(value)
        if mutated != value:
            variants.append(
                MutationVariant(
                    strategy="waf_bypass",
                    sub_strategy="case_switching",
                    params={param: mutated},
                    description="Case-switched keywords",
                    expected_behavior="WAF case-sensitive regex bypassed",
                )
            )

        # Newline injection (2 variants)
        for _ in range(2):
            mutated = cls.newline_injection(value)
            if mutated != value:
                variants.append(
                    MutationVariant(
                        strategy="waf_bypass",
                        sub_strategy="newline_injection",
                        params={param: mutated},
                        description="Newline/carriage return injection",
                        expected_behavior="WAF line-based parsing bypassed",
                    )
                )

        return variants


# ── Main Engine ───────────────────────────────────────────────────────


class SmartMutationEngine:
    """Orchestrates all mutation strategies to produce enriched MutationPlans."""

    def __init__(self, max_variants_per_endpoint: int = 15):
        self._max_variants = max_variants_per_endpoint
        self._encoding = EncodingBypassEngine()
        self._hpp = HPPEngine()
        self._type_confusion = TypeConfusionEngine()
        self._waf_bypass = WAFBypassEngine()

    def plan(
        self,
        url: str,
        method: str = "GET",
        params: dict[str, str] | None = None,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> SmartMutationPlan:
        """Generate a complete mutation plan for an endpoint."""
        params = params or {}
        headers = headers or {}

        attack_vector = _detect_attack_vector(params, url)
        variants: list[MutationVariant] = []

        for param, value in params.items():
            if not value or len(value) > 500:
                continue

            variants.extend(self._encoding.generate_variants(param, value))
            variants.extend(self._type_confusion.generate_variants(params))
            variants.extend(self._waf_bypass.generate_variants(param, value))

        # HPP variants (only generate once, not per-param)
        variants.extend(self._hpp.generate_duplicate_variants(params))
        variants.extend(self._hpp.array_notation(params))

        # Deduplicate by param key (keep unique param maps)
        seen: set[str] = set()
        unique_variants: list[MutationVariant] = []
        for v in variants:
            key = str(sorted(v.params.items()))
            if key not in seen:
                seen.add(key)
                unique_variants.append(v)

        # Sort by strategy for deterministic ordering
        strategy_order = {"encoding_bypass": 0, "hpp": 1, "type_confusion": 2, "waf_bypass": 3}
        unique_variants.sort(key=lambda v: strategy_order.get(v.strategy, 99))

        limited = unique_variants[: self._max_variants]

        return SmartMutationPlan(
            attack_vector=attack_vector,
            variants=limited,
            reasoning=(
                f"Generated {len(limited)} mutation variants "
                f"({len(unique_variants)} before limit) for "
                f"attack vector '{attack_vector}' across "
                f"{len(params)} parameters"
            ),
        )

    def plan_for_tool(
        self,
        tool_name: str,
        url: str,
        method: str = "GET",
        params: dict[str, str] | None = None,
        body: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> SmartMutationPlan:
        """Generate a mutation plan optimized for a specific tool."""
        plan = self.plan(url, method, params, body, headers)

        if tool_name == "sqlmap":
            filtered = [v for v in plan.variants if v.strategy in ("encoding_bypass", "waf_bypass")]
            plan.variants = filtered[: self._max_variants]
            plan.reasoning += " [sqlmap-optimized: encoding + WAF bypass only]"

        elif tool_name == "dalfox":
            filtered = [
                v
                for v in plan.variants
                if v.sub_strategy in ("double_url_encode", "case_switching", "unicode", "mixed", "newline_injection")
            ]
            plan.variants = filtered[: self._max_variants]
            plan.reasoning += " [dalfox-optimized: XSS-relevant variants only]"

        return plan

    def encode_tamper_command(self, plan: SmartMutationPlan) -> str:
        """Build a sqlmap --tamper command from the mutation plan."""
        tamper_map = {
            "double_url_encode": "between",
            "unicode": "unicode",
            "case_switching": "randomcase",
            "comment_injection": "space2comment",
            "newline_injection": "between",
            "mixed": "multiplespaces",
        }
        tampers: list[str] = []
        seen_tampers: set[str] = set()
        for v in plan.variants:
            tm = tamper_map.get(v.sub_strategy)
            if tm and tm not in seen_tampers:
                seen_tampers.add(tm)
                tampers.append(tm)
        return ",".join(tampers) if tampers else "between,randomcase,space2comment"

    def enrich_evidence(self, plan: SmartMutationPlan) -> dict[str, Any]:
        """Build mutation metadata for inclusion in scan evidence."""
        strategy_counts: dict[str, int] = {}
        for v in plan.variants:
            strategy_counts[v.strategy] = strategy_counts.get(v.strategy, 0) + 1

        return {
            "mutation_engine": True,
            "attack_vector": plan.attack_vector,
            "variants_count": len(plan.variants),
            "strategies": strategy_counts,
            "variants": [
                {
                    "strategy": v.strategy,
                    "sub_strategy": v.sub_strategy,
                    "params": v.params,
                    "description": v.description,
                }
                for v in plan.variants[:5]  # Top 5 for evidence
            ],
        }
