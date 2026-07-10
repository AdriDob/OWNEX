"""Hook System — allows extensions to run code at specific points.

Hooks are NOT events. Hooks are synchronous callbacks that can:
- Read/modify context before/after an operation
- Short-circuit an operation (return False to cancel)
- Log, monitor, or extend behavior

EventBus is for async communication between apps.
Hooks are for sync extension of Core behavior.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("orion.core.hooks")

HookHandler = Callable[..., Any]


class Hook:
    """A named hook point that multiple extensions can attach to."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._handlers: list[tuple[str, HookHandler]] = []  # (ext_id, handler)

    def register(self, extension_id: str, handler: HookHandler) -> None:
        self._handlers.append((extension_id, handler))
        logger.debug("Hook '%s': %s registered", self.name, extension_id)

    def unregister(self, extension_id: str) -> None:
        self._handlers = [(eid, h) for eid, h in self._handlers if eid != extension_id]

    def run(self, **context: Any) -> list[Any]:
        """Run all handlers sequentially. Returns list of results.

        If any handler returns ``False``, the chain stops (short-circuit).
        """
        results = []
        for ext_id, handler in self._handlers:
            try:
                result = handler(**context)
                results.append(result)
                if result is False:
                    logger.info("Hook '%s' short-circuited by %s", self.name, ext_id)
                    break
            except Exception as exc:
                logger.exception("Hook '%s' handler %s failed: %s", self.name, ext_id, exc)
                results.append(None)
        return results

    @property
    def handler_count(self) -> int:
        return len(self._handlers)


# ── Pre-defined hook points ─────────────────────────

HOOK_POINTS = {
    # CATEYE pipeline
    "before_scan": "Before a scan starts. Context: target_id, scan_type",
    "after_scan": "After a scan completes. Context: target_id, findings_count",
    "before_hypothesis": "Before hypothesis generation. Context: target_id, evidence",
    "after_hypothesis": "After hypothesis generated. Context: hypothesis",
    "before_report": "Before report generation. Context: finding_ids",
    "after_report": "After report generated. Context: report_id",
    "before_publish": "Before publishing/submitting. Context: report_id",
    "after_publish": "After publishing. Context: report_id, response",
    # AI reasoning
    "before_ai_reasoning": "Before AI agent reasons. Context: prompt, tools",
    "after_ai_reasoning": "After AI agent reasons. Context: response, tokens_used",
    # Events
    "before_publish_event": "Before EventBus publish. Context: event, data",
    "after_publish_event": "After EventBus publish. Context: event, data",
    # System
    "before_shutdown": "Before system shutdown. Context: reason",
    "after_startup": "After system startup. Context: apps_count",
}


class HookRegistry:
    """Manages all hook points."""

    def __init__(self) -> None:
        self._hooks: dict[str, Hook] = {}
        for name, description in HOOK_POINTS.items():
            self._hooks[name] = Hook(name)
            self._hooks[name].__doc__ = description

    def get(self, name: str) -> Hook | None:
        return self._hooks.get(name)

    def register_handler(self, hook_name: str, extension_id: str, handler: HookHandler) -> bool:
        hook = self._hooks.get(hook_name)
        if hook is None:
            logger.warning("Unknown hook point: %s", hook_name)
            return False
        hook.register(extension_id, handler)
        return True

    def unregister_extension(self, extension_id: str) -> None:
        for hook in self._hooks.values():
            hook.unregister(extension_id)

    def list_hooks(self) -> list[dict]:
        return [
            {
                "name": name,
                "description": getattr(hook, "__doc__", ""),
                "handlers": hook.handler_count,
            }
            for name, hook in self._hooks.items()
        ]

    def run(self, hook_name: str, **context: Any) -> list[Any]:
        hook = self._hooks.get(hook_name)
        if hook is None:
            return []
        return hook.run(**context)


_registry: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    global _registry
    if _registry is None:
        _registry = HookRegistry()
    return _registry


# ── Decorator for clean handler registration ────────


def on_hook(hook_name: str, extension_id: str | None = None):
    """Decorator: register a function as a hook handler.

    Usage::

        @on_hook("before_scan")
        def my_handler(target_id, scan_type):
            logger.info("About to scan %s", target_id)
    """
    def decorator(func: HookHandler) -> HookHandler:
        registry = get_hook_registry()
        ext_id = extension_id or func.__module__.split(".")[0]
        registry.register_handler(hook_name, ext_id, func)

        @functools.wraps(func)
        def wrapper(**kwargs: Any) -> Any:
            return func(**kwargs)

        return wrapper

    return decorator
