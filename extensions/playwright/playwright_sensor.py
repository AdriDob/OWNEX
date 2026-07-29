"""PlaywrightSensor — sensor para escanear páginas web con Playwright.

Genera una observación por cada descubrimiento relevante (ciertos patrones,
lenguajes, tendencias) encontrado al navegar por páginas seleccionadas.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.sensors.base import Sensor
from core.sensors.observation import Observation
from extensions.playwright.playwright_provider import get_playwright_provider

logger = logging.getLogger("ownex.sensors.playwright_sensor")


class PlaywrightSensor(Sensor):
    """Sensor que usa Playwright para explorar páginas web.

        Descubre contenido de interés: patrones de seguridad, lenguajes, frameworks,
    tecnologías emergentes desde las páginas web monitorizadas.
    """

    id = "playwright_sensor"
    name = "Playwright Web Scraper Sensor"
    source_type = "web_scan"
    source_name = "playwright"
    cadence_seconds = 300  # cada 5 minutos por defecto

    def __init__(self) -> None:
        super().__init__()
        self._provider = None
        self._last_heartbeat = 0.0
        self._heartbeat_interval = 60.0  # 1 minuto
        self._event_bus = None

    async def initialize(self) -> None:
        """Inicializa el sensor y su proveedor."""
        try:
            # Obtener PlaywrightProvider usando la fábrica
            self._provider = await get_playwright_provider()
            logger.info("[PLAYWRIGHT_SENSOR] Inicializado con proveedor: %s", type(self._provider).__name__)

            # Registrar self en el CapabilityRegistry
            try:
                from core.capabilities.registry import get_capability_registry

                reg = get_capability_registry()
                reg.register(
                    "playwright_provider",
                    "playwright_sensor",
                    {"type": "web_scraper", "capabilities": ["analyze_page", "get_target_urls", "get_stats"]},
                    description="Playwright web scraping provider",
                )
                logger.info("[PLAYWRIGHT_SENSOR] Registrado en CapabilityRegistry")
            except Exception as exc:
                logger.warning("[PLAYWRIGHT_SENSOR] Error registrando CapabilityRegistry: %s", exc)

            self._last_heartbeat = asyncio.get_running_loop().time()
            self._running = True
            logger.info("[PLAYWRIGHT_SENSOR] Inicialización completada")

        except Exception as exc:
            logger.error("[PLAYWRIGHT_SENSOR] Error al inicializar: %s", exc)
            self._last_error = str(exc)
            raise

    async def fetch(self) -> list[Observation]:
        """Obtiene observaciones desde las páginas objetivo del proveedor."""
        if not self._provider:
            logger.warning("[PLAYWRIGHT_SENSOR] Proveedor no inicializado")
            return []

        try:
            self._fetch_count += 1
            self._last_fetch = asyncio.get_running_loop().time()

            # Obtener URLs objetivo desde el proveedor
            target_urls = getattr(self._provider, "target_urls", [])
            if not target_urls:
                logger.debug("[PLAYWRIGHT_SENSOR] No hay URLs objetivo configuradas")
                return []

            observations = []
            for url in target_urls:
                try:
                    # Usar el proveedor para analizar la página
                    page_data = await self._provider.analyze_page(url)
                    if not page_data:
                        continue

                    # Convertir datos de página a observaciones
                    page_observations = self._page_to_observations(url, page_data)
                    observations.extend(page_observations)
                    logger.debug("[PLAYWRIGHT_SENSOR] Obtenidas %d observaciones de %s", len(page_observations), url)

                except Exception as exc:
                    logger.warning("[PLAYWRIGHT_SENSOR] Error analizando %s: %s", url, exc)

            # Publicar evento de sensor
            try:
                from cores.events.event_bus import get_event_bus

                bus = get_event_bus()
                bus.publish(
                    "sensor:playwright:completed",
                    {
                        "sensor_id": self.id,
                        "observations_count": len(observations),
                        "urls_scanned": len(target_urls),
                        "timestamp": self._last_fetch,
                    },
                )
            except Exception:
                logger.debug("[PLAYWRIGHT_SENSOR] EventBus no disponible")

            return observations

        except Exception as exc:
            logger.error("[PLAYWRIGHT_SENSOR] Error en fetch: %s", exc)
            self._last_error = str(exc)
            return []

    def _page_to_observations(self, url: str, page_data: dict[str, Any]) -> list[Observation]:
        """Convierte datos de página a observaciones OWNEX."""
        observations = []

        # Extraer temas de seguridad
        security_findings = page_data.get("security_patterns", [])
        for finding in security_findings:
            obs = Observation(
                id=f"{self.id}:{url}:{finding.get('hash', 'sec')}",
                sensor_id=self.id,
                external_id=f"{url}:{finding.get('hash', 'sec')}",
                title=f"Padrón de seguridad encontrado: {finding.get('type', 'unknown')}",
                description=f"Detectado en {url}: {finding.get('details', '')}",
                raw_data={"url": url, "pattern": finding, "type": "security"},
                source_type="web_scan",
                source_name="playwright",
                estimated_reward_min=0.0,
                estimated_reward_max=1000.0,
                estimated_effort_hours=0.5,
                tags=["security", "web_scrape", "pattern"],
                confidence=0.8 if finding.get("severity") == "high" else 0.5,
            )
            observations.append(obs)

        # Extraer lenguajes/frameworks detectados
        tech_stack = page_data.get("technologies", {})
        for tech, version in tech_stack.items():
            obs = Observation(
                id=f"{self.id}:{url}:{tech}:{version}",
                sensor_id=self.id,
                external_id=f"{url}:{tech}:{version}",
                title=f"Tecnología detectada: {tech}",
                description=f"Versión {version} encontrada en {url}",
                raw_data={"url": url, "technology": tech, "version": version},
                source_type="web_scan",
                source_name="playwright",
                estimated_reward_min=0.0,
                estimated_reward_max=500.0,
                estimated_effort_hours=0.25,
                tags=["technology", "stack", tech],
                confidence=0.9,
            )
            observations.append(obs)

        # Extraer tendencias emergentes (título, meta, links)
        trends = page_data.get("trending_topics", [])
        for trend in trends:
            obs = Observation(
                id=f"{self.id}:{url}:trend:{trend.get('hash', 'trend')}",
                sensor_id=self.id,
                external_id=f"{url}:trend:{trend.get('hash', 'trend')}",
                title=f"Tema emergente: {trend.get('title', 'sin título')}",
                description=f"Encontrado en {url}",
                raw_data={"url": url, "trend": trend},
                source_type="web_scan",
                source_name="playwright",
                estimated_reward_min=100.0,
                estimated_reward_max=2000.0,
                estimated_effort_hours=1.0,
                tags=["trend", "emerging", "web"],
                confidence=0.7,
            )
            observations.append(obs)

        return observations

    async def stop(self) -> None:
        """Detiene el sensor."""
        try:
            if self._provider and hasattr(self._provider, "cleanup"):
                await self._provider.cleanup()
            self._running = False
            logger.info("[PLAYWRIGHT_SENSOR] Detenido")
        except Exception as exc:
            logger.error("[PLAYWRIGHT_SENSOR] Error deteniendo: %s", exc)
