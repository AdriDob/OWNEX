from __future__ import annotations

import logging
import os
from collections.abc import Callable
from functools import wraps

logger = logging.getLogger("ownex.opentelemetry")


def _init_tracer_provider() -> None:
    """Initialize the OpenTelemetry tracer provider with resource detection.

    Only runs once; subsequent calls are no-ops. If OTel environment variables
    are not set, a no-op tracer is used so the rest of the code works without
    changes.
    """
    # Check if OTel is disabled via env var
    if os.environ.get("OTEL_DISABLED", "").lower() in {"1", "true", "yes"}:
        logger.info("OpenTelemetry disabled via OTEL_DISABLED env var")
        return

    # Try to detect cloud environment for resource attributes
    resource_attrs: dict[str, str] = {}

    # Cloud provider detection
    cloud_provider = os.environ.get("OTEL_CLOUD_PROVIDER", "")
    if cloud_provider:
        resource_attrs["cloud.provider"] = cloud_provider

    # Kubernetes namespace
    k8s_namespace = os.environ.get("OTEL_K8S_NAMESPACE", "")
    if k8s_namespace:
        resource_attrs["k8s.namespace"] = k8s_namespace

    # Service name from env, default to OWNEX API
    service_name = os.environ.get("OTEL_SERVICE_NAME", "ownex-api")

    try:
        from opentelemetry.sdk.resources import Resource

        attributes = {}
        if cloud_provider:
            attributes["cloud.provider"] = cloud_provider
        if k8s_namespace:
            attributes["k8s.namespace"] = k8s_namespace
        attributes["service.name"] = service_name

        resource = Resource.create(attributes)

        # Set the global tracer provider — must be a TracerProvider, not the
        # Resource itself (FastAPI telemetry calls provider.get_tracer).
        from opentelemetry import trace as otel_trace
        from opentelemetry.sdk.trace import TracerProvider

        otel_trace.set_tracer_provider(TracerProvider(resource=resource))
        logger.info("OpenTelemetry tracer initialized: %s", service_name)
    except Exception as e:
        logger.warning("Failed to initialize OpenTelemetry: %s", e)
        # Fall back to no-op; the app continues normally


# Initialize on import (safe to call multiple times)
_init_tracer_provider()


def trace_endpoint(operation_name: str | None = None):
    """Decorator to add manual tracing to endpoint functions.

    Args:
        operation_name: Custom span name. If not provided, uses the route path.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from opentelemetry import trace as otel_trace

            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            with otel_trace.get_tracer(span_name).start_as_current_context(span_name) as span:
                # Set common attributes
                if span.is_recording():
                    span.set_attribute("http.method", kwargs.get("method", "GET"))
                    span.set_attribute("http.url", kwargs.get("path", ""))
                try:
                    result = await func(*args, **kwargs)
                    if span.is_recording():
                        span.set_status({"code": "OK"})
                    return result
                except Exception as e:
                    if span.is_recording():
                        span.record_exception(e)
                        span.set_status({"code": "ERROR", "message": str(e)})
                    raise

        return wrapper

    return decorator
