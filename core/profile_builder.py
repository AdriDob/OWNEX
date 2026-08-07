"""GitHub Profile Builder — vincula GitHub a OWNEX y construye/mejora el perfil.

Responsabilidades:
1. Vincular la cuenta de GitHub del operador (username + token del vault).
2. Auditar el perfil (README, avatar, bio, pinned, repos, contribuciones)
   y calcular un score accionable.
3. Generar el README.md de perfil listo para copiar/subir.
4. Registrar contribuciones reales (bounts validados, PRs cerrados).
5. Auto-push: si está activado y hay repo portfolio configurado, la solución
   de cada bounty validado se sube automáticamente a ese repo.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.profile_builder")

SCORE_WEIGHTS = {
    "readme": 25,
    "avatar_bio": 15,
    "pinned_repos": 20,
    "public_repos": 10,
    "contributions": 15,
    "historial": 15,
}

_DEFAULT_STATE = {
    "username": "",
    "linked": False,
    "contributions": [],
    "portfolio_repo": "",
    "auto_push": False,
}


class ProfileBuilder:
    """Construcción y mejora continua del perfil de GitHub."""

    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/profile_builder/")
        os.makedirs(self.data_dir, exist_ok=True)

    # ── Estado persistente ──

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                state = json.load(f)
                for k, v in _DEFAULT_STATE.items():
                    state.setdefault(k, v)
                return state
        except Exception:
            return dict(_DEFAULT_STATE)

    def _save(self, state: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def _github_token(self) -> str:
        try:
            from core.credentials.vault import get_credentials

            return get_credentials().github_token or os.environ.get("GITHUB_TOKEN", "")
        except Exception:
            return os.environ.get("GITHUB_TOKEN", "")

    def _api_request(self, url: str, method: str = "GET", data: str | None = None) -> dict[str, Any]:
        token = self._github_token()
        req = urllib.request.Request(url, method=method)
        req.add_header("Accept", "application/vnd.github.v3+json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, data=data.encode("utf-8") if data else None, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}

    # ── Vínculo con GitHub ──

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        return {
            "success": True,
            "linked": state.get("linked", False),
            "username": state.get("username", ""),
            "has_token": bool(self._github_token()),
            "portfolio_repo": state.get("portfolio_repo", ""),
            "auto_push": state.get("auto_push", False),
            "score": state.get("score", 0),
            "score_detail": state.get("score_detail", {}),
            "audit": state.get("audit", {}),
            "recommendations": self.recommendations(),
            "contributions": state.get("contributions", [])[-10:],
        }

    def link_github(self, username: str) -> dict[str, Any]:
        username = username.strip().lstrip("@").strip()
        if not username:
            return {"success": False, "message": "Ingresá tu usuario de GitHub."}
        if not re.match(r"^[a-zA-Z0-9-]{1,39}$", username):
            return {"success": False, "message": "Usuario de GitHub inválido."}

        state = self._load()
        state["username"] = username
        state["linked"] = True
        self._save(state)
        logger.info("[PROFILE_BUILDER] GitHub vinculado: %s", username)

        try:
            audit = self.audit()
            return {"success": True, "username": username, **audit}
        except Exception as e:
            return {"success": True, "username": username, "message": f"Vinculado. Auditoría pendiente: {e}"}

    # ── Configuración de auto-push a repo portfolio ──

    def set_portfolio_repo(self, repo: str) -> dict[str, Any]:
        """Configura el repo destino (formato 'usuario/repo') para auto-push de bounties."""
        repo = repo.strip().rstrip("/")
        if not repo or "/" not in repo:
            return {"success": False, "message": "Formato: usuario/repo (ej. adrie/bounty-portfolio)"}
        state = self._load()
        state["portfolio_repo"] = repo
        self._save(state)
        return {"success": True, "portfolio_repo": repo}

    def set_auto_push(self, enabled: bool) -> dict[str, Any]:
        """Activa/desactiva auto-push de bounties validados al repo portfolio."""
        state = self._load()
        state["auto_push"] = bool(enabled)
        self._save(state)
        return {"success": True, "auto_push": state["auto_push"]}

    # ── Auto-push de soluciones al repo portfolio ──

    def _push_to_portfolio(self, title: str, solution: dict[str, Any], bounty_url: str = "") -> dict[str, Any]:
        """Pushea la solución del bounty al repo portfolio configurado."""
        token = self._github_token()
        if not token:
            return {"success": False, "message": "Sin GITHUB_TOKEN configurado."}
        state = self._load()
        portfolio = state.get("portfolio_repo", "")
        if not portfolio:
            return {"success": False, "message": "Repo portfolio no configurado."}

        # Sanitizar título para path
        safe_title = re.sub(r"[^a-zA-Z0-9-_]", "-", title.lower())[:50]
        date_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
        folder = f"bounties/{date_prefix}-{safe_title}"

        # Preparar archivos: solution files + README del bounty
        files: dict[str, str] = {}
        sol = solution.get("solution", {}) if isinstance(solution, dict) else {}
        if sol.get("files"):
            for f in sol["files"]:
                path = f.get("path", "")
                content = f.get("content", "")
                if path and content:
                    files[f"{folder}/{path}"] = content
        readme_content = [
            f"# {title}",
            "",
            f"**Bounty resuelto:** {bounty_url or 'N/A'}",
            f"**Fecha:** {datetime.now(UTC).strftime('%Y-%m-%d')}",
            f"**Tipo:** {solution.get('platform', 'dev_bounty')}",
            "",
            "## Solución",
            sol.get("summary", "Ver archivos de la solución."),
            "",
            "---",
            "*Generado automáticamente por OWNEX Profile Builder*",
        ]
        files[f"{folder}/README.md"] = "\n".join(readme_content)

        if not files:
            return {"success": False, "message": "Sin archivos para pushear."}

        # Crear commit via GitHub API (create blobs + tree + commit + update ref)
        try:
            repo_info = self._api_request(f"https://api.github.com/repos/{portfolio}")
            default_branch = repo_info.get("default_branch", "main")
            ref_data = self._api_request(f"https://api.github.com/repos/{portfolio}/git/refs/heads/{default_branch}")
            latest_commit_sha = ref_data["object"]["sha"]

            commit_data = self._api_request(f"https://api.github.com/repos/{portfolio}/git/commits/{latest_commit_sha}")
            base_tree_sha = commit_data["tree"]["sha"]

            blobs = []
            for path, content in files.items():
                blob_resp = self._api_request(
                    f"https://api.github.com/repos/{portfolio}/git/blobs",
                    method="POST",
                    data=json.dumps({"content": content, "encoding": "utf-8"}),
                )
                blobs.append({"path": path, "mode": "100644", "type": "blob", "sha": blob_resp["sha"]})

            tree_resp = self._api_request(
                f"https://api.github.com/repos/{portfolio}/git/trees",
                method="POST",
                data=json.dumps({"base_tree": base_tree_sha, "tree": blobs}),
            )
            new_tree_sha = tree_resp["sha"]

            commit_resp = self._api_request(
                f"https://api.github.com/repos/{portfolio}/git/commits",
                method="POST",
                data=json.dumps(
                    {
                        "message": f"feat: add bounty solution - {title}",
                        "tree": new_tree_sha,
                        "parents": [latest_commit_sha],
                    }
                ),
            )
            new_commit_sha = commit_resp["sha"]

            self._api_request(
                f"https://api.github.com/repos/{portfolio}/git/refs/heads/{default_branch}",
                method="PATCH",
                data=json.dumps({"sha": new_commit_sha, "force": False}),
            )

            return {
                "success": True,
                "folder": folder,
                "commit": new_commit_sha[:7],
                "files": len(files),
            }
        except Exception as e:
            logger.error("[PROFILE_BUILDER] auto-push failed: %s", e)
            return {"success": False, "message": f"Error en push: {e}"}

    # ── Auditoría del perfil ──

    def audit(self) -> dict[str, Any]:
        state = self._load()
        username = state.get("username", "")
        if not username:
            return {"success": False, "score": 0, "score_detail": {}, "audit": {}, "message": "Sin usuario vinculado."}

        audit: dict[str, Any] = {}
        try:
            user = self._api_request(f"https://api.github.com/users/{username}")
            audit["user"] = {
                "name": user.get("name", ""),
                "bio": user.get("bio", ""),
                "avatar": bool(user.get("avatar_url")),
                "public_repos": user.get("public_repos", 0),
                "followers": user.get("followers", 0),
                "created_at": user.get("created_at", ""),
                "company": user.get("company", ""),
                "blog": user.get("blog", ""),
            }
        except Exception as e:
            audit["user_error"] = str(e)

        try:
            readme = self._api_request(f"https://api.github.com/repos/{username}/{username}/readme")
            audit["has_readme"] = bool(readme.get("content"))
        except Exception:
            audit["has_readme"] = False

        try:
            repos = self._api_request(f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated")
            pinned = [r for r in repos if r.get("pinned")] or []
            audit["repo_count"] = len(repos)
            audit["pinned_count"] = len(pinned)
            audit["has_pinned"] = bool(pinned)
            audit["top_repos"] = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:3]
        except Exception as e:
            audit["repos_error"] = str(e)

        score, detail = self._score(audit)
        state["audit"] = audit
        state["score"] = score
        state["score_detail"] = detail
        state["last_audit"] = datetime.now(UTC).isoformat()
        self._save(state)
        return {"success": True, "username": username, "score": score, "score_detail": detail, "audit": audit}

    def _score(self, audit: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        detail: dict[str, Any] = {}

        has_readme = audit.get("has_readme", False)
        detail["readme"] = {"points": SCORE_WEIGHTS["readme"] if has_readme else 0, "has_readme": has_readme}

        u = audit.get("user", {})
        avatar_bio = (1 if u.get("avatar") else 0) + (1 if u.get("bio") else 0) + (1 if u.get("name") else 0)
        detail["avatar_bio"] = {"points": round(SCORE_WEIGHTS["avatar_bio"] * avatar_bio / 3), "complete": avatar_bio}

        pinned = audit.get("pinned_count", 0)
        detail["pinned_repos"] = {
            "points": SCORE_WEIGHTS["pinned_repos"]
            if pinned >= 3
            else (SCORE_WEIGHTS["pinned_repos"] // 2 if pinned else 0),
            "pinned": pinned,
        }

        repo_count = audit.get("repo_count", 0)
        detail["public_repos"] = {
            "points": min(SCORE_WEIGHTS["public_repos"], repo_count * 2),
            "repos": repo_count,
        }

        contributions = len(self._load().get("contributions", []))
        detail["contributions"] = {
            "points": min(SCORE_WEIGHTS["contributions"], contributions * 3),
            "contributions": contributions,
        }

        try:
            created = datetime.fromisoformat((audit.get("user") or {}).get("created_at", "")[:10])
            months = max(0, (datetime.now(UTC) - created.replace(tzinfo=UTC)).days / 30)
        except Exception:
            months = 0
        historial = 0
        if months > 0 and repo_count > 0:
            historial = min(SCORE_WEIGHTS["historial"], int(months) + repo_count // 2)
        detail["historial"] = {"points": historial, "months": round(months)}

        total = min(100, sum(d["points"] for d in detail.values()))
        return total, detail

    # ── Recomendaciones ──

    def recommendations(self) -> list[dict[str, Any]]:
        state = self._load()
        audit = state.get("audit", {})
        recs: list[dict[str, Any]] = []
        if not state.get("linked"):
            recs.append(
                {
                    "priority": "alta",
                    "action": "Vincular tu usuario de GitHub en esta sección.",
                    "why": "Sin vínculo no hay auditoría ni plan.",
                }
            )
            return recs

        if not audit.get("has_readme"):
            recs.append(
                {
                    "priority": "alta",
                    "action": "Crear el README.md del perfil (generalo acá y copialo).",
                    "why": "Es el 25% del score y lo primero que mira un mantenedor.",
                }
            )
        if (audit.get("user") or {}).get("bio") == "":
            recs.append(
                {
                    "priority": "media",
                    "action": "Escribir una bio con tu stack (Python/Go/TypeScript) y lo que hacés.",
                    "why": "Suma credibilidad instantánea.",
                }
            )
        if (audit.get("pinned_count") or 0) < 3:
            recs.append(
                {
                    "priority": "media",
                    "action": "Fijar 3 repos representativos (pinned).",
                    "why": "Los pinned son la vitrina de tu perfil.",
                }
            )
        if not self._github_token():
            recs.append(
                {
                    "priority": "alta",
                    "action": "Configurar GITHUB_TOKEN (vault / .env).",
                    "why": "Permite auditoría más completa y push del README.",
                }
            )
        if (audit.get("repo_count") or 0) == 0:
            recs.append(
                {
                    "priority": "alta",
                    "action": "Subir tu primer repo (aunque sea un proyecto chico propio).",
                    "why": "Perfil con 0 repos se ve inactivo.",
                }
            )
        if not state.get("portfolio_repo"):
            recs.append(
                {
                    "priority": "media",
                    "action": "Configurar repo portfolio (usuario/repo) y activar auto-push.",
                    "why": "Cada bounty validado se sube solo a tu GitHub.",
                }
            )
        pending = self._count_dev_bounty_pending()
        if pending:
            recs.append(
                {
                    "priority": "alta",
                    "action": f"Validar los {pending} bounty(s) pendientes → serán tu historial real.",
                    "why": "Cada bounty cerrado = contribución + credibilidad.",
                }
            )
        recs.append(
            {
                "priority": "baja",
                "action": "Mantener ritmo constante: 2-3 commits/PRs por semana.",
                "why": "El historial se construye con consistencia, no en un día.",
            }
        )
        return recs

    def _count_dev_bounty_pending(self) -> int:
        try:
            from core.dev_bounty_autopilot import get_dev_bounty_autopilot

            return get_dev_bounty_autopilot()._count_pending_proposals()
        except Exception:
            return 0

    # ── README del perfil ──

    def generate_readme(self) -> dict[str, Any]:
        state = self._load()
        username = state.get("username", "")
        if not username:
            return {"success": False, "message": "Vinculá tu GitHub primero."}
        audit = state.get("audit", {})
        u = audit.get("user", {})
        name = u.get("name") or username

        stats = (
            f"[![GitHub followers](https://img.shields.io/github/followers/{username}?style=flat-square)]"
            f"(https://github.com/{username})"
        )
        lines = [
            f"# Hola, soy {name} 👋",
            "",
            "Soy desarrollador trabajando con Python, Go y TypeScript. Me gusta resolver "
            "problemas reales, colaborar en open source y construir proyectos de punta a punta.",
            "",
            "### 🔭 En lo que estoy trabajando",
            "- Aportes a proyectos open source (bugs, mejoras, features)",
            "- Herramientas de automatización e inteligencia",
            "",
            "### 🛠️ Stack",
            "- **Lenguajes:** Python · Go · TypeScript",
            "- **Herramientas:** Git · Docker · APIs REST",
            "",
            "### 📈 Actividad",
            stats,
            "",
            "### 📫 Contacto",
            f"- GitHub: [@{username}](https://github.com/{username})",
            "",
        ]
        if (audit.get("repo_count") or 0) > 0:
            top = audit.get("top_repos", [])
            if top:
                lines.insert(-3, "### ⭐ Proyectos destacados")
                for r in top[:3]:
                    desc = (r.get("description") or "").strip()
                    lines.insert(-3, f"- [{r['name']}]({r.get('html_url', '')}) — {desc if desc else 'ver repo'}")
                lines.insert(-3, "")

        readme = "\n".join(lines)
        state["last_readme"] = readme
        self._save(state)
        return {"success": True, "username": username, "readme": readme}

    # ── Registro de contribuciones (con auto-push opcional) ──

    def record_contribution(
        self, kind: str, title: str, url: str = "", solution: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        state = self._load()
        push_result: dict[str, Any] | None = None

        # Auto-push si está activo y hay solución disponible
        if kind == "dev_bounty" and state.get("auto_push") and solution:
            push_result = self._push_to_portfolio(title, solution, url)

        contributions = state.get("contributions", [])
        entry = {
            "kind": kind,
            "title": title,
            "url": url,
            "created_at": datetime.now(UTC).isoformat(),
            "push": push_result,
        }
        contributions.append(entry)
        state["contributions"] = contributions
        self._save(state)
        return {"success": True, "contributions": len(contributions), "entry": entry, "push": push_result}


_builder: ProfileBuilder | None = None


def get_profile_builder() -> ProfileBuilder:
    global _builder
    if _builder is None:
        _builder = ProfileBuilder()
    return _builder
