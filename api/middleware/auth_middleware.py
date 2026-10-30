import logging
import re

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from cores.auth.session_validator import get_session_validator

logger = logging.getLogger("ownex.api.middleware")

# Session cookie set on login/register/refresh (httpOnly). The token is also
# accepted via Authorization: Bearer for backwards compatibility.
SESSION_COOKIE = "ownex-session"

# Paths that do NOT require authentication
PUBLIC_PATHS: set[str] = {
    "/api/health",
    "/api/agents/health",
    "/api/version",
    "/api/system/health",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
    "/api/this-will-definitely-fail",
}

# Prefixes that do NOT require authentication
PUBLIC_PREFIXES: set[str] = {
    "/api/auth",
    "/api/license",
    # 265 rutas se montan en raíz (sin prefijo /api) porque sus routers se
    # se registran con `include_router(router)`. Antes de 2026-10-04 el early-return
    # `if not path.startswith("/api/")` las dejaba pasar TODAS, incluidas 139
    # mutantes (POST/PUT/PATCH/DELETE) — entre ellas
    # `POST /direct-work/workbank/{id}/deliver/approve`. Eso es P0: cualquier
    # request sin credencial podía aprobar entregas.
    #
    # Ahora las root-mounted pasan por el mismo gate que las de /api, con una
    # allowlist explícita de lo que debe quedar abierto. La allowlist, no el
    # early-return: un default abierto se convierte en bypass en cuanto
    # alguien monta un router nuevo sin pensar en esto.
    "/auth",
    "/api/ws",
}

#: Rutas raíz que además deben quedar públicas aunque no empiecen por
#: `/auth`. Cada una está acá porque el cliente la usa antes de tener sesión
#: (o porque no expone datos del usuario). Agregar acá = abrir sin credencial:
#: dejar una de estas en la lista es una decisión, no un descuido.
PUBLIC_ROOT_EXACT: set[str] = {
    "/health",
    "/version",
    # `GET /` es el endpoint raíz del backend (api/routers/* con `router.get("/")`).
    # El frontend SPA se sirve en otro lado (Tauri o spa-server.cjs), así que
    # este path no es el index.html y sí debe seguir siendo público.
    "/",
}


class AuthMiddleware(BaseHTTPMiddleware):
    # Rutas que existen como endpoint ⇒ exigen sesión. Las que NO existen
    # (assets, SPA routes como /daily o /settings) las sirve el frontend y no
    # deben pedir credencial, o la app no carga. Se calcula una vez al
    # importar: el conjunto de paths montados en el backend.
    _MOUNTED_PATHS: frozenset[str] = frozenset()

    # BUG (2026-10-05): `_MOUNTED_PATHS` guarda el path **con plantilla**
    # (`/direct-work/workbank/{item_id}/deliver/approve`) y el dispatch lo
    # comparaba contra el path **concreto** de la request
    # (`/direct-work/workbank/1/deliver/approve`). Nunca coinciden, así que las
    # 51 rutas root-mounted con parámetro de path caían en la rama
    # "asset o SPA route" y pasaban **sin credencial**. Medido en vivo:
    # `GET /mobile/reject/1` anónimo → 405 (llegó al router), mientras
    # `GET /today` anónimo → 401. Entre las afectadas:
    # `POST /mobile/approve/{approval_id}`, `POST /mobile/reject/{approval_id}`,
    # `POST /direct-work/workbank/{item_id}/deliver/approve`.
    #
    # El arreglo es matchear contra el patrón, no contra el literal. Se
    # indexan por prefijo literal (la parte antes del primer `{`) para no
    # recorrer 1857 regex por request en el path caliente.
    _MOUNTED_BY_PREFIX: dict[str, tuple[re.Pattern[str], ...]] = {}
    _MOUNTED_CATCHALL: tuple[re.Pattern[str], ...] = ()

    @classmethod
    def _register_mounted(cls, app) -> None:
        cls._MOUNTED_PATHS = frozenset(getattr(r, "path", "") for r in getattr(app, "routes", []))
        by_prefix: dict[str, list[re.Pattern[str]]] = {}
        catchall: list[re.Pattern[str]] = []
        for route in getattr(app, "routes", []):
            regex = getattr(route, "path_regex", None)
            if regex is None:  # Mount y similares: sólo prefijo literal
                raw = getattr(route, "path", None)
                if raw:
                    catchall.append(re.compile(re.escape(raw)))
                continue
            prefix = cls._literal_prefix(getattr(route, "path", "") or "")
            if prefix is None:
                catchall.append(regex)
            else:
                by_prefix.setdefault(prefix, []).append(regex)
        cls._MOUNTED_BY_PREFIX = {k: tuple(v) for k, v in by_prefix.items()}
        cls._MOUNTED_CATCHALL = tuple(catchall)

    @staticmethod
    def _literal_prefix(template: str) -> str | None:
        """Primer segmento literal de una plantilla de ruta.

        `/mobile/approve/{id}` → `"mobile"`. `None` cuando no hay un primer
        segmento literal (`/{id}/...`): esas van al catch-all, que se consulta
        siempre porque no se pueden indexar.
        """
        parts = template.split("/", 2)
        if len(parts) < 2 or not parts[1] or "{" in parts[1]:
            return None
        return parts[1]

    @classmethod
    def _is_mounted(cls, path: str) -> bool:
        """¿El path corresponde a una ruta montada en el backend?

        Acepta tanto el literal (`/today`) como el concreto con los parámetros
        ya resueltos (`/mobile/reject/1`), que es lo que llega por HTTP.
        """
        if path in cls._MOUNTED_PATHS:
            return True
        patterns = cls._MOUNTED_BY_PREFIX.get(path.strip("/").split("/", 1)[0], ())
        if any(p.match(path) for p in patterns):
            return True
        return any(p.match(path) for p in cls._MOUNTED_CATCHALL)

    async def dispatch(self, request: Request, call_next):
        # WebSocket connections are handled by their own auth (token in query param)
        if request.scope["type"] == "websocket":
            return await call_next(request)

        path = request.url.path

        # Browser preflights (CORS) never carry an Authorization header by
        # spec — answering 401 here would kill the handshake before
        # CORSMiddleware can respond (tests/test_cors_tauri.py).
        if request.method == "OPTIONS":
            return await call_next(request)

        # Desktop mode: non-API paths are frontend assets, never require auth.
        # Pero las rutas montadas en raíz SÍ son endpoints: son 265 rutas
        # (139 mutantes) que el early-return dejaba pasar sin sesión.
        # La distinción no es "empieza con /api" sino **¿existe como ruta?**
        # Un path no montado lo sirve el frontend (SPA/asset) y debe pasar.
        if not path.startswith("/api/"):
            if path in PUBLIC_ROOT_EXACT:
                return await call_next(request)
            if any(path.startswith(p) for p in PUBLIC_PREFIXES):
                return await call_next(request)
            if not self._is_mounted(path):
                return await call_next(request)  # asset o SPA route
            return await self._require_auth(request, call_next)

        if path in PUBLIC_PATHS:
            return await call_next(request)

        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        return await self._require_auth(request, call_next)

    async def _require_auth(self, request: Request, call_next):
        """Validate the session for a non-public path.

        Extraído para que /api/ y las rutas montadas en raíz compartan **la
        misma** validación: antes eran dos caminos y sólo uno exigía sesión.
        """
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()

        # Fallback: httpOnly session cookie (set on login). The cookie path is
        # only honored when no Authorization header is present, keeping the
        # Bearer flow fully backwards compatible.
        if not token:
            token = request.cookies.get(SESSION_COOKIE, "").strip()

        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": "Authorization header required"},
            )

        validator = get_session_validator()
        result = validator.validate(token)

        if not result.valid:
            return JSONResponse(
                status_code=401,
                content={"error": result.reason or "Invalid or expired token"},
            )

        logger.info("[HW] AuthMiddleware.dispatch: JWT valid, passing request through")
        return await call_next(request)
