from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("catseye.intel.llm")


@dataclass
class LLMProbe:
    name: str
    payload: str
    category: str


@dataclass
class LLMCheck:
    name: str
    passed: bool
    severity: str
    detail: str
    probe: LLMProbe | None = None
    model_response: str | None = None
    remediation: str | None = None


@dataclass
class LLMScanResult:
    endpoint: str
    model: str
    timestamp: str
    checks: list[LLMCheck]
    summary: dict[str, Any]
    methodology: str = "Garak probes via REST/Ollama (real execution)"
    data_sources: list[str] = field(
        default_factory=lambda: [
            "Garak (NVIDIA)",
            "OWASP LLM Top 10 2025",
        ]
    )


def _build_fallback_result(endpoint: str, api_key: str | None = None) -> LLMScanResult:
    """Sin Garak no hay escaneo. Se devuelve `NOT_SCANNED`, no checks falsos.

    Antes devolvía `SIMULATED_CHECKS`, que incluye `model_response`
    inventados: **fabricaba lo que un modelo respondió** sobre el endpoint
    del usuario, con `score` y severidad calculados de checks que nunca
    se ejecutaron. Un "3 fallos altos, 34%" de un escaneo inexistente es
    la forma más cara de mentir en seguridad (misma clase que el pipeline
    de $5.810 y `infinite-sources`, 2026-08-08).
    """
    logger.warning("Garak no disponible: %s NO se escanea", endpoint)
    return LLMScanResult(
        endpoint=endpoint,
        model="NOT_SCANNED",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        checks=[],
        summary={
            "passed": None,
            "failed": None,
            "total": 0,
            "score": None,
            "high_severity": None,
            "medium_severity": None,
            "status": "NOT_SCANNED",
        },
        methodology=(
            "UNKNOWN: Garak no esta instalado, el escaneo NO se ejecuto. "
            "Instalalo con `pip install garak` para escanear de verdad."
        ),
        data_sources=[],
    )


def _garak_check_to_llm_check(garak_result: Any) -> LLMCheck:
    name = garak_result.name or garak_result.target or "Garak probe"
    detected = garak_result.result_type == "vulnerability"
    return LLMCheck(
        name=name,
        passed=not detected,
        severity=garak_result.severity or "medium",
        detail=garak_result.description or garak_result.name or "",
        probe=LLMProbe(name=name, payload="", category="garak"),
        model_response=garak_result.raw if isinstance(garak_result.raw, str) else str(garak_result.evidence or {}),
        remediation="Review probe output and apply mitigations" if detected else None,
    )


async def scan_llm_endpoint(endpoint: str, api_key: str | None = None) -> LLMScanResult:
    try:
        from cores.tools.extra import GarakTool

        tool = GarakTool()
        if tool.is_available():
            model_name = api_key or "gpt-3.5-turbo"
            results = tool.scan_endpoint(endpoint_url=endpoint, model_name=model_name)
            checks = [_garak_check_to_llm_check(r) for r in results]
            if not checks:
                return _build_fallback_result(endpoint, api_key)
            passed = sum(1 for c in checks if c.passed)
            total = len(checks)
            return LLMScanResult(
                endpoint=endpoint,
                model=model_name,
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                checks=checks,
                summary={
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                    "score": round(passed / total * 100) if total else 0,
                    "high_severity": sum(1 for c in checks if not c.passed and c.severity == "high"),
                    "medium_severity": sum(1 for c in checks if not c.passed and c.severity == "medium"),
                },
                methodology="Garak real execution",
            )
    except ImportError:
        logger.info("Garak not installed, using fallback simulation")
    except Exception as exc:
        logger.warning("Garak scan failed, using fallback: %s", exc)

    return _build_fallback_result(endpoint, api_key)


async def scan_local_model(model_name: str = "qwen3-coder:8b") -> LLMScanResult:
    endpoint = f"ollama:{model_name}"
    try:
        from cores.tools.extra import GarakTool

        tool = GarakTool()
        if tool.is_available():
            results = tool.scan_ollama(model_name=model_name, probes=["promptinject", "jailbreak", "leakreplay"])
            checks = [_garak_check_to_llm_check(r) for r in results]
            passed = sum(1 for c in checks if c.passed)
            total = len(checks)
            return LLMScanResult(
                endpoint=endpoint,
                model=model_name,
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                checks=checks,
                summary={
                    "passed": passed,
                    "failed": total - passed,
                    "total": total,
                    "score": round(passed / total * 100) if total else 0,
                    "high_severity": sum(1 for c in checks if not c.passed and c.severity == "high"),
                    "medium_severity": sum(1 for c in checks if not c.passed and c.severity == "medium"),
                },
                methodology="Garak Ollama real execution",
            )
    except ImportError:
        logger.info("Garak not installed, using fallback")
    except Exception as exc:
        logger.warning("Local scan failed, using fallback: %s", exc)

    return _build_fallback_result(endpoint)
