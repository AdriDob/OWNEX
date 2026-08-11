from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.request import urlopen

logger = logging.getLogger("catseye.intel.finance")

DOLAR_API_URL = "https://dolarapi.com/v1/dolares"
BLUELYTICS_URL = "https://api.bluelytics.com.ar/v2/latest"
ARGENTINA_DATOS_IPC = "https://api.argentinadatos.com/v1/finanzas/indices/inflacion"

RISK_THRESHOLDS = {
    "dolar_brecha": {"green": 15, "yellow": 30, "red": 50},
    "inflacion_mensual": {"green": 2.0, "yellow": 4.0, "red": 8.0},
    "crypto_volatility": {"green": 30, "yellow": 50, "red": 80},
    "liquidez_ratio": {"green": 0.3, "yellow": 0.15, "red": 0.05},
    "concentracion": {"green": 40, "yellow": 60, "red": 80},
}


@dataclass
class DolarRate:
    nombre: str
    compra: float | None
    venta: float | None
    promedio: float | None
    variacion: float | None
    last_updated: str | None


@dataclass
class InflationData:
    mensual: float | None
    acumulada_anual: float | None
    interanual: float | None
    fuente: str
    last_updated: str | None


@dataclass
class RiskScore:
    overall: int
    label: str
    factors: dict[str, Any]


@dataclass
class Opportunity:
    title: str
    description: str
    action: str
    priority: str
    category: str
    roi_estimate: str
    risk: str


@dataclass
class FinanceIntel:
    timestamp: str
    patrimonio_total: float
    patrimonio_usd: float
    ingresos_mes: float
    objetivo_libertad: float
    objetivo_progreso: float
    dolares: list[DolarRate]
    inflacion: InflationData | None
    crypto_precios: dict[str, float]
    crypto_24h: dict[str, float]
    riesgo: RiskScore
    oportunidades: list[Opportunity]
    health_score: int
    data_sources: list[str]


def _fetch_json(url: str, timeout: int = 10) -> dict | list | None:
    try:
        with urlopen(url, timeout=timeout) as r:
            import json

            return json.loads(r.read().decode())
    except Exception as e:
        logger.debug("fetch failed for %s: %s", url, e)
        return None


def _get_dolares() -> list[DolarRate]:
    rates: list[DolarRate] = []
    data = _fetch_json(DOLAR_API_URL)
    if isinstance(data, list):
        for d in data:
            rates.append(
                DolarRate(
                    nombre=d.get("nombre", d.get("moneda", "?")),
                    compra=d.get("compra"),
                    venta=d.get("venta"),
                    promedio=d.get("promedio"),
                    variacion=d.get("variacion"),
                    last_updated=d.get("fechaActualizacion"),
                )
            )
    if not rates:
        bl = _fetch_json(BLUELYTICS_URL)
        if isinstance(bl, dict):
            for key in ("blue", "oficial", "bolsa", "contadoconliqui"):
                b = bl.get(key)
                if isinstance(b, dict):
                    rates.append(
                        DolarRate(
                            nombre=key,
                            compra=b.get("value_sell"),
                            venta=b.get("value_buy"),
                            promedio=None,
                            variacion=b.get("value_avg"),
                            last_updated=bl.get("last_updated"),
                        )
                    )
    return rates


def _get_inflacion() -> InflationData | None:
    data = _fetch_json(ARGENTINA_DATOS_IPC)
    if isinstance(data, list) and data:
        ultimo = data[-1]
        if isinstance(ultimo, dict):
            valor = ultimo.get("valor")
            return InflationData(
                mensual=float(valor) if valor else None,
                acumulada_anual=None,
                interanual=None,
                fuente="INDEC vía argentinadatos.com",
                last_updated=ultimo.get("fecha"),
            )
    return None


def _compute_risk(
    dolares: list[DolarRate],
    inflacion: InflationData | None,
    patrimonio_usd: float,
    ingresos_mes: float,
) -> RiskScore:
    factors: dict[str, Any] = {}
    scores: list[int] = []

    # Dolar brecha
    blue = next((d for d in dolares if d.nombre.lower() in ("blue", "blue")), None)
    oficial = next((d for d in dolares if d.nombre.lower() in ("oficial", "oficial")), None)
    if blue and oficial and blue.venta and oficial.venta and oficial.venta > 0:
        brecha = ((blue.venta - oficial.venta) / oficial.venta) * 100
        factors["dolar_brecha"] = round(brecha, 1)
        t = RISK_THRESHOLDS["dolar_brecha"]
        if brecha <= t["green"]:
            scores.append(20)
        elif brecha <= t["yellow"]:
            scores.append(50)
        elif brecha <= t["red"]:
            scores.append(70)
        else:
            scores.append(90)

    # Inflacion
    if inflacion and inflacion.mensual is not None:
        factors["inflacion_mensual"] = inflacion.mensual
        t = RISK_THRESHOLDS["inflacion_mensual"]
        if inflacion.mensual <= t["green"]:
            scores.append(15)
        elif inflacion.mensual <= t["yellow"]:
            scores.append(40)
        elif inflacion.mensual <= t["red"]:
            scores.append(65)
        else:
            scores.append(85)

    # Liquidez
    if patrimonio_usd > 0:
        liq_ratio = ingresos_mes / patrimonio_usd if patrimonio_usd else 0
        factors["liquidez_ratio"] = round(liq_ratio, 3)
        t = RISK_THRESHOLDS["liquidez_ratio"]
        if liq_ratio >= t["green"]:
            scores.append(10)
        elif liq_ratio >= t["yellow"]:
            scores.append(40)
        elif liq_ratio >= t["red"]:
            scores.append(70)
        else:
            scores.append(90)

    if not scores:
        scores = [50]

    overall = sum(scores) // len(scores)
    if overall <= 25:
        label = "Bajo"
    elif overall <= 50:
        label = "Moderado"
    elif overall <= 75:
        label = "Elevado"
    else:
        label = "Alto"

    return RiskScore(overall=overall, label=label, factors=factors)


def _generate_opportunities(
    dolares: list[DolarRate],
    riesgo: RiskScore,
    patrimonio_usd: float,
    ingresos_mes: float,
) -> list[Opportunity]:
    ops: list[Opportunity] = []

    # Dolar brecha
    blue = next((d for d in dolares if d.nombre.lower() in ("blue", "blue")), None)
    oficial = next((d for d in dolares if d.nombre.lower() in ("oficial", "oficial")), None)
    ccl = next((d for d in dolares if "ccl" in d.nombre.lower() or "contadoconliqui" in d.nombre.lower()), None)

    if blue and oficial and oficial.venta and blue.venta and oficial.venta > 0:
        brecha = ((blue.venta - oficial.venta) / oficial.venta) * 100
        if brecha < 20:
            ops.append(
                Opportunity(
                    title="Brecha cambiaria baja",
                    description=f"Dólar blue vs oficial: {brecha:.1f}%. Brecha menor a 20% — momento favorable para comprar oficial si necesitás pesos.",
                    action="Evaluar compra de USD oficial",
                    priority="media",
                    category="cambio",
                    roi_estimate="Ahorro de ~15% vs blue",
                    risk="Bajo",
                )
            )

    # Inflacion alta → recomendar activos indexados
    if riesgo.factors.get("inflacion_mensual", 0) > 3:
        ops.append(
            Opportunity(
                title="Inflación elevada",
                description=f"Inflación mensual del {riesgo.factors.get('inflacion_mensual', 0):.1f}%. Considerar activos ajustados por inflación.",
                action="Comprar CER / T-bills o USDC",
                priority="alta",
                category="resguardo",
                roi_estimate="Preserva poder adquisitivo",
                risk="Bajo",
            )
        )

    # Ingresos vs patrimonio
    if patrimonio_usd > 0 and ingresos_mes / patrimonio_usd < 0.1:
        ops.append(
            Opportunity(
                title="Portfolio de bajo rendimiento",
                description=f"Ingresos mensuales ({ingresos_mes:.0f} USD) son <10% del patrimonio ({patrimonio_usd:.0f} USD). Considerar rebalancear.",
                action="Rebalancear cartera",
                priority="media",
                category="inversión",
                roi_estimate="+2-5% rendimiento anual",
                risk="Medio",
            )
        )

    # CCL para sacar dolares
    if ccl and blue and ccl.venta and blue.venta and blue.venta > 0:
        diff = ((blue.venta - ccl.venta) / ccl.venta) * 100
        if abs(diff) < 5:
            ops.append(
                Opportunity(
                    title="Dólar CCL vs Blue alineados",
                    description=f"Brecha CCL/Blue: {diff:.1f}%. Sin arbitraje significativo. Mercado cambiario estable.",
                    action="Monitorear",
                    priority="baja",
                    category="cambio",
                    roi_estimate="Sin oportunidad clara",
                    risk="Bajo",
                )
            )

    if not ops:
        ops.append(
            Opportunity(
                title="Sin oportunidades destacadas",
                description="No se detectaron oportunidades claras en este momento. Seguir monitoreando.",
                action="Seguir monitoreando",
                priority="info",
                category="general",
                roi_estimate="—",
                risk="—",
            )
        )

    return ops


async def get_finance_intel() -> FinanceIntel:
    from cores.crypto.coingecko import get_coingecko_feed
    from cores.financial.dashboard import get_dashboard

    dash = get_dashboard() if callable(get_dashboard) else {}
    feed = get_coingecko_feed()

    patrimonio_total = dash.get("patrimonio_total", 0) if isinstance(dash, dict) else 0
    ingresos_mes = 0
    if isinstance(dash, dict):
        ingresos_raw = dash.get("ingresos", {})
        ingresos_mes = ingresos_raw.get("total", 0) if isinstance(ingresos_raw, dict) else 0

    objetivo = 30000.0
    objetivo_progreso = min((patrimonio_total / objetivo) * 100, 100) if objetivo > 0 else 0

    dolares = _get_dolares()
    inflacion = _get_inflacion()

    crypto_prices = {}
    crypto_24h = {}
    for sym in ("btc", "eth", "sol", "usdc", "ada", "bnb", "doge", "link", "uni", "xrp"):
        try:
            price = feed.get_price(sym)
            if price is not None:
                crypto_prices[sym] = price
        except Exception:
            pass
    for sym in crypto_prices:
        try:
            ch = feed.get_24h_change(sym)
            if ch is not None:
                crypto_24h[sym] = ch
        except Exception:
            pass

    riesgo = _compute_risk(dolares, inflacion, patrimonio_total, ingresos_mes)
    oportunidades = _generate_opportunities(dolares, riesgo, patrimonio_total, ingresos_mes)

    health = 100
    deductions = 0
    if not dolares:
        deductions += 15
    if riesgo.overall > 50:
        deductions += 10
    if not crypto_prices:
        deductions += 10
    health = max(0, health - deductions)

    return FinanceIntel(
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        patrimonio_total=round(patrimonio_total, 2),
        patrimonio_usd=round(patrimonio_total, 2),
        ingresos_mes=round(ingresos_mes, 2),
        objetivo_libertad=objetivo,
        objetivo_progreso=round(objetivo_progreso, 1),
        dolares=dolares,
        inflacion=inflacion,
        crypto_precios=crypto_prices,
        crypto_24h=crypto_24h,
        riesgo=riesgo,
        oportunidades=oportunidades,
        health_score=health,
        data_sources=["dolarapi.com", "bluelytics.com.ar", "argentinadatos.com", "CoinGecko", "ORION Ledger"],
    )
