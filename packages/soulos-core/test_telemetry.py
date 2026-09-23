"""Tests for hybrid telemetry spans."""

from __future__ import annotations

import builtins
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

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


def test_record_hybrid_duration_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", False)
    monkeypatch.setattr(telemetry, "_duration_histogram", None)
    telemetry.record_hybrid_duration("prepare", 0.12)


def test_record_hybrid_duration_records_when_histogram_present(monkeypatch):
    hist = MagicMock()
    monkeypatch.setattr(telemetry, "_duration_histogram", hist)
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)
    telemetry.record_hybrid_duration("complete", 0.25)
    hist.record.assert_called_once_with(0.25, {"operation": "complete"})


def test_get_tracer_cached_and_disabled(monkeypatch):
    cached = MagicMock()
    monkeypatch.setattr(telemetry, "_tracer", cached)
    assert telemetry._get_tracer() is cached

    monkeypatch.setattr(telemetry, "_tracer", None)
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", False)
    assert telemetry._get_tracer() is None


def test_get_tracer_import_error(monkeypatch):
    monkeypatch.setattr(telemetry, "_tracer", None)
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)
    real_import = builtins.__import__

    def boom(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("no otel")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", boom)
    assert telemetry._get_tracer() is None


def _install_otel_trace_modules(monkeypatch, fake_trace, FakeResource, FakeProvider, FakeExporter, FakeProcessor):
    monkeypatch.setitem(sys.modules, "opentelemetry", MagicMock(trace=fake_trace))
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", fake_trace)
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
        MagicMock(OTLPSpanExporter=FakeExporter),
    )
    monkeypatch.setitem(
        sys.modules, "opentelemetry.sdk.resources", MagicMock(Resource=FakeResource)
    )
    monkeypatch.setitem(
        sys.modules, "opentelemetry.sdk.trace", MagicMock(TracerProvider=FakeProvider)
    )
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.sdk.trace.export",
        MagicMock(BatchSpanProcessor=FakeProcessor),
    )


def test_get_tracer_builds_with_and_without_endpoint(monkeypatch):
    class FakeResource:
        @staticmethod
        def create(_attrs):
            return MagicMock()

    class FakeProvider:
        def __init__(self, resource=None):
            self.added = []

        def add_span_processor(self, proc):
            self.added.append(proc)

    class FakeExporter:
        pass

    class FakeProcessor:
        def __init__(self, exporter):
            self.exporter = exporter

    fake_trace = MagicMock()
    fake_tracer = MagicMock(name="tracer")
    fake_trace.get_tracer.return_value = fake_tracer
    _install_otel_trace_modules(
        monkeypatch, fake_trace, FakeResource, FakeProvider, FakeExporter, FakeProcessor
    )

    monkeypatch.setattr(telemetry, "_tracer", None)
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    assert telemetry._get_tracer() is fake_tracer

    monkeypatch.setattr(telemetry, "_tracer", None)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert telemetry._get_tracer() is fake_tracer


def test_get_duration_histogram_paths(monkeypatch):
    cached = MagicMock(name="cached-hist")
    monkeypatch.setattr(telemetry, "_duration_histogram", cached)
    assert telemetry._get_duration_histogram() is cached

    monkeypatch.setattr(telemetry, "_duration_histogram", None)
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", False)
    assert telemetry._get_duration_histogram() is None

    monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)
    monkeypatch.setattr(telemetry, "_duration_histogram", None)
    real_import = builtins.__import__

    def boom(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("no otel")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", boom)
    assert telemetry._get_duration_histogram() is None
    monkeypatch.setattr(builtins, "__import__", real_import)

    fake_metrics = MagicMock()
    fake_meter = MagicMock()
    fake_hist = MagicMock(name="hist")
    fake_meter.create_histogram.return_value = fake_hist
    fake_metrics.get_meter.return_value = fake_meter

    class FakeResource:
        @staticmethod
        def create(_a):
            return MagicMock()

    class FakeMeterProvider:
        def __init__(self, resource=None, metric_readers=None):
            pass

    class FakeReader:
        def __init__(self, *a, **k):
            pass

    class FakeExporter:
        pass

    monkeypatch.setitem(sys.modules, "opentelemetry", MagicMock(metrics=fake_metrics))
    monkeypatch.setitem(sys.modules, "opentelemetry.metrics", fake_metrics)
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.exporter.otlp.proto.http.metric_exporter",
        MagicMock(OTLPMetricExporter=FakeExporter),
    )
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.sdk.metrics",
        MagicMock(MeterProvider=FakeMeterProvider),
    )
    monkeypatch.setitem(
        sys.modules,
        "opentelemetry.sdk.metrics.export",
        MagicMock(PeriodicExportingMetricReader=FakeReader),
    )
    monkeypatch.setitem(
        sys.modules, "opentelemetry.sdk.resources", MagicMock(Resource=FakeResource)
    )

    monkeypatch.setattr(telemetry, "_duration_histogram", None)
    monkeypatch.setattr(telemetry, "_meter", None)
    monkeypatch.setattr(telemetry, "OTEL_ENABLED", True)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    assert telemetry._get_duration_histogram() is fake_hist

    monkeypatch.setattr(telemetry, "_duration_histogram", None)
    monkeypatch.setattr(telemetry, "_meter", None)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert telemetry._get_duration_histogram() is fake_hist
