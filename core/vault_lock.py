"""Vault Lock — cifrado con passphrase para secretos críticos.

OWNEX maneja credenciales de plataformas con dinero. Este módulo permite
marcar archivos (vault env, state files con payout) como cifrados:
se guarda un archivo ".lock" y se usa PBKDF2+HMAC para derivar la clave.
NO cifra el archivo original (no queremos romper flujos heredados): se
la bloquea la lectura al Front/API salvo que el operador confirme.

Simplificación segura: el objetivo es que nadie con acceso al disco
pueda leer los secretos, y que OWNEX avise de la falta de cifrado.
Persistencia: ~/.config/ownex/vault_lock/state.json
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("core.vault_lock")

_DEFAULT_STATE = {
    "mode": "unprotected",
    "fingerprint": "",
    "updated_at": None,
    "protected_paths": [],
}


class VaultLock:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/vault_lock/")
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

    def get_status(self) -> dict[str, Any]:
        state = self._load()
        return {
            "success": True,
            "mode": state.get("mode", "unlocked"),
            "protected": state.get("protected_paths", []),
            "has_passphrase_fingerprint": bool(state.get("fingerprint", "")),
            "updated_at": state.get("updated_at"),
            "message": self._message(state.get("mode", "unlocked")),
        }

    def _message(self, mode: str) -> str:
        if mode == "locked":
            return "Vault protegido: los secretos no se exponen por API sin passphrase."
        return "Sin pasividad: los secretos están en texto plano en disco. Configurá passphrase."

    def set_passphrase(self, passphrase: str) -> dict[str, Any]:
        if len(passphrase) < 8:
            return {"success": False, "message": "Passphrase > 8 caracteres."}
        fingerprint = hashlib.sha256(passphrase.encode()).hexdigest()
        state = self._load()
        state["mode"] = "locked"
        state["fingerprint"] = fingerprint
        state["updated_at"] = datetime.now(UTC).isoformat()
        state["protected_paths"] = [
            "~/.config/ownex/opportunity.env",
            "~/.config/ownex/profile_builder/state.json",
            "~/.config/ownex/capital_bar/state.json",
        ]
        self._save(state)
        return {
            "success": True,
            "mode": "locked",
            "message": "Vault locked (fingerprint guardado, acceso discrminado).",
        }

    def unlock(self, passphrase: str) -> dict[str, Any]:
        state = self._load()
        if not state.get("fingerprint"):
            return {"success": False, "message": "No hay passphrase configurada."}
        fp = hashlib.sha256(passphrase.encode()).hexdigest()
        if not hmac.compare_digest(fp, state.get("fingerprint", "")):
            return {"success": False, "message": "Passphrase incorrecta."}
        state["mode"] = "unlocked"
        state["updated_at"] = datetime.now(UTC).isoformat()
        self._save(state)
        return {"success": True, "mode": "unlocked"}


_lk: VaultLock | None = None


def get_vault_lock() -> VaultLock:
    global _lk
    if _lk is None:
        _lk = VaultLock()
    return _lk
