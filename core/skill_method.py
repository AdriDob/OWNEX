"""Skill Method — ruta de estudio guiada del hambre técnico, con evidencia.

Sube el score de skill con sesiones de evidencia reales (write-up, CTF, recon).
No se "aprueba" solo: cada sesión registrada marca skills pendientes del track.
Persistencia: ~/.config/ownex/skill_method/state.json
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.skill_method")

TRACKS = [
    {
        "id": "web",
        "icon": "🕸️",
        "name": "Web / API",
        "goal": "OWASP Top 10 real: auth, IDOR, SSRF, XSS, RCE, JWT, GraphQL.",
        "levels": [
            {
                "id": "web-1",
                "name": "Base de recon",
                "skills": ["HTTP y metodología", "OWASP Top 10", "Burp intercepts", "Análisis de requests"],
            },
            {
                "id": "web-2",
                "name": "Auth y acceso",
                "skills": ["IDOR / BOLA", "Privilege escalation", "JWT attacks", "Bypass de auth"],
            },
            {"id": "web-3", "name": "Inyecciones", "skills": ["SSRF → interno", "XSS contextual", "SQLi real", "SSTI"]},
            {
                "id": "web-4",
                "name": "RCE y weird APIs",
                "skills": ["RCE en uploads", "Deserialización", "GraphQL abuse", "Chain de vulns"],
            },
        ],
    },
    {
        "id": "mobile",
        "icon": "📱",
        "name": "Mobile",
        "goal": "Análisis android/iOS: storage, deep links, intercept, bypass TLS.",
        "levels": [
            {"id": "mob-1", "name": "Estática", "skills": ["apk/ipa decode", "manifest", "Secretos en código"]},
            {
                "id": "mob-2",
                "name": "Dinámica",
                "skills": ["Intercept tráfico", "Frida hooking", "SSL pinning bypass", "Deep links"],
            },
        ],
    },
    {
        "id": "cloud",
        "icon": "☁️",
        "name": "Cloud / Infra",
        "levels": [
            {
                "id": "cloud-1",
                "name": "Misconfigs",
                "skills": ["S3 público", "Bucket policy", "IAM enumeración", "SSRF → metadata"],
            },
            {
                "id": "cloud-2",
                "name": "Escalación",
                "skills": ["Privesc IAM", "AssumeRole", "Serverless", "Terraform review"],
            },
        ],
    },
    {
        "id": "web3",
        "icon": "🔗",
        "name": "Web3 / DeFi",
        "levels": [
            {
                "id": "w3-1",
                "name": "Base EVM",
                "skills": ["Solidity reads", "Reentrancy", "call/transfer", "Storage layout"],
            },
            {
                "id": "w3-2",
                "name": "Exploits DeFi",
                "skills": ["Flash loans", "Oracle attacks", "CEI patterns", "Audit walkthrough"],
            },
        ],
    },
]

SESSION_TYPES = {
    "writeup": "Publicaste un write-up real (GitHub/blog).",
    "ctf": "Resolviste un challenge/máquina y lo documentaste.",
    "recon": "Hiciste un recon estructurado de un target.",
    "labs": "Completaste un lab guiado (PortSwigger/TryHackMe).",
}

_DEFAULT_STATE = {
    "started_on": None,
    "current_track": "web",
    "sessions": [],
    "completed": [],
    "stats": {},
}


class SkillMethod:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/skill_method/")
        os.makedirs(self.data_dir, exist_ok=True)

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

    def _total_skills(self) -> int:
        return sum(len(level["skills"]) for t in TRACKS for level in t["levels"])

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        completed = state.get("completed", [])
        total = self._total_skills()
        score = min(100, round(len(completed) / max(1, total) * 100))
        tracks = []
        for t in TRACKS:
            tr = {**t}
            levels = []
            for lvl in t["levels"]:
                level_data = dict(lvl)
                done = [s for s in lvl["skills"] if f"{t['id']}:{lvl['id']}:{s}" in completed]
                level_data["progress"] = len(done)
                level_data["total"] = len(lvl["skills"])
                levels.append(level_data)
            tr["levels"] = levels
            tr["done"] = sum(level["progress"] for level in levels)
            tr["total"] = sum(level["total"] for level in levels)
            tracks.append(tr)
        return {
            "success": True,
            "started_on": state.get("started_on"),
            "current_track": state.get("current_track", "web"),
            "tracks": tracks,
            "sessions": state.get("sessions", [])[-10:],
            "completed": completed,
            "score": score,
            "done_skills": len(completed),
            "total_skills": total,
            "stats": state.get("stats", {}),
            "message": self._message(score),
            "session_types": SESSION_TYPES,
        }

    def _message(self, score: int) -> str:
        if score == 0:
            return "Arrancá con el track Web — registrá tu primera sesión de evidencia."
        if score < 35:
            return "Buena base. Seguí acumulando sesiones, no skills marcadas a mano."
        if score < 70:
            return "Nivel operativo. Ya podés colaborar en programas reales sin miedo."
        return "Ritmo 0,1%. Competencia de elite en los skills que tocás."

    def set_track(self, track_id: str) -> dict[str, Any]:
        if not any(t["id"] == track_id for t in TRACKS):
            return {"success": False, "message": "Track inválido."}
        state = self._load()
        state["current_track"] = track_id
        self._save(state)
        return {"success": True, "current_track": track_id}

    def register_session(self, track_id: str, session_type: str, title: str, notes: str = "") -> dict[str, Any]:
        state = self._load()
        track = next((t for t in TRACKS if t["id"] == track_id), None)
        if not track:
            return {"success": False, "message": "Track inválido."}
        if session_type not in SESSION_TYPES:
            return {"success": False, "message": "Tipo de sesión inválido."}
        if not title.strip():
            return {"success": False, "message": "Poné un título a la sesión."}

        state["started_on"] = state.get("started_on") or datetime.now(UTC).isoformat()
        now = datetime.now(UTC)
        entry = {
            "id": f"ses-{int(now.timestamp() * 1000)}",
            "track": track_id,
            "track_name": track["name"],
            "type": session_type,
            "title": title.strip(),
            "notes": notes.strip(),
            "created_at": now.isoformat(),
        }
        state["sessions"].append(entry)
        stats = state.get("stats", {})
        stats["total_sessions"] = stats.get("total_sessions", 0) + 1
        stats[session_type] = stats.get(session_type, 0) + 1
        state["stats"] = stats

        completed = list(state.get("completed", []))
        for lvl in track["levels"]:
            for skill in lvl["skills"]:
                key = f"{track_id}:{lvl['id']}:{skill}"
                if key not in completed:
                    completed.append(key)
                    break
            else:
                continue
            break
        state["completed"] = completed
        self._save(state)
        return {"success": True, "entry": entry, "completed": len(completed)}


_sm: SkillMethod | None = None


def get_skill_method() -> SkillMethod:
    global _sm
    if _sm is None:
        _sm = SkillMethod()
    return _sm
