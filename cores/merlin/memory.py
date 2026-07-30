"""MERLIN Memory — Office Retro Modernized Memory System."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ownex.merlin.memory")


class MemoryType(Enum):
    """Types of memory entries."""
    CONVERSATION = "conversation"
    PATTERN = "pattern"
    WORKFLOW = "workflow"
    STRATEGY = "strategy"
    KNOWLEDGE = "knowledge"
    NOTE = "note"


@dataclass
class MemoryEntry:
    """A memory entry."""
    id: str
    type: MemoryType
    title: str
    content: str
    timestamp: datetime
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            title=data["title"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None
        )


class MerlinMemory:
    """MERLIN's memory system with retro office styling."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.cwd() / "database" / "merlin_memory.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._memories: Dict[str, MemoryEntry] = {}
        self._load_memories()

    def _load_memories(self) -> None:
        """Load memories from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for entry_data in data.get("memories", []):
                        entry = MemoryEntry.from_dict(entry_data)
                        self._memories[entry.id] = entry
                logger.info(f"Loaded {len(self._memories)} memories from storage")
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")
                self._memories = {}

    def _save_memories(self) -> None:
        """Save memories to storage."""
        try:
            data = {
                "memories": [entry.to_dict() for entry in self._memories.values()],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self._memories)} memories to storage")
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")

    async def save_conversation(
        self,
        question: str,
        response: str,
        timestamp: datetime,
        tags: Optional[List[str]] = None
    ) -> str:
        """Save a conversation to memory."""
        entry_id = f"conv_{timestamp.timestamp()}"

        entry = MemoryEntry(
            id=entry_id,
            type=MemoryType.CONVERSATION,
            title=f"Conversation - {timestamp.strftime('%Y-%m-%d %H:%M')}",
            content=f"Q: {question}\nA: {response}",
            timestamp=timestamp,
            tags=tags or ["conversation"],
            metadata={"question": question, "response": response}
        )

        self._memories[entry_id] = entry
        self._save_memories()

        logger.info(f"Saved conversation memory: {entry_id}")
        return entry_id

    async def save_pattern(
        self,
        title: str,
        pattern: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """Save a pattern to memory."""
        entry_id = f"pattern_{datetime.now().timestamp()}"

        entry = MemoryEntry(
            id=entry_id,
            type=MemoryType.PATTERN,
            title=title,
            content=pattern,
            timestamp=datetime.now(),
            tags=tags or ["pattern"],
            metadata={"pattern": pattern}
        )

        self._memories[entry_id] = entry
        self._save_memories()

        logger.info(f"Saved pattern memory: {entry_id}")
        return entry_id

    async def save_workflow(
        self,
        title: str,
        workflow: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """Save a workflow to memory."""
        entry_id = f"workflow_{datetime.now().timestamp()}"

        entry = MemoryEntry(
            id=entry_id,
            type=MemoryType.WORKFLOW,
            title=title,
            content=workflow,
            timestamp=datetime.now(),
            tags=tags or ["workflow"],
            metadata={"workflow": workflow}
        )

        self._memories[entry_id] = entry
        self._save_memories()

        logger.info(f"Saved workflow memory: {entry_id}")
        return entry_id

    async def save_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """Save a note to memory."""
        entry_id = f"note_{datetime.now().timestamp()}"

        entry = MemoryEntry(
            id=entry_id,
            type=MemoryType.NOTE,
            title=title,
            content=content,
            timestamp=datetime.now(),
            tags=tags or ["note"],
            metadata={"note": content}
        )

        self._memories[entry_id] = entry
        self._save_memories()

        logger.info(f"Saved note memory: {entry_id}")
        return entry_id

    async def get_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory entry."""
        entry = self._memories.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._save_memories()
        return entry

    async def get_recent_memories(
        self,
        limit: int = 10,
        memory_type: Optional[MemoryType] = None
    ) -> List[MemoryEntry]:
        """Get recent memories."""
        memories = list(self._memories.values())

        if memory_type:
            memories = [m for m in memories if m.type == memory_type]

        # Sort by timestamp descending
        memories.sort(key=lambda m: m.timestamp, reverse=True)

        return memories[:limit]

    async def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories by query."""
        query_lower = query.lower()
        results = []

        for entry in self._memories.values():
            if (
                query_lower in entry.title.lower() or
                query_lower in entry.content.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)

        # Sort by access count and timestamp
        results.sort(key=lambda m: (m.access_count, m.timestamp), reverse=True)

        return results[:limit]

    async def cleanup_old_memories(self, retention_days: int = 90) -> int:
        """Clean up old memories beyond retention period."""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        to_remove = [
            entry_id for entry_id, entry in self._memories.items()
            if entry.timestamp < cutoff_date and entry.type != MemoryType.PATTERN
        ]

        for entry_id in to_remove:
            del self._memories[entry_id]

        if to_remove:
            self._save_memories()
            logger.info(f"Cleaned up {len(to_remove)} old memories")

        return len(to_remove)

    async def get_memories_by_tag(self, tag: str) -> List[MemoryEntry]:
        """Get memories by tag."""
        return [m for m in self._memories.values() if tag in m.tags]

    async def get_memories_by_type(self, memory_type: MemoryType) -> List[MemoryEntry]:
        """Get memories by type."""
        return [m for m in self._memories.values() if m.type == memory_type]

    async def update_memory(
        self,
        entry_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Update a memory entry."""
        entry = self._memories.get(entry_id)
        if not entry:
            return False

        if title:
            entry.title = title
        if content:
            entry.content = content
        if tags:
            entry.tags = tags

        entry.last_accessed = datetime.now()
        self._save_memories()

        logger.info(f"Updated memory: {entry_id}")
        return True

    async def delete_memory(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        if entry_id in self._memories:
            del self._memories[entry_id]
            self._save_memories()
            logger.info(f"Deleted memory: {entry_id}")
            return True
        return False

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        memories = list(self._memories.values())

        type_counts = {}
        for mem_type in MemoryType:
            type_counts[mem_type.value] = len([m for m in memories if m.type == mem_type])

        total_access = sum(m.access_count for m in memories)

        return {
            "total_memories": len(memories),
            "type_counts": type_counts,
            "total_access_count": total_access,
            "oldest_memory": min((m.timestamp for m in memories), default=None),
            "newest_memory": max((m.timestamp for m in memories), default=None)
        }


# Singleton instance
_merlin_memory: Optional[MerlinMemory] = None


def get_merlin_memory() -> MerlinMemory:
    """Get the singleton MerlinMemory instance."""
    global _merlin_memory
    if _merlin_memory is None:
        _merlin_memory = MerlinMemory()
    return _merlin_memory


def reset_merlin_memory() -> None:
    """Reset the singleton MerlinMemory instance."""
    global _merlin_memory
    _merlin_memory = None
