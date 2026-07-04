"""Unified settings router — save/load any configuration via key-value store."""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("catseye.api.settings")
router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsBatch(BaseModel):
    settings: dict[str, Any]


@router.get("/all")
def get_all_settings() -> dict[str, Any]:
    """Return every stored setting as a flat key-value dict."""
    from database.db import SessionLocal
    from database.models import RastroConfig
    session = SessionLocal()
    try:
        rows = session.query(RastroConfig).all()
        result = {}
        for r in rows:
            try:
                result[r.key] = json.loads(r.value)
            except (json.JSONDecodeError, TypeError):
                result[r.key] = r.value
        return {"settings": result, "count": len(result)}
    finally:
        session.close()


@router.get("/all/{key:path}")
def get_setting_by_key(key: str) -> Any:
    """Return a single setting by its key path."""
    from cores.settings.service import get_setting
    value = get_setting(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return {"key": key, "value": value}


@router.put("/all")
def save_settings_batch(body: SettingsBatch) -> dict[str, Any]:
    """Save multiple settings at once. Keys with None value are deleted."""
    from cores.settings.service import set_setting
    from database.db import SessionLocal
    from database.models import RastroConfig

    saved = 0
    deleted = 0
    session = SessionLocal()
    try:
        for key, value in body.settings.items():
            if value is None:
                session.query(RastroConfig).filter(RastroConfig.key == key).delete()
                deleted += 1
            else:
                set_setting(key, value)
                saved += 1
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Failed to save settings batch: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        session.close()

    return {"status": "ok", "saved": saved, "deleted": deleted}


@router.delete("/all/{key:path}")
def delete_setting(key: str) -> dict[str, str]:
    """Delete a single setting by its key path."""
    from database.db import SessionLocal
    from database.models import RastroConfig
    session = SessionLocal()
    try:
        rows = session.query(RastroConfig).filter(RastroConfig.key == key).delete()
        session.commit()
        return {"status": "deleted", "key": key, "found": rows > 0}
    finally:
        session.close()
