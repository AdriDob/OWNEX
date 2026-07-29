"""PlaywrightProvider — proveedor centralizado que abstrae la lógica de Playwright
para uso desde sensores, auditoría y análisis directo.

Singleton para asegurar una sola instancia de navegador por proceso.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from playwright.async_api import async_playwright

logger = logging.getLogger("ownex.playwright_provider")

_PLAYWRIGHT_PROVIDER: PlaywrightProvider | None = None


class PlaywrightProvider:
    """Proveedor reusable de Playwright con thimdpool, conectividad automática,
    cache de páginas, y detección de interés basada en patterns.
    """

    def __init__(self, max_concurrent: int = 3) -> None:
        self._playwright = None
        self._browser = None
        self._page = None
        self._context = None
        self._max_concurrent = max_concurrent

        # Cache de páginas analizadas (clave: URL hash → datos)
        self._page_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl = 1800  # 30 minutos

        # Contador de scans exitosos y fallos
        self._scan_count = 0
        self._failure_count = 0
        self._target_urls: list[str] = [
            "https://github.com/facebook/react",
            "https://github.com/tenderlove/rails-guides",
            "https://github.com/golang/go",
            "https://pypi.org/project/flask/",
            "https://pypi.org/project/django/",
        ]

    async def __aenter__(self) -> PlaywrightProvider:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.cleanup()

    async def initialize(self) -> None:
        """Inicializa el navegador Playwright si no está ya."""
        if self._playwright is None:
            try:
                self._playwright = async_playwright()
                self._playwright_instance = self._playwright.__aenter__()
                self._browser = await self._playwright_instance
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                )
                self._page = await self._context.new_page()
                logger.info("[PLAYWRIGHT_PROVIDER] Navegador inicializado")
            except Exception as exc:
                logger.error("[PLAYWRIGHT_PROVIDER] Falló la inicialización: %s", exc)
                await self.cleanup()
                raise

    async def cleanup(self) -> None:
        """Libera todos los recursos de Playwright."""
        try:
            if self._page:
                await self._page.close()
                self._page = None
            if self._context:
                await self._context.close()
                self._context = None
            if hasattr(self, "_playwright_instance") and self._browser:
                await self._playwright_instance.__aexit__(None, None, None)
                self._browser = None
            self._playwright = None
            logger.info("[PLAYWRIGHT_PROVIDER] Recursos liberados")
        except Exception as exc:
            logger.warning("[PLAYWRIGHT_PROVIDER] Error durante limpieza: %s", exc)

    async def analyze_page(self, url: str, wait_for_network: bool = True) -> dict[str, Any] | None:
        """Analiza una única URL y devuelve signos de interés estructurados.

        Solo mantiene datos relevantes para el pipeline de inteligencia de OWNEX:
        patterns de seguridad, stack tecnológico, temas emergentes.
        """
        if not self._page:
            await self.initialize()

        cache_key = hashlib.md5(url.encode()).hexdigest()
        now = asyncio.get_running_loop().time()

        # Verificar cache
        cached = self._page_cache.get(cache_key)
        if cached and (now - cached.get("_fetched_at", 0)) < self._cache_ttl:
            logger.debug("[PLAYWRIGHT_PROVIDER] Usando cache para %s", url)
            return cached

        try:
            logger.debug("[PLAYWRIGHT_PROVIDER] Analizando %s", url)
            await self._page.goto(
                url, wait_until="networkidle" if wait_for_network else "domcontentloaded", timeout=30000
            )

            # Esperar renderizado inicial
            await self._page.wait_for_timeout(1000)

            # Extraer título
            title = await self._page.title()

            # Extraer meta tags relevantes
            meta_tags = await self._page.evaluate("""
                () => {
                    const tags = {};
                    document.querySelectorAll('meta[name="keywords"], meta[property="og:title"], meta[property="description"]').forEach(m => {
                        const name = m.getAttribute('name') || m.getAttribute('property') || 'unknown';
                        if (m.content) tags[name] = m.content.substring(0, 200);
                    });
                    return tags;
                }
            """)

            # Detectar frameworks por href/link/etc.
            tech_stack = await self._page.evaluate("""
                () => {
                    const techs = {};
                    document.querySelectorAll('script[src], link[rel="stylesheet"], meta[content*="generator"').forEach(el => {
                        const src = el.getAttribute('src') || el.getAttribute('content');
                        if (!src) return;
                        if (src.includes('react')) techs['React'] = 'detected';
                        else if (src.includes('vue')) techs['Vue'] = 'detected';
                        else if (src.includes('angular')) techs['Angular'] = 'detected';
                        else if (src.includes('webpack') || src.includes('vite')) techs['Build Tool'] = 'detected';
                        else if (src.includes('bootstrap')) techs['Bootstrap'] = 'detected';
                    });
                    return techs;
                }
            """)

            # Patterns de seguridad simples (título/texto que contiene keywords)
            page_text = await self._page.evaluate("() => document.body.innerText.toLowerCase()")
            security_patterns = []
            if "sql" in page_text and "injection" in page_text:
                security_patterns.append(
                    {"type": "sql_injection", "severity": "high", "details": "Posible mención de SQLi"}
                )
            if "xss" in page_text:
                security_patterns.append({"type": "xss", "severity": "medium", "details": "Posible mención de XSS"})
            if "csrf" in page_text:
                security_patterns.append({"type": "csrf", "severity": "medium", "details": "Posible mención de CSRF"})
            if "authentication" in page_text:
                security_patterns.append({"type": "auth", "severity": "low", "details": "Mención de autenticación"})

            # Temas emergentes: título + meta + títulos de sección
            headings = await self._page.evaluate(
                "() => Array.from(document.querySelectorAll('h1, h2, h3')).map(h => h.innerText.trim())"
            )
            trending = [
                h
                for h in headings
                if len(h) > 10 and any(kw in h.lower() for kw in ["ai", "ml", "chat", "gpt", "llm", "emerging"])
            ]

            result = {
                "url": url,
                "title": title,
                "meta_tags": meta_tags,
                "technologies": tech_stack,
                "security_patterns": security_patterns,
                "trending_topics": trending,
                "fetched_at": now,
            }

            # Cachear
            self._page_cache[cache_key] = result
            self._scan_count += 1

            logger.debug(
                "[PLAYWRIGHT_PROVIDER] Análisis completado para %s: %d patrones, %d tecnologías",
                url,
                len(security_patterns),
                len(tech_stack),
            )
            return result

        except Exception as exc:
            logger.warning("[PLAYWRIGHT_PROVIDER] Falló al analizar %s: %s", url, exc)
            self._failure_count += 1
            return None

    def get_target_urls(self) -> list[str]:
        """Devuelve URLs objetivo para scraping."""
        return self._target_urls.copy()

    def set_target_urls(self, urls: list[str]) -> None:
        """Establece URLs objetivo."""
        self._target_urls = urls

    def get_stats(self) -> dict[str, Any]:
        """Devuelve estadísticas de uso."""
        return {
            "scan_count": self._scan_count,
            "failure_count": self._failure_count,
            "cache_size": len(self._page_cache),
            "target_urls_count": len(self._target_urls),
            "browser_initialized": self._browser is not None,
        }


# Singleton
async def get_playwright_provider() -> PlaywrightProvider:
    """Devuelve la instancia singleton de PlaywrightProvider."""
    global _PLAYWRIGHT_PROVIDER
    if _PLAYWRIGHT_PROVIDER is None:
        _PLAYWRIGHT_PROVIDER = PlaywrightProvider()
        await _PLAYWRIGHT_PROVIDER.initialize()
    return _PLAYWRIGHT_PROVIDER


async def reset_playwright_provider() -> None:
    """Reinicializa el singleton (útil para testing/limpieza)."""
    global _PLAYWRIGHT_PROVIDER
    if _PLAYWRIGHT_PROVIDER:
        await _PLAYWRIGHT_PROVIDER.cleanup()
        _PLAYWRIGHT_PROVIDER = None
