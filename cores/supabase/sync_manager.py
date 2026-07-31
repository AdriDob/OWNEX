"""
Supabase Sync Manager — Sistema de Sincronización con Supabase

Usa Supabase para autenticación y sincronización en la nube.
100% gratuito (Free Tier) y open source.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.supabase_sync")


class SupabaseSyncManager:
    """Gestor de sincronización con Supabase."""

    def __init__(self, supabase_url: str, supabase_key: str):
        """Inicializar sync manager con Supabase."""
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client = None  # Se inicializa cuando se importe supabase

    def _get_client(self):
        """Obtener cliente de Supabase."""
        try:
            from supabase import create_client

            if self.client is None:
                self.client = create_client(self.supabase_url, self.supabase_key)

            return self.client
        except ImportError:
            logger.error("Supabase client not installed. Run: pip install supabase")
            return None

    def sync_task(self, user_id: str, task_data: dict[str, Any]) -> bool:
        """Sincronizar tarea con Supabase."""
        client = self._get_client()

        if not client:
            return False

        try:
            # Upsert task (insert or update)
            client.table('tasks').upsert(task_data).execute()

            logger.info(f"Task synced to Supabase: {task_data.get('task_id')}")
            return True
        except Exception as e:
            logger.error(f"Error syncing task to Supabase: {e}")
            return False

    def sync_goal(self, user_id: str, goal_data: dict[str, Any]) -> bool:
        """Sincronizar meta con Supabase."""
        client = self._get_client()

        if not client:
            return False

        try:
            client.table('goals').upsert(goal_data).execute()

            logger.info(f"Goal synced to Supabase: {goal_data.get('goal_id')}")
            return True
        except Exception as e:
            logger.error(f"Error syncing goal to Supabase: {e}")
            return False

    def sync_habit(self, user_id: str, habit_data: dict[str, Any]) -> bool:
        """Sincronizar hábito con Supabase."""
        client = self._get_client()

        if not client:
            return False

        try:
            client.table('habits').upsert(habit_data).execute()

            logger.info(f"Habit synced to Supabase: {habit_data.get('habit_id')}")
            return True
        except Exception as e:
            logger.error(f"Error syncing habit to Supabase: {e}")
            return False

    def sync_daily_mood(self, user_id: str, mood_data: dict[str, Any]) -> bool:
        """Sincronizar estado de ánimo con Supabase."""
        client = self._get_client()

        if not client:
            return False

        try:
            client.table('daily_moods').upsert(mood_data).execute()

            logger.info(f"Daily mood synced to Supabase: {mood_data.get('date')}")
            return True
        except Exception as e:
            logger.error(f"Error syncing daily mood to Supabase: {e}")
            return False

    def get_user_tasks(self, user_id: str) -> list[dict[str, Any]]:
        """Obtener tareas del usuario desde Supabase."""
        client = self._get_client()

        if not client:
            return []

        try:
            response = client.table('tasks').select('*').eq('user_id', user_id).execute()

            return response.data
        except Exception as e:
            logger.error(f"Error getting tasks from Supabase: {e}")
            return []

    def get_user_goals(self, user_id: str) -> list[dict[str, Any]]:
        """Obtener metas del usuario desde Supabase."""
        client = self._get_client()

        if not client:
            return []

        try:
            response = client.table('goals').select('*').eq('user_id', user_id).execute()

            return response.data
        except Exception as e:
            logger.error(f"Error getting goals from Supabase: {e}")
            return []

    def get_user_habits(self, user_id: str) -> list[dict[str, Any]]:
        """Obtener hábitos del usuario desde Supabase."""
        client = self._get_client()

        if not client:
            return []

        try:
            response = client.table('habits').select('*').eq('user_id', user_id).execute()

            return response.data
        except Exception as e:
            logger.error(f"Error getting habits from Supabase: {e}")
            return []

    def get_user_daily_moods(self, user_id: str, limit: int = 7) -> list[dict[str, Any]]:
        """Obtener estados de ánimo del usuario desde Supabase."""
        client = self._get_client()

        if not client:
            return []

        try:
            response = client.table('daily_moods').select('*').eq('user_id', user_id).order('date', desc=True).limit(limit).execute()

            return response.data
        except Exception as e:
            logger.error(f"Error getting daily moods from Supabase: {e}")
            return []

    def subscribe_to_changes(self, user_id: str, table: str, callback):
        """Suscribirse a cambios en tiempo real (WebSocket)."""
        client = self._get_client()

        if not client:
            return False

        try:
            # Supabase realtime subscription
            client.realtime.subscribe(
                f'{table}:user_id=eq.{user_id}',
                callback
            )

            logger.info(f"Subscribed to {table} changes for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to Supabase realtime: {e}")
            return False


# Singleton instance
_supabase_sync_manager: SupabaseSyncManager | None = None


def get_supabase_sync_manager() -> SupabaseSyncManager | None:
    """Obtener instancia singleton de SupabaseSyncManager."""
    global _supabase_sync_manager

    if _supabase_sync_manager is None:
        from os import getenv

        supabase_url = getenv("SUPABASE_URL")
        supabase_key = getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
            return None

        _supabase_sync_manager = SupabaseSyncManager(supabase_url, supabase_key)

    return _supabase_sync_manager
