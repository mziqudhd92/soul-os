"""OpenTelemetry spans for hybrid sidecar (OpenInference-aligned)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

OTEL_ENABLED = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip() != "" or os.getenv(
    "SOULOS_OTEL_ENABLED", "0"
).lower() in ("1", "true", "yes")

_tracer = None


def _get_tracer():
    global _tracer
    if _tracer is not None:
        return _tracer
    if not OTEL_ENABLED:
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        resource = Resource.create({"service.name": "soulos-kernel"})
        provider = TracerProvider(resource=resource)
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if endpoint:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("soulos.hybrid")
    except ImportError:
        _tracer = None
    return _tracer


@contextmanager
def hybrid_prepare_span(
    bot_id: str, session_id: str | None, query: str
) -> Generator[object | None, None, None]:
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("soulos.hybrid.prepare") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        span.set_attribute("session.id", session_id or "")
        span.set_attribute("bot.id", bot_id)
        span.set_attribute("input.value", query[:500])
        yield span


@contextmanager
def hybrid_complete_span(
    bot_id: str, session_id: str | None, summary: str
) -> Generator[object | None, None, None]:
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    with tracer.start_as_current_span("soulos.hybrid.complete") as span:
        span.set_attribute("openinference.span.kind", "CHAIN")
        span.set_attribute("session.id", session_id or "")
        span.set_attribute("bot.id", bot_id)
        span.set_attribute("input.value", summary[:500])
        yield span
