"""Tests for hybrid telemetry (no-op when OTel disabled)."""

from runtime.telemetry import hybrid_complete_span, hybrid_prepare_span


def test_spans_noop_when_otel_disabled():
    with hybrid_prepare_span("bot-1", "sess", "hello") as span:
        assert span is None
    with hybrid_complete_span("bot-1", "sess", "summary") as span:
        assert span is None
