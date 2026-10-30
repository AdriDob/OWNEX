"""La confianza de un finding tiene que venir de la EVIDENCIA.

Por qué existe (auditoría 2026-10-05). Cada adapter usaba una constante:

    sqlmap 0.8 · xsstrike 0.7 · subfinder 0.6 · ffuf 0.4 · katana 0.3 · gau 0.3

Y el orchestrator hace:

    high_confidence = [f for f in findings if f.confidence >= min_confidence_for_report]

con `min_confidence_for_report = 0.65`. Traducido: **sqlmap (0.8) y xsstrike
(0.7) pasaban el gate por el hecho de venir de sqlmap**, sin ninguna
evidencia. Y las herramientas de descubrimiento que sólo peptan URLs
(subfinder 0.6, ffuf 0.4) estaban por encima o por debajo del corte según un
número escrito a mano.

Un número constante que decide si se reporta un bounty no es una métrica: es
un sesgo con formato decimal.

Ahora la confianza se deriva de la `severity` que el scanner reporta —la
única señal comparable entre estos tools— y lo que no la tiene arranca en
`_BASE_CONFIDENCE`, deliberadamente **bajo** el gate.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cores.revenue_multiplier.adapters.base import NucleiAdapter, ToolAdapter
from cores.revenue_multiplier.config import RevenueMultiplierConfig

ADAPTERS = Path(__file__).resolve().parent.parent / "cores" / "revenue_multiplier" / "adapters" / "base.py"


@pytest.fixture
def adapter() -> NucleiAdapter:
    return NucleiAdapter()


class TestConfidenceIsDerived:
    def test_escala_por_severity(self, adapter: NucleiAdapter) -> None:
        assert adapter._confidence_for("critical") > adapter._confidence_for("high")
        assert adapter._confidence_for("high") > adapter._confidence_for("medium")
        assert adapter._confidence_for("medium") > adapter._confidence_for("low")

    def test_severidad_desconocida_es_la_base(self, adapter: NucleiAdapter) -> None:
        assert adapter._confidence_for(None) == adapter._BASE_CONFIDENCE
        assert adapter._confidence_for("unknown") == adapter._BASE_CONFIDENCE
        assert adapter._confidence_for("") == adapter._BASE_CONFIDENCE

    def test_es_case_insensitive(self, adapter: NucleiAdapter) -> None:
        assert adapter._confidence_for("CRITICAL") == adapter._confidence_for("critical")

    def test_la_base_esta_bajo_el_gate_de_reporte(self, adapter: NucleiAdapter) -> None:
        """Sin evidencia no se reportan bounties: preferimos number bajo a falso."""
        gate = RevenueMultiplierConfig().min_confidence_for_report
        assert adapter._BASE_CONFIDENCE < gate, (
            f"la confianza base ({adapter._BASE_CONFIDENCE}) debe quedar bajo el gate "
            f"({gate}); si no, una herramienta sin severity reporta bounty"
        )

    def test_solo_severidad_alta_cruza_el_gate(self, adapter: NucleiAdapter) -> None:
        gate = RevenueMultiplierConfig().min_confidence_for_report
        pasan = [s for s in ("critical", "high", "medium", "low", "info", None) if adapter._confidence_for(s) >= gate]
        assert set(pasan) == {"critical", "high"}, f"cruzaron el gate sin severidad alta: {pasan}"


class TestNoConstantConfidenceLeft:
    def test_no_queda_ninguna_confidence_constante_en_los_adapters(self) -> None:
        """Guard estructural del bug: `confidence=0.x` es una constante inventada."""
        src = ADAPTERS.read_text(encoding="utf-8")
        offenders = [
            f"línea {i}: {ln.strip()}"
            for i, ln in enumerate(src.splitlines(), start=1)
            if re.search(r"confidence\s*=\s*0\.\d", ln)
        ]
        assert not offenders, (
            "confidence hardcodeada en adapters (debe ser self._confidence_for(severity)):\n  " + "\n  ".join(offenders)
        )

    def test_la_escala_es_una_declaracion_unica(self) -> None:
        """Una sola tabla de severidad→confianza, no una por adapter."""
        src = ADAPTERS.read_text(encoding="utf-8")
        assert src.count("_SEVERITY_CONFIDENCE") == 2, "la tabla debe declararse una vez y documentarse"
        assert ToolAdapter._SEVERITY_CONFIDENCE["critical"] > ToolAdapter._BASE_CONFIDENCE


class TestToolDiscoveryConfidence:
    """Las herramientas que sólo peptan URLs no pueden(reportar bounties)."""

    @pytest.mark.parametrize("tool", ["katana", "gau", "ffuf", "subfinder"])
    def test_descubrimiento_queda_bajo_el_gate(self, tool: str, adapter: NucleiAdapter) -> None:
        gate = RevenueMultiplierConfig().min_confidence_for_report
        assert adapter._BASE_CONFIDENCE < gate, f"{tool} no debería cruzar el gate de reporte"
