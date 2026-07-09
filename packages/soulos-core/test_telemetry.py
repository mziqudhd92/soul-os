"""Tests for hybrid telemetry spans."""

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

import runtime.telemetry as telemetry
from runtime.telemetry import hybrid_complete_span, hybrid_prepare_span


def test_spans_noop_when_otel_disabled(monkeypatch):
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", False)
    monkeypatch.setattr(telemetry, "_tracer", None)
    with hybrid_prepare_span("bot-1", "sess", "hello") as span:
        assert span is None
    with hybrid_complete_span("bot-1", "sess", "summary") as span:
        assert span is None


def test_prepare_span_sets_attributes(monkeypatch):
    span = MagicMock()

    @contextmanager
    def fake_cm(_name):
        yield span

    tracer = MagicMock()
    tracer.start_as_current_span.side_effect = fake_cm
    monkeypatch.setattr(telemetry, "_tracer", tracer)

    with hybrid_prepare_span("bot-1", "sess-1", "What is the refund policy?"):
        pass

    tracer.start_as_current_span.assert_called_once_with("soulos.hybrid.prepare")
    span.set_attribute.assert_any_call("bot.id", "bot-1")
    span.set_attribute.assert_any_call("session.id", "sess-1")
    span.set_attribute.assert_any_call("input.value", "What is the refund policy?")


def test_complete_span_sets_attributes(monkeypatch):
    span = MagicMock()

    @contextmanager
    def fake_cm(_name):
        yield span

    tracer = MagicMock()
    tracer.start_as_current_span.side_effect = fake_cm
    monkeypatch.setattr(telemetry, "_tracer", tracer)

    with hybrid_complete_span("bot-2", None, "User asked about refunds."):
        pass

    tracer.start_as_current_span.assert_called_once_with("soulos.hybrid.complete")
    span.set_attribute.assert_any_call("bot.id", "bot-2")
    span.set_attribute.assert_any_call("session.id", "")
