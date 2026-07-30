from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

LOG = logging.getLogger("ownex.validation.challenger")


@dataclass
class AlternativeExplanation:
    label: str
    description: str
    test_description: str
    confidence_reduction: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "description": self.description,
            "test_description": self.test_description,
            "confidence_reduction": self.confidence_reduction,
        }


@dataclass
class ContradictionTest:
    test_type: str
    description: str
    expected_if_vulnerable: str
    expected_if_not: str
    info_gain: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_type": self.test_type,
            "description": self.description,
            "expected_if_vulnerable": self.expected_if_vulnerable,
            "expected_if_not": self.expected_if_not,
            "info_gain": self.info_gain,
        }


@dataclass
class EnrichedVerdictData:
    alternative_explanations: list[AlternativeExplanation] = field(default_factory=list)
    contradiction_tests: list[ContradictionTest] = field(default_factory=list)
    missing_verifications: list[str] = field(default_factory=list)
    next_best_test: ContradictionTest | None = None
    uncertainty_level: str = "unknown"

    @property
    def uncertainty_penalty(self) -> float:
        mapping = {"baja": 0.0, "media": 0.05, "alta": 0.12, "unknown": 0.03}
        return mapping.get(self.uncertainty_level, 0.03)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alternative_explanations": [a.to_dict() for a in self.alternative_explanations],
            "contradiction_tests": [t.to_dict() for t in self.contradiction_tests],
            "missing_verifications": self.missing_verifications,
            "next_best_test": self.next_best_test.to_dict() if self.next_best_test else None,
            "uncertainty_level": self.uncertainty_level,
            "uncertainty_penalty": self.uncertainty_penalty,
        }


ALTERNATIVES: dict[str, list[dict[str, Any]]] = {
    "idor": [
        {
            "label": "Recurso público",
            "description": "El endpoint podría ser público y mostrar datos de cualquier usuario intencionalmente.",
            "test_description": "Hacer request sin autenticación. Si da 200, el recurso es público.",
            "confidence_reduction": 0.3,
        },
        {
            "label": "Mismo usuario",
            "description": "Ambos perfiles (baseline y probe) podrían pertenecer al mismo usuario real.",
            "test_description": "Verificar que los tokens corresponden a usuarios distintos.",
            "confidence_reduction": 0.15,
        },
        {
            "label": "Permiso delegado",
            "description": "El usuario probe podría tener permiso legítimo (rol, grupo compartido).",
            "test_description": "Probar con usuario de rol inferior o sin permisos explícitos.",
            "confidence_reduction": 0.2,
        },
        {
            "label": "Respuesta genérica",
            "description": "El endpoint podría devolver la misma respuesta para cualquier ID.",
            "test_description": "Probar con ID de recurso inexistente. Si da 200, respuesta genérica.",
            "confidence_reduction": 0.25,
        },
    ],
    "auth_bypass": [
        {
            "label": "Endpoint público",
            "description": "El endpoint podría ser intencionalmente público (login, docs, landing).",
            "test_description": "Verificar documentación o probar con usuario anónimo.",
            "confidence_reduction": 0.3,
        },
        {
            "label": "Cache",
            "description": "La respuesta podría venir de una caché (CDN, proxy), no del backend real.",
            "test_description": "Comparar headers Cache-Control, Age, ETag. Agregar cache-buster.",
            "confidence_reduction": 0.2,
        },
        {
            "label": "Endpoint informativo",
            "description": "Podría ser healthcheck, métricas o documentación sin datos sensibles.",
            "test_description": "Inspeccionar contenido: buscar datos de usuarios reales en la respuesta.",
            "confidence_reduction": 0.15,
        },
        {
            "label": "Mock / stub",
            "description": "El entorno de pruebas puede tener endpoints mock que siempre responden 200.",
            "test_description": "Buscar patrones de datos de prueba en el body (test, dummy, example).",
            "confidence_reduction": 0.25,
        },
    ],
    "ssrf": [
        {
            "label": "URL validation existe",
            "description": "El backend podría validar URLs contra una lista permitida.",
            "test_description": "Probar con URL inválida o dominio inexistente.",
            "confidence_reduction": 0.25,
        },
        {
            "label": "Endpoint proxy esperado",
            "description": "El endpoint podría ser un proxy intencional para funcionalidad legítima.",
            "test_description": "Verificar documentación de la API.",
            "confidence_reduction": 0.2,
        },
        {
            "label": "Restricción de red",
            "description": "El backend podría tener restricciones de red que impidan SSRF externo.",
            "test_description": "Probar con callback a Interactsh o Burp Collaborator.",
            "confidence_reduction": 0.15,
        },
    ],
    "privilege_escalation": [
        {
            "label": "Rol no verificado",
            "description": "El usuario probe podría tener el rol necesario sin verificarse.",
            "test_description": "Inspeccionar claims del token o cookies de sesión.",
            "confidence_reduction": 0.2,
        },
        {
            "label": "Funcionalidad intencional",
            "description": "La acción podría estar permitida para todos los usuarios autenticados.",
            "test_description": "Verificar documentación o probar con usuario de nivel mínimo.",
            "confidence_reduction": 0.25,
        },
    ],
    "data_exposure": [
        {
            "label": "Datos no sensibles",
            "description": "Los datos expuestos podrían ser no sensibles (metadata, agregados).",
            "test_description": "Verificar si los datos permiten identificar a un usuario específico.",
            "confidence_reduction": 0.2,
        },
        {
            "label": "Endpoint público",
            "description": "Podría ser un endpoint público de estadísticas o información general.",
            "test_description": "Probar sin autenticación.",
            "confidence_reduction": 0.3,
        },
    ],
    "business_logic": [
        {
            "label": "Comportamiento esperado",
            "description": "El comportamiento podría ser intencional por diseño del negocio.",
            "test_description": "Verificar documentación funcional.",
            "confidence_reduction": 0.3,
        },
        {
            "label": "Race condition no explotable",
            "description": "La ventana de race condition podría ser demasiado pequeña.",
            "test_description": "Intentar múltiples veces con timing preciso.",
            "confidence_reduction": 0.15,
        },
    ],
}

MISSING_FILTER_MAP: dict[str, dict[str, str]] = {
    "idor": {
        "ownership_boundary": "Ownership",
        "public_endpoint": "Recurso público",
        "uuid": "Recurso inexistente",
    },
    "auth_bypass": {
        "public_endpoint": "Endpoint público",
        "cacheable": "Cache",
    },
}

MISSING_VERIFICATIONS: dict[str, list[str]] = {
    "idor": [
        "Ownership: no se verificó con recurso de otro usuario real",
        "Recurso público: no se descartó que el endpoint sea público",
        "RBAC: no se probó con diferentes roles",
        "Recurso inexistente: no se probó con ID que no existe",
    ],
    "auth_bypass": [
        "Endpoint público: no se verificó intencionalidad pública",
        "Cache: no se descartó respuesta cacheada",
        "Contenido sensible: no se verificó si hay datos de usuarios reales",
    ],
    "ssrf": [
        "URL validation: no se comprobó si el endpoint valida destinos",
        "Callback externo: no se intentó con servicio de callback propio",
        "Restricción de red: no se verificaron límites de red del backend",
    ],
    "privilege_escalation": [
        "Roles: no se verificaron roles alternativos del usuario probe",
        "Funcionalidad: no se confirmó que sea admin-only",
    ],
    "data_exposure": [
        "Sensibilidad: no se verificó si los datos permiten identificar usuarios",
        "Autenticación: no se probó acceso anónimo",
    ],
    "business_logic": [
        "Documentación: no se verificó el diseño esperado",
        "Explotabilidad: no se confirmó que la condición sea explotable repetidamente",
    ],
    "graphql_introspection": [
        "Persistencia: no se verificó si la introspección persiste tras reinicio",
        "Rate limit: no se probó si hay límite de consultas",
    ],
    "file_operation": [
        "Path traversal: no se verificó sanitización de path",
        "Tipo de archivo: no se confirmó restricción de extensión",
    ],
}

INFO_GAIN_ORDER = {"baja": 0, "media": 1, "alta": 2, "muy alta": 3}


class HypothesisChallenger:
    def challenge(
        self,
        vulnerability_type: str,
        vulnerability_vector: str = "",
        signals: dict[str, Any] | None = None,
    ) -> EnrichedVerdictData:
        vt = vulnerability_type.lower()

        alt_list = ALTERNATIVES.get(vt, [])
        if not alt_list:
            alt_list = self._generic_alternatives(vt)

        alternatives = [AlternativeExplanation(**a) for a in alt_list]
        tests = self._design_contradiction_tests(vt, signals or {})
        missing = self._filter_missing_by_signals(vt, signals or {})
        next_test = self._pick_next_best(tests)
        uncertainty = self._compute_uncertainty(alternatives, missing, tests)

        if alternatives or missing or tests:
            LOG.info(
                "Challenger: vt=%s, alternatives=%d, tests=%d, missing=%d, uncertainty=%s",
                vt,
                len(alternatives),
                len(tests),
                len(missing),
                uncertainty,
            )

        return EnrichedVerdictData(
            alternative_explanations=alternatives,
            contradiction_tests=tests,
            missing_verifications=missing,
            next_best_test=next_test,
            uncertainty_level=uncertainty,
        )

    def _design_contradiction_tests(self, vt: str, signals: dict[str, Any]) -> list[ContradictionTest]:
        tests_by_type: dict[str, list[dict[str, Any]]] = {
            "idor": [
                {
                    "test_type": "anonymous_access",
                    "description": "Request sin autenticación al mismo endpoint",
                    "expected_if_vulnerable": "403/401 (requiere auth)",
                    "expected_if_not": "200 (recurso público)",
                    "info_gain": "muy alta",
                },
                {
                    "test_type": "nonexistent_resource",
                    "description": "Request con ID de recurso que no existe",
                    "expected_if_vulnerable": "404 (distingue existencia)",
                    "expected_if_not": "200 (respuesta genérica)",
                    "info_gain": "alta",
                },
                {
                    "test_type": "cross_user",
                    "description": "Request con recurso de otro usuario real",
                    "expected_if_vulnerable": "200 con datos diferentes",
                    "expected_if_not": "403 o 200 con mismos datos",
                    "info_gain": "muy alta",
                },
            ],
            "auth_bypass": [
                {
                    "test_type": "anonymous_access",
                    "description": "Mismo endpoint sin token ni cookie",
                    "expected_if_vulnerable": "401/403 (requiere auth)",
                    "expected_if_not": "200 (público o sin auth)",
                    "info_gain": "muy alta",
                },
                {
                    "test_type": "cache_buster",
                    "description": "Agregar Cache-Control: no-cache + parámetro aleatorio",
                    "expected_if_vulnerable": "respuesta diferente (había caché)",
                    "expected_if_not": "misma respuesta (no hay caché)",
                    "info_gain": "alta",
                },
            ],
            "ssrf": [
                {
                    "test_type": "invalid_url",
                    "description": "Probar con URL malformada o dominio inexistente",
                    "expected_if_vulnerable": "error de validación 400",
                    "expected_if_not": "200 o timeout (intenta resolver)",
                    "info_gain": "alta",
                },
                {
                    "test_type": "callback_test",
                    "description": "Usar URL de callback controlado (Interactsh/Burp Collaborator)",
                    "expected_if_vulnerable": "callback recibido",
                    "expected_if_not": "sin callback",
                    "info_gain": "muy alta",
                },
            ],
            "privilege_escalation": [
                {
                    "test_type": "lower_role",
                    "description": "Probar con token de usuario con rol mínimo",
                    "expected_if_vulnerable": "403 (rol insuficiente denegado)",
                    "expected_if_not": "200 (sin verificación de rol)",
                    "info_gain": "muy alta",
                },
                {
                    "test_type": "header_override",
                    "description": "Probar con X-Forwarded-Role, X-Admin",
                    "expected_if_vulnerable": "sin efecto (backen valida en serio)",
                    "expected_if_not": "200 (backend confía en headers)",
                    "info_gain": "alta",
                },
            ],
            "data_exposure": [
                {
                    "test_type": "anonymous_access",
                    "description": "Request sin autenticación",
                    "expected_if_vulnerable": "401/403",
                    "expected_if_not": "200 (público)",
                    "info_gain": "muy alta",
                },
                {
                    "test_type": "pagination_depth",
                    "description": "Solicitar página 100 o límite alto",
                    "expected_if_vulnerable": "error o datos limitados",
                    "expected_if_not": "todos los datos expuestos",
                    "info_gain": "media",
                },
            ],
        }
        tests = tests_by_type.get(vt, [])
        if not tests:
            tests = self._generic_tests(vt)
        return [ContradictionTest(**t) for t in tests]

    def _filter_missing_by_signals(self, vt: str, signals: dict[str, Any]) -> list[str]:
        all_missing = list(MISSING_VERIFICATIONS.get(vt, []))
        if not all_missing:
            return self._generic_missing(vt)
        prefix_map = MISSING_FILTER_MAP.get(vt, {})
        for signal, prefix in prefix_map.items():
            if signals.get(signal):
                all_missing = [m for m in all_missing if not m.startswith(prefix)]
        return all_missing or self._generic_missing(vt)

    def _generic_alternatives(self, vt: str) -> list[dict[str, Any]]:
        return [
            {
                "label": f"Falso positivo de tipo {vt}",
                "description": "El patrón detectado podría no ser una vulnerabilidad real.",
                "test_description": "Revisar manualmente la lógica del endpoint.",
                "confidence_reduction": 0.2,
            },
            {
                "label": "Comportamiento esperado",
                "description": "El endpoint podría comportarse así por diseño.",
                "test_description": "Verificar documentación del programa.",
                "confidence_reduction": 0.15,
            },
        ]

    def _generic_tests(self, vt: str) -> list[dict[str, Any]]:
        return [
            {
                "test_type": "baseline_confirmation",
                "description": "Repetir prueba baseline para confirmar consistencia",
                "expected_if_vulnerable": "misma respuesta (consistente)",
                "expected_if_not": "respuesta diferente (inconsistente)",
                "info_gain": "media",
            },
            {
                "test_type": "anonymous_access",
                "description": "Request sin autenticación",
                "expected_if_vulnerable": "401/403",
                "expected_if_not": "200 (público)",
                "info_gain": "alta",
            },
        ]

    def _generic_missing(self, vt: str) -> list[str]:
        return [
            f"No se verificaron explicaciones alternativas para {vt}",
            "No se diseñaron contrapruebas específicas para este tipo",
        ]

    def _pick_next_best(self, tests: list[ContradictionTest]) -> ContradictionTest | None:
        if not tests:
            return None
        return max(tests, key=lambda t: INFO_GAIN_ORDER.get(t.info_gain, 0))

    def _compute_uncertainty(
        self,
        alternatives: list[AlternativeExplanation],
        missing: list[str],
        tests: list[ContradictionTest],
    ) -> str:
        score = 0
        if alternatives:
            score += len(alternatives) * 12
        if missing:
            score += len(missing) * 8
        if tests:
            score += len(tests) * 4
        if score < 15:
            return "baja"
        elif score < 35:
            return "media"
        else:
            return "alta"
