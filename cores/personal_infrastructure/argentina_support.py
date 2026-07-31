"""Argentina/ARCA Specific Support - Soporte Específico para Argentina.

Proporciona información y guías específicas para el contexto fiscal y legal
argentino, incluyendo AFIP, CUIT/CUIL, Monotributo, Responsable Inscripto, etc.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.personal_infrastructure.argentina_support")


class AFIPCategory(StrEnum):
    """Categorías AFIP."""
    MONOTRIBUTISTA = "monotributista"
    RESPONSABLE_INSCRIPTO = "responsable_inscripto"
    EXENTO = "exento"
    NO_REGISTRADO = "no_registrado"


class IncomeCategoryAR(StrEnum):
    """Categorías de ingresos para Argentina."""
    SERVICIOS_DIGITALES = "servicios_digitales"
    BUG_BOUNTY = "bug_bounty"
    FREELANCE = "freelance"
    INVERSIONES = "inversiones"
    HONORARIOS = "honorarios"


@dataclass
class ArgentinaTaxInfo:
    """Información fiscal argentina."""
    category: AFIPCategory
    cuit: str | None = None
    cuil: str | None = None
    registration_date: datetime | None = None
    tax_rate: float = 0.0
    iva_rate: float = 0.0
    ganancias_rate: float = 0.0


@dataclass
class ArgentinaRecommendation:
    """Recomendación específica para Argentina."""
    title: str
    description: str
    category: str  # fiscal, legal, operational
    priority: str  # high, medium, low
    action_required: str
    afip_related: bool = False


class ArgentinaSupport:
    """Soporte específico para Argentina."""

    def __init__(self):
        self.tax_info: ArgentinaTaxInfo | None = None
        self.recommendations: list[ArgentinaRecommendation] = []

    def get_tax_category_explanation(self, category: AFIPCategory) -> dict[str, Any]:
        """Obtener explicación de categoría fiscal."""
        explanations = {
            AFIPCategory.MONOTRIBUTISTA: {
                "title": "Monotributista",
                "description": "Régimen simplificado para pequeños contribuyentes. Pago mensual fijo que incluye impuestos, obra social y prepaga.",
                "annual_limit": "Ingresos anuales hasta ~$12M (valor actualizado)",
                "tax_rate": "8-11% de ingresos anuales (según categoría)",
                "advantages": [
                    "Simplicidad administrativa",
                    "Pago mensual fijo",
                    "Incluye obra social y prepaga",
                    "Facturación simplificada",
                ],
                "disadvantages": [
                    "Límite de ingresos anuales",
                    "No permite crédito fiscal por IVA",
                    "No permite deducir gastos",
                ],
                "ideal_for": [
                    "Ingresos anuales < $12M",
                    "Personas físicas",
                    "Actividades unipersonales",
                    "Simplicidad administrativa preferida",
                ],
            },
            AFIPCategory.RESPONSABLE_INSCRIPTO: {
                "title": "Responsable Inscripto",
                "description": "Régimen general para contribuyentes. Declaración mensual de IVA y anual de Ganancias.",
                "annual_limit": "Sin límite de ingresos",
                "tax_rate": "IVA 21% + Ganancias (escala progresiva 5-35%)",
                "advantages": [
                    "Sin límite de ingresos",
                    "Crédito fiscal por IVA",
                    "Deducción de gastos",
                    "Permite facturar a grandes empresas",
                ],
                "disadvantages": [
                    "Complejidad administrativa",
                    "Declaraciones mensuales y anuales",
                    "Requiere contador recomendado",
                    "Más controles de AFIP",
                ],
                "ideal_for": [
                    "Ingresos anuales > $12M",
                    "Actividades con IVA significativo",
                    "Deseo de facturar a grandes empresas",
                    "Capacidad de contratar contador",
                ],
            },
            AFIPCategory.EXENTO: {
                "title": "Exento",
                "description": "Categoría para actividades exentas de ciertos impuestos (común para exportaciones de servicios).",
                "annual_limit": "Sin límite de ingresos",
                "tax_rate": "0% IVA (exportaciones), Ganancias según caso",
                "advantages": [
                    "No paga IVA en exportaciones",
                    "Competitividad internacional",
                    "Simplificación fiscal parcial",
                ],
                "disadvantages": [
                    "Requisitos específicos de exportación",
                    "Moneda extranjera",
                    "Cumplimiento adicional",
                ],
                "ideal_for": [
                    "Clientes internacionales",
                    "Exportación de servicios",
                    "Ingresos en moneda extranjera",
                ],
            },
        }

        return explanations.get(category, {})

    def get_recommendation_for_income(self, annual_income_usd: float) -> ArgentinaRecommendation:
        """Obtener recomendación basada en ingresos anuales."""
        if annual_income_usd < 10000:
            return ArgentinaRecommendation(
                title="Considerar Monotributista",
                description=f"Con ingresos anuales de ${annual_income_usd:.0f} USD, el Monotributo puede ser la opción más conveniente por simplicidad.",
                category="fiscal",
                priority="high",
                action_required="Consultar con contador sobre categoría Monotributista",
                afip_related=True,
            )
        elif annual_income_usd < 50000:
            return ArgentinaRecommendation(
                title="Evaluar Monotributo vs Responsable Inscripto",
                description=f"Con ingresos anuales de ${annual_income_usd:.0f} USD, ambas categorías son viables. Evalúa complejidad vs beneficios.",
                category="fiscal",
                priority="medium",
                action_required="Consultar con contador para análisis comparativo",
                afip_related=True,
            )
        else:
            return ArgentinaRecommendation(
                title="Recomendado Responsable Inscripto",
                description=f"Con ingresos anuales de ${annual_income_usd:.0f} USD, el Responsable Inscripto es recomendado por flexibilidad y escalabilidad.",
                category="fiscal",
                priority="high",
                action_required="Consultar con contador para registro como Responsable Inscripto",
                afip_related=True,
            )

    def get_services_digital_tax_guide(self) -> dict[str, Any]:
        """Obtener guía para servicios digitales en Argentina."""
        return {
            "title": "Guía Fiscal para Servicios Digitales en Argentina",
            "description": "Información clave para profesionales de tecnología que prestan servicios digitales.",
            "key_points": [
                {
                    "point": "Exportación de Servicios",
                    "detail": "Los servicios digitales exportados a clientes del exterior están exentos de IVA (Decreto 2633/92).",
                    "benefit": "Competitividad: sin IVA, tus precios son más competitivos internacionalmente.",
                },
                {
                    "point": "Moneda Extranjera",
                    "detail": "Debes facturar en moneda extranjera (USD, EUR) para exportaciones.",
                    "benefit": "Protección contra devaluación y mayor estabilidad.",
                },
                {
                    "point": "Registración de Exportador",
                    "detail": "Debes registrarte como exportador de servicios en AFIP (Formulario 413/F).",
                    "benefit": "Cumplimiento legal y acceso a beneficios fiscales.",
                },
                {
                    "point": "Retenciones de Ganancias",
                    "detail": "Clientes extranjeros pueden retener Ganancias (generalmente 0-35% según convenios).",
                    "benefit": "Argentina tiene convenios de doble imposición que reducen retenciones.",
                },
                {
                    "point": "Monotributo vs Responsable Inscripto",
                    "detail": "Evaluación según ingresos anuales y complejidad deseada.",
                    "benefit": "Elige la categoría que mejor se adapte a tu situación.",
                },
            ],
            "warning": "Esta información es educativa. Consulta siempre con un contador matriculado para tu situación específica.",
        }

    def get_argentina_specific_processes(self) -> list[dict[str, Any]]:
        """Obtener procesos administrativos específicos para Argentina."""
        return [
            {
                "process_id": "afip_registration",
                "title": "Registro en AFIP",
                "objective": "Obtener CUIT/CUIL y categoría fiscal",
                "steps": [
                    {
                        "step": "Obtener Clave Fiscal",
                        "description": "Solicitar Clave Fiscal Nivel 3 o superior en AFIP",
                        "why": "Necesario para realizar trámites online",
                        "where": "Sitio web de AFIP",
                    },
                    {
                        "step": "Determinar Categoría",
                        "description": "Consultar con contador para determinar categoría fiscal (Monotributo/RI)",
                        "why": "La categoría determina tus obligaciones fiscales",
                        "where": "Contador matriculado",
                    },
                    {
                        "step": "Registrar como Exportador",
                        "description": "Completar Formulario 413/F para exportación de servicios",
                        "why": "Necesario para exportación de servicios con exención de IVA",
                        "where": "Sitio web de AFIP con Clave Fiscal",
                    },
                ],
            },
            {
                "process_id": "wise_argentina",
                "title": "Configurar Wise para Argentina",
                "objective": "Recibir pagos internacionales en Argentina",
                "steps": [
                    {
                        "step": "Crear cuenta Wise",
                        "description": "Registrarse en Wise con datos personales",
                        "why": "Wise tiene mejores tasas para transferencias a Argentina",
                        "where": "Sitio web de Wise",
                    },
                    {
                        "step": "Verificar identidad",
                        "description": "Subir DNI y selfie para verificación",
                        "why": "Requisito para activar cuenta y recibir pagos",
                        "where": "App de Wise",
                    },
                    {
                        "step": "Conectar cuenta bancaria",
                        "description": "Vincular cuenta bancaria argentina (CBU/CVU)",
                        "why": "Para retirar fondos a pesos argentinos",
                        "where": "App de Wise",
                    },
                    {
                        "step": "Configurar CBU/CVU",
                        "description": "Usar CVU preferiblemente (transferencias gratuitas)",
                        "why": "CVU tiene comisiones más bajas que CBU tradicional",
                        "where": "Banco o billetera virtual",
                    },
                ],
            },
            {
                "process_id": "bookkeeping_argentina",
                "title": "Sistema de Contabilidad Argentina",
                "objective": "Organizar contabilidad para cumplimiento fiscal argentino",
                "steps": [
                    {
                        "step": "Registrar todos los ingresos",
                        "description": "Registrar cada ingreso con fecha, cliente, monto en ARS",
                        "why": "Necesario para declaración de impuestos",
                        "where": "Excel, software contable o Wise Assistant",
                    },
                    {
                        "step": "Registrar gastos deducibles",
                        "description": "Registrar gastos relacionados con actividad (software, hardware, internet)",
                        "why": "Gastos deducibles reducen base imponible de Ganancias",
                        "where": "Excel, software contable o Wise Assistant",
                    },
                    {
                        "step": "Separar retenciones",
                        "description": "Registrar retenciones de clientes extranjeros",
                        "why": "Retenciones pueden ser crédito fiscal en Ganancias",
                        "where": "Comprobantes de retención",
                    },
                    {
                        "step": "Generar reporte mensual",
                        "description": "Resumen mensual de ingresos, gastos, retenciones",
                        "why": "Para entrega a contador y control interno",
                        "where": "Wise Assistant > Reportes",
                    },
                ],
            },
        ]

    def get_tax_calendar(self, year: int) -> list[dict[str, Any]]:
        """Obtener calendario fiscal para Argentina."""
        return [
            {
                "month": 1,
                "deadline": "20/01",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de enero",
            },
            {
                "month": 2,
                "deadline": "20/02",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de febrero",
            },
            {
                "month": 3,
                "deadline": "20/03",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de marzo",
            },
            {
                "month": 4,
                "deadline": "20/04",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de abril",
            },
            {
                "month": 5,
                "deadline": "20/05",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de mayo",
            },
            {
                "month": 6,
                "deadline": "20/06",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de junio",
            },
            {
                "month": 7,
                "deadline": "20/07",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de julio",
            },
            {
                "month": 8,
                "deadline": "20/08",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de agosto",
            },
            {
                "month": 9,
                "deadline": "20/09",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de septiembre",
            },
            {
                "month": 10,
                "deadline": "20/10",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de octubre",
            },
            {
                "month": 11,
                "deadline": "20/11",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de noviembre",
            },
            {
                "month": 12,
                "deadline": "20/12",
                "tax": "Monotributo / IVA / Ganancias",
                "description": "Vencimiento de impuestos de diciembre",
            },
        ]

    def get_warning_for_bug_bounty(self) -> dict[str, Any]:
        """Obtener advertencia específica para bug bounty en Argentina."""
        return {
            "title": "Consideraciones Fiscales para Bug Bounty en Argentina",
            "description": "El bug bounty tiene implicaciones fiscales específicas en Argentina.",
            "points": [
                {
                    "point": "Clasificación de Ingresos",
                    "detail": "Los pagos de bug bounty se consideran ingresos por servicios digitales.",
                    "implication": "Deben declararse como ingresos de la categoría fiscal correspondiente.",
                },
                {
                    "point": "Plataformas Extranjeras",
                    "detail": "HackerOne, Bugcrowd, etc. son plataformas extranjeras.",
                    "implication": "Sujetas a retenciones de Ganancias según país de origen.",
                },
                {
                    "point": "Retenciones",
                    "detail": "Estados Unidos puede retener hasta 30% (convenio doble imposición reduce a 10-15%).",
                    "implication": "Retenciones pueden ser crédito fiscal en Argentina.",
                },
                {
                    "point": "Declaración Anual",
                    "detail": "Debes declarar todos los ingresos de bug bounty en Ganancias.",
                    "implication": "AFIP puede auditar inconsistencias entre plataformas y declaraciones.",
                },
                {
                    "point": "Facturación",
                    "detail": "Las plataformas extranjeras no requieren factura Argentina.",
                    "implication": "Debes conservar comprobantes de pago y retenciones.",
                },
            ],
            "recommendation": "Consulta con un contador especializado en ingresos digitales para asegurar cumplimiento fiscal.",
        }


# Singleton instance
_argentina_support: ArgentinaSupport | None = None


def get_argentina_support() -> ArgentinaSupport:
    """Obtener instancia singleton del Argentina Support."""
    global _argentina_support
    if _argentina_support is None:
        _argentina_support = ArgentinaSupport()
    return _argentina_support


def reset_argentina_support() -> None:
    """Resetear instancia singleton."""
    global _argentina_support
    _argentina_support = None
