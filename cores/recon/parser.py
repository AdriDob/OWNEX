import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from cores.engine.unified_scoring import score as unified_score
from cores.recon.hostname import has_real_host

logger = logging.getLogger("ownex.recon.parser")

AUTH_SMELLS = [
    "org_id",
    "tenant_id",
    "workspace_id",
    "account_id",
    "user_id",
    "team_id",
]

SIGNAL_KEYWORDS = [
    "/api/",
    "/graphql",
    "/admin/",
    "/export",
    "/internal",
    "/billing",
    "/settings",
    "/members",
    "/users",
    "/organizations",
    "/teams",
    "/workspaces",
    "/attachments",
    "/uploads",
    "/files",
    "/reports",
    "/audit",
    "/invites",
    "/tokens",
    "/keys",
]

STATIC_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".css",
    ".js",
    ".map",
    ".ico",
    ".mp4",
    ".webm",
}

HIGH_VALUE_KEYWORDS = {
    "billing",
    "admin",
    "internal",
    "graphql",
    "export",
    "attachments",
    "uploads",
    "reports",
    "audit",
    "token",
    "apikey",
    "keys",
    "invite",
    "organization",
    "workspace",
    "tenant",
}

UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

NUMERIC_PATTERN = re.compile(r"/(?:[0-9]+)(?:/|$)")

#: Un path HTTP serializado no lleva una comilla doble sin escapar: siempre
#: va percent-encoded (`%22`). Si aparece una, lo que se guardó no es un path.
_QUOTE_CHARS = ('"', "\n", "\r", "\t")

#: Longitud máxima razonable para un endpoint. Lo más largo que se ha visto
#: sano ronda los 300 chars; 2048 es holgado y corta los blobs.
MAX_PATH_LENGTH = 2048

_PATHY = re.compile(r"^(?:/|[a-zA-Z][a-zA-Z0-9+.\-]*://|//)")


def looks_like_path(value: object) -> bool:
    """¿Es esto un path/URL, o es la serialización de otra cosa?

    Existe por un bug medido: `scan_service` hacía
    `path = entry.get("normalized") or entry.get("path") or entry.get("raw")`
    y `raw` es el payload sin parsear del crawler. Cuando faltaban los dos
    primeros, se guardaba ese blob en la columna `path` y quedaba

        //host/x.html","tag":"a","attribute":"href",…,"error":"max depth reached"}

    8.937 de 44.597 endpoints (20% de la tabla). No era cosmético: ese string
    entra a `unified_score()` y a la detección de superficie por substring, así
    que un endpoint de documentación marcaba "tiene exports" por la URL de
    origen pegada. Ver KNOWN_DEBT #81.

    **La defensa va en el writer, no en reparar después**: normalizar la tabla
    es una operación de 8.937 filas; rechazar el blob, una línea.

    Lo que se acepta, además de `/x`:
      · `//docs.hackerone.com/en/articles/…` — URL protocol-relative: es
        discovery real, no basura.
      · `https://host/x` con esquema.
    Lo que se rechaza: comillas sin escapar, caracteres de control, texto con
    pares `"clave":valor` (es decir, serialización), y cualquier cosa que no
    empiece por `/`, `//` o esquema.
    """
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if not candidate or len(candidate) > MAX_PATH_LENGTH:
        return False
    if any(ch in candidate for ch in _QUOTE_CHARS):
        return False
    # Serialización: `"algo":algo` con separadores. Una URL con query
    # (`?a=1&b=2`) no tiene `"` ni coma-con-comillas, así que no hay
    # colisión con paths legítimos.
    if '":' in candidate and "," in candidate:
        return False
    return bool(_PATHY.match(candidate))


@dataclass
class EndpointMetadata:
    raw: str
    scheme: str
    host: str
    path: str
    normalized: str
    labels: list[str]
    auth_smells: list[str]
    uuid: bool
    numeric_id: bool
    score: int

    def to_dict(self) -> dict:
        return {
            "raw": self.raw,
            "scheme": self.scheme,
            "host": self.host,
            "path": self.path,
            "normalized": self.normalized,
            "labels": self.labels,
            "auth_smells": self.auth_smells,
            "uuid": self.uuid,
            "numeric_id": self.numeric_id,
            "score": self.score,
        }


class EndpointParser:
    def normalize_path(self, path: str) -> str:
        path = path.strip()

        if not path:
            return "/"

        path = path.split("?", 1)[0]
        path = re.sub(r"/+", "/", path)

        parts = [segment for segment in path.split("/") if segment]
        normalized = []

        for segment in parts:
            lower = segment.lower()

            if UUID_PATTERN.search(segment):
                normalized.append("{uuid}")

            elif segment.isdigit():
                normalized.append("{id}")

            elif re.match(r"^[0-9a-fA-F]{24}$", segment):
                normalized.append("{hex_id}")

            elif re.match(r"^[A-Za-z0-9_-]{32,}$", segment):
                normalized.append("{token}")

            else:
                normalized.append(lower)

        if not normalized:
            return "/"

        return "/" + "/".join(normalized)

    def extract_path(self, raw: str) -> str:
        raw = raw.strip()

        if not raw:
            return "/"

        try:
            if raw.startswith("http"):
                parsed = urlparse(raw)
                return parsed.path or "/"

            if raw.startswith("/"):
                return raw

            if "?" in raw:
                return raw.split("?", 1)[0]

            parsed = urlparse(f"http://{raw}") if not raw.startswith(("http", "/")) else urlparse(raw)

            return parsed.path or "/"

        except Exception:
            return "/"

    def detect_labels(self, path: str) -> list[str]:
        labels = []
        lower = path.lower()

        for keyword in SIGNAL_KEYWORDS:
            if keyword in lower:
                labels.append(keyword.strip("/"))

        if "/graphql" in lower:
            labels.append("graphql")

        if "/admin" in lower:
            labels.append("admin")

        if "export" in lower:
            labels.append("export")

        if "internal" in lower:
            labels.append("internal")

        if any(x in lower for x in ["/org", "/organization", "/tenant", "/workspace"]):
            labels.append("multi_tenant")

        if any(x in lower for x in ["/billing", "/invoice", "/subscription"]):
            labels.append("billing")

        if any(x in lower for x in ["/upload", "/attachment", "/file"]):
            labels.append("files")

        if any(x in lower for x in ["/auth", "/login", "/session", "/token"]):
            labels.append("auth")

        if any(x in lower for x in ["/invite", "/member", "/user"]):
            labels.append("identity")

        return sorted(set(labels))

    def detect_auth_smells(self, path: str) -> list[str]:
        smells = []

        for token in AUTH_SMELLS:
            if token in path.lower():
                smells.append(token)

        return smells

    def extract_url(self, raw: str) -> str:
        raw = raw.strip()

        if raw.startswith("{") and raw.endswith("}"):
            try:
                payload = json.loads(raw)

                for key in ["url", "uri", "link", "request", "host"]:
                    if key in payload and isinstance(payload[key], str):
                        return payload[key]

                if "url" in payload and isinstance(payload["url"], dict):
                    return payload["url"].get("raw", raw)

            except json.JSONDecodeError:
                logger.warning("Failed to decode JSON from payload", exc_info=True)

        return raw

    def parse_endpoint(self, raw: str) -> EndpointMetadata:
        raw = raw.strip()

        url = self.extract_url(raw)
        path = self.extract_path(url)
        normalized = self.normalize_path(path)

        labels = self.detect_labels(path)
        smells = self.detect_auth_smells(path)

        score = int(unified_score(path, "GET", {})["risk_score"])

        parsed = urlparse(url) if url.startswith("http") else urlparse("http://example.com" + path)

        return EndpointMetadata(
            raw=url,
            scheme=parsed.scheme,
            host=parsed.netloc,
            path=path,
            normalized=normalized,
            labels=labels,
            auth_smells=smells,
            uuid=bool(UUID_PATTERN.search(path)),
            numeric_id=bool(NUMERIC_PATTERN.search(path)),
            score=score,
        )

    def parse_lines(self, lines: Iterable[str]) -> list[EndpointMetadata]:
        endpoints = []
        seen = set()

        for raw in lines:
            if not raw:
                continue

            try:
                metadata = self.parse_endpoint(raw)

                # Sin host real no hay evidencia: banners ASCII y líneas de
                # error JSON caen acá con host placeholder (example.com).
                # Persistirlos crea endpoints falsos que contaminan el scoring.
                if not has_real_host(metadata.host):
                    continue

                dedupe_key = (
                    metadata.normalized,
                    tuple(sorted(metadata.labels)),
                )

                if dedupe_key in seen:
                    continue

                seen.add(dedupe_key)
                endpoints.append(metadata)

            except Exception:
                continue

        endpoints.sort(key=lambda x: x.score, reverse=True)

        return endpoints

    def save_metadata(self, endpoints: list[EndpointMetadata], out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)

        array = [endpoint.to_dict() for endpoint in endpoints]

        out_path.write_text(json.dumps(array, indent=2, ensure_ascii=False))

        return out_path

    def parse_files(self, source_paths: list[Path], out_path: Path) -> Path:
        lines = []

        for path in source_paths:
            if not path.exists():
                continue

            with path.open("r", encoding="utf-8", errors="ignore") as stream:
                for raw in stream:
                    raw = raw.strip()

                    if raw:
                        lines.append(raw)

        endpoints = self.parse_lines(lines)

        return self.save_metadata(endpoints, out_path)
