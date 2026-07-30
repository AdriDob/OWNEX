from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealAction:
    category: str
    file: str
    description: str
    status: str = "fixed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "file": self.file,
            "description": self.description,
            "status": self.status,
        }


@dataclass
class HealReport:
    project_dir: str
    actions: list[HealAction] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.actions)

    @property
    def fixed(self) -> int:
        return sum(1 for a in self.actions if a.status == "fixed")

    @property
    def summary(self) -> str:
        lines = ["OWNEX Self-Heal Report", f"Project: {self.project_dir}", f"Actions taken: {self.total}"]
        for a in self.actions:
            lines.append(f"  [{a.status.upper()}] {a.category}: {a.file} — {a.description}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_dir": self.project_dir,
            "total_actions": self.total,
            "fixed": self.fixed,
            "actions": [a.to_dict() for a in self.actions],
        }
