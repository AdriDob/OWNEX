"""Sync Service — Handles synchronization between devices."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from cores.sync.models import (
    PendingMutation,
)

logger = logging.getLogger("ownex.sync")


class SyncService:
    """Service for handling device synchronization with conflict resolution."""

    def __init__(self, storage_path: str | None = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            data_dir = os.environ.get("OWNEX_DATA_DIR")
            base = Path(data_dir) if data_dir else Path(__file__).resolve().parents[3] / "data"
            self.storage_path = base / "sync"

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._pending_mutations: dict[str, dict] = {}
        self._conflicts: dict[str, dict] = {}
        self._load()

    def _get_mutations_path(self) -> Path:
        return self.storage_path / "pending_mutations.json"

    def _get_conflicts_path(self) -> Path:
        return self.storage_path / "conflicts.json"

    def _load(self) -> None:
        """Load pending mutations and conflicts from storage."""
        try:
            mutations_file = self._get_mutations_path()
            if mutations_file.exists():
                with open(mutations_file) as f:
                    self._pending_mutations = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load pending mutations: {e}")

        try:
            conflicts_file = self._get_conflicts_path()
            if conflicts_file.exists():
                with open(conflicts_file) as f:
                    self._conflicts = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load conflicts: {e}")

    def _save_mutations(self) -> None:
        """Save pending mutations to storage."""
        try:
            with open(self._get_mutations_path(), "w") as f:
                json.dump(self._pending_mutations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save mutations: {e}")

    def _save_conflicts(self) -> None:
        """Save conflicts to storage."""
        try:
            with open(self._get_conflicts_path(), "w") as f:
                json.dump(self._conflicts, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save conflicts: {e}")

    def queue_mutation(
        self,
        entity_type: str,
        entity_id: str,
        operation: str,
        payload: dict,
        device_id: str,
    ) -> str:
        """Queue a mutation for synchronization."""

        mutation = PendingMutation(
            mutation_id=f"mut_{__import__('uuid').uuid4().hex[:12]}",
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=payload,
            device_id=device_id,
        )

        self._pending_mutations[mutation.mutation_id] = mutation.to_dict()
        self._save_mutations()
        return mutation.mutation_id

    def get_pending_mutations(self, device_id: str | None = None) -> list[dict]:
        """Get pending mutations, optionally filtered by device."""
        mutations = list(self._pending_mutations.values())
        if device_id:
            mutations = [m for m in mutations if m.get("device_id") == device_id]
        return mutations

    def process_sync(self, request: dict) -> dict:
        """Process a sync request from a device.

        Estado actual (honesto): valida la petición y devuelve el snapshot de
        mutaciones pendientes para el dispositivo. La aplicación de eventos
        entrantes + detección de conflictos por versión llegan con el driver
        de ejecución (corte siguiente, TASK_QUEUE §EXECUTION LAYER).
        """
        device_id = request.get("device_id", "")
        last_sync_at = request.get("last_sync_at", "")

        pending = self.get_pending_mutations(device_id)
        if last_sync_at:
            pending = [m for m in pending if m.get("created_at", "") > last_sync_at]

        return {
            "success": True,
            "events": [],
            "conflicts": [],
            "pending_for_device": pending,
            "server_time": __import__("datetime").datetime.now().isoformat(),
        }

    def register_conflict(self, conflict: dict) -> str:
        """Register a sync conflict."""

        conflict_id = f"conflict_{__import__('uuid').uuid4().hex[:12]}"
        self._conflicts[conflict_id] = {
            "conflict_id": conflict_id,
            **conflict,
        }
        self._save_conflicts()
        return conflict_id

    def resolve_conflict(self, conflict_id: str, strategy: str, resolved_by: str) -> bool:
        """Resolve a conflict with the given strategy."""
        if conflict_id not in self._conflicts:
            return False

        self._conflicts[conflict_id]["strategy"] = strategy
        self._conflicts[conflict_id]["resolved_at"] = __import__("datetime").datetime.now().isoformat()
        self._conflicts[conflict_id]["resolved_by"] = resolved_by
        self._save_conflicts()
        return True

    def get_conflicts(self) -> list[dict]:
        """Get all unresolved conflicts."""
        return [c for c in self._conflicts.values() if not c.get("resolved_at")]

    def get_device_mutations(self, device_id: str) -> list[dict]:
        """Get all pending mutations for a device."""
        return [m for m in self._pending_mutations.values() if m.get("device_id") == device_id]


# Singleton instance
_sync_service = None


def get_sync_service() -> SyncService:
    """Get singleton instance of SyncService."""
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service
