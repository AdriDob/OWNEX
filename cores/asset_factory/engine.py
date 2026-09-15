"""ASSET_FACTORY engine — scoring, pipeline y priorización de activos.

Formula honesta (nunca inventa demanda):
  score = (gate_score × repeatability_boost × builds_on_ownex_boost) / human_hours
  donde repeatability_boost = 1 + repeatability (0.0→1.0 = ×1.0→×2.0)

GATE obligatorio: si no pasa los 9 criterios → score = 0, no se prioriza.
P(CASH) para assets = gate_passed × (1 si ya monetiza, 0.5 si solo tracción, 0.2 si solo publicado)
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from cores.asset_factory.models import GATE_CRITERIA, Asset, AssetStatus, AssetType

logger = logging.getLogger("ownex.asset_factory")

# Persistencia simple JSON en data-dir (como WorkBank), inyectable para tests.
_DEFAULT_PATH_ENV = "OWNEX_DATA_DIR"


def _data_path() -> Path:
    import os

    base = os.environ.get(_DEFAULT_PATH_ENV) or os.environ.get("CATEYE_DATA_DIR") or "data"
    return Path(base) / "asset_factory.json"


class AssetFactoryEngine:
    """Registry + scoring + pipeline para activos digitales."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path else _data_path()
        self._assets: dict[str, Asset] = {}
        self._load()

    # ——— persistence ———

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for d in data if isinstance(data, list) else data.get("assets", []):
                try:
                    a = Asset(
                        asset_id=d["asset_id"],
                        title=d["title"],
                        asset_type=AssetType(d["asset_type"]),
                        description=d.get("description", ""),
                        status=AssetStatus(d.get("status", "idea")),
                        problem=d.get("problem", ""),
                        evidence_url=d.get("evidence_url", ""),
                        gate=d.get("gate", {}),
                        gate_notes=d.get("gate_notes", {}),
                        distribution_channel=d.get("distribution_channel", "organica_gratuita"),
                        revenue_model=d.get("revenue_model", "suscripcion"),
                        human_hours_est=float(d.get("human_hours_est", 8)),
                        human_hours_actual=float(d.get("human_hours_actual", 0)),
                        builds_on_ownex=bool(d.get("builds_on_ownex", True)),
                        created_at=d.get("created_at", ""),
                        updated_at=d.get("updated_at", ""),
                        users=int(d.get("users", 0)),
                        mrr_usd=float(d.get("mrr_usd", 0)),
                        sales_count=int(d.get("sales_count", 0)),
                        revenue_total_usd=float(d.get("revenue_total_usd", 0)),
                    )
                    self._assets[a.asset_id] = a
                except Exception as e:
                    logger.warning("asset load skip %s: %s", d.get("asset_id"), e)
        except Exception as e:
            logger.warning("asset_factory load failed: %s", e)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps([a.to_dict() for a in self._assets.values()], indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("asset_factory save failed: %s", e)

    # ——— CRUD ———

    def create(self, title: str, asset_type: AssetType | str, **kw: Any) -> Asset:
        at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
        aid = f"asset_{uuid.uuid4().hex[:8]}"
        a = Asset(asset_id=aid, title=title, asset_type=at, **kw)
        self._assets[aid] = a
        self._save()
        return a

    def get(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)

    def list(self, status: AssetStatus | str | None = None) -> list[Asset]:
        if status is None:
            return list(self._assets.values())
        st = AssetStatus(status) if isinstance(status, str) else status
        return [a for a in self._assets.values() if a.status == st]

    def update(self, asset_id: str, **kw: Any) -> Asset | None:
        a = self._assets.get(asset_id)
        if not a:
            return None
        for k, v in kw.items():
            if hasattr(a, k):
                if k == "asset_type":
                    v = AssetType(v) if isinstance(v, str) else v
                if k == "status":
                    v = AssetStatus(v) if isinstance(v, str) else v
                setattr(a, k, v)
        from datetime import UTC, datetime

        a.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return a

    def set_gate(self, asset_id: str, gate: dict[str, bool], notes: dict[str, str] | None = None) -> Asset | None:
        a = self._assets.get(asset_id)
        if not a:
            return None
        # solo criterios válidos, nunca inventa nuevos
        a.gate = {c: bool(gate.get(c, False)) for c in GATE_CRITERIA}
        if notes:
            a.gate_notes = {k: v for k, v in notes.items() if k in GATE_CRITERIA}
        from datetime import UTC, datetime

        a.updated_at = datetime.now(UTC).isoformat()
        # auto-gate: si no pasa → ARCHIVED, si pasa y estaba en IDEA → VALIDATING
        if not a.gate_passed and a.status == AssetStatus.IDEA:
            pass  # queda en IDEA hasta decisión explícita
        self._save()
        return a

    def advance(self, asset_id: str, to_status: AssetStatus | str) -> tuple[bool, str]:
        a = self._assets.get(asset_id)
        if not a:
            return False, "not_found"
        ns = AssetStatus(to_status) if isinstance(to_status, str) else to_status
        # Guard: BUILDING exige gate_passed
        if ns == AssetStatus.BUILDING and not a.gate_passed:
            return False, "gate_not_passed: completa los 9 criterios con evidencia"
        # Guard: MONETIZING/SCALING exige métricas reales
        if ns in (AssetStatus.MONETIZING, AssetStatus.SCALING) and a.sales_count == 0 and a.mrr_usd == 0:
            return False, "no_revenue_yet: registra ventas/MRR reales primero"
        a.status = ns
        from datetime import UTC, datetime

        a.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return True, "ok"

    # ——— scoring ———

    def score(self, asset: Asset) -> dict[str, Any]:
        """Score honesto: 0 si no pasa gate; boost por repeatability y OWNEX reuse."""
        if not asset.gate_passed:
            return {
                "score": 0.0,
                "gate_passed": False,
                "gate_score": round(asset.gate_score, 2),
                "reason": "gate_not_passed",
            }
        base = asset.gate_score  # 1.0 si pasa los 9
        repeat_boost = 1.0 + asset.repeatability  # 1.0→2.0
        ownex_boost = 1.2 if asset.builds_on_ownex else 1.0
        hours = max(1.0, asset.human_hours_est)
        score = round((base * repeat_boost * ownex_boost) / hours * 100, 2)
        # P(CASH) para asset: gate × tracción
        if asset.mrr_usd > 0 or asset.sales_count >= 10:
            p_cash = 1.0
        elif asset.users > 0:
            p_cash = 0.5
        elif asset.status in (AssetStatus.PUBLISHED, AssetStatus.TRACTION):
            p_cash = 0.2
        else:
            p_cash = 0.1
        return {
            "score": score,
            "gate_passed": True,
            "gate_score": round(asset.gate_score, 2),
            "repeatability": round(asset.repeatability, 2),
            "p_cash": p_cash,
            "human_hours_est": hours,
            "builds_on_ownex": asset.builds_on_ownex,
            "reason": f"gate {asset.gate_score:.0%} × repeat ×{repeat_boost:.1f} × ownex ×{ownex_boost:.1f} / {hours:.0f}h",
        }

    def ranked(self, limit: int = 20) -> list[tuple[Asset, dict]]:
        scored = [(a, self.score(a)) for a in self._assets.values()]
        scored.sort(key=lambda x: x[1]["score"], reverse=True)
        return scored[:limit]

    def pipeline_stats(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for a in self._assets.values():
            by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
        total_mrr = sum(a.mrr_usd for a in self._assets.values())
        total_rev = sum(a.revenue_total_usd for a in self._assets.values())
        return {
            "total": len(self._assets),
            "by_status": by_status,
            "total_mrr_usd": round(total_mrr, 2),
            "total_revenue_usd": round(total_rev, 2),
            "gate_passed": sum(1 for a in self._assets.values() if a.gate_passed),
        }

    def next_action(self) -> dict[str, Any] | None:
        """Qué construir hoy: el IDEA con mayor score que pasó gate y aún sin BUILD."""
        candidates = [a for a in self._assets.values() if a.status == AssetStatus.IDEA and a.gate_passed]
        if not candidates:
            # si no hay candidatos, sugerir completar gates
            incomplete = [a for a in self._assets.values() if a.status == AssetStatus.IDEA and not a.gate_passed]
            if incomplete:
                incomplete.sort(key=lambda a: a.gate_score, reverse=True)
                best = incomplete[0]
                missing = [c for c in GATE_CRITERIA if not best.gate.get(c, False)]
                return {"action": "complete_gate", "asset_id": best.asset_id, "title": best.title, "missing": missing}
            return None
        candidates.sort(key=lambda a: self.score(a)["score"], reverse=True)
        best = candidates[0]
        return {"action": "build", "asset_id": best.asset_id, "title": best.title, "score": self.score(best)}


# Singleton factory
_asset_factory: AssetFactoryEngine | None = None


def get_asset_factory(path: Path | None = None) -> AssetFactoryEngine:
    global _asset_factory
    if path is not None:
        return AssetFactoryEngine(path=path)
    if _asset_factory is None:
        _asset_factory = AssetFactoryEngine()
    return _asset_factory


def reset_asset_factory() -> None:
    global _asset_factory
    _asset_factory = None
