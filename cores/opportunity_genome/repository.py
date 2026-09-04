"""Simple OpportunityGenome repository implementations.

Provides an in-memory repository useful for tests and early wiring.
Persistence adapters can be added later to back this with SQLite/Postgres.
"""

from __future__ import annotations

from typing import Iterable, Optional

from cores.opportunity_genome.models import OpportunityGenome


class InMemoryOpportunityGenomeRepository:
    """In-memory repository for OpportunityGenome objects.

    - `save` performs an upsert keyed by `external_id` when present, otherwise by `id`.
    - `get_by_id`, `get_by_external_id`, `list_all`, and `delete` helpers are provided.
    """

    def __init__(self) -> None:
        self._store: dict[str, OpportunityGenome] = {}
        self._by_external: dict[str, str] = {}

    def save(self, genome: OpportunityGenome) -> OpportunityGenome:
        """Save or update a genome. Returns the saved genome."""
        # Prefer dedupe by external_id when available
        ext = getattr(genome, "external_id", None)
        if ext:
            existing_id = self._by_external.get(ext)
            if existing_id and existing_id != genome.id:
                # remove old id mapping
                self._store.pop(existing_id, None)
            self._by_external[ext] = genome.id

        # store by id
        self._store[genome.id] = genome
        return genome

    def get_by_id(self, id: str) -> Optional[OpportunityGenome]:
        return self._store.get(id)

    def get_by_external_id(self, external_id: str) -> Optional[OpportunityGenome]:
        id = self._by_external.get(external_id)
        if not id:
            return None
        return self._store.get(id)

    def list_all(self) -> Iterable[OpportunityGenome]:
        return list(self._store.values())

    def delete(self, id: str) -> bool:
        obj = self._store.pop(id, None)
        if not obj:
            return False
        # clean external mapping if present
        ext = getattr(obj, "external_id", None)
        if ext and self._by_external.get(ext) == id:
            self._by_external.pop(ext, None)
        return True
