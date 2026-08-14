"""
Observability setup: OpenTelemetry traces/metrics + Langfuse LLM tracing.
"""
import os
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("agent-service.observability")

# ── Langfuse ────────────────────────────────────────────────────────────────

_langfuse = None

def _get_langfuse():
    global _langfuse
    if _langfuse is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
        host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
        if public_key and secret_key:
            try:
                from langfuse import Langfuse
                _langfuse = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host,
                )
                logger.info("Langfuse connected at %s", host)
            except Exception as e:
                logger.warning("Langfuse init failed: %s", e)
        else:
            logger.info("Langfuse keys not set, tracing disabled")
    return _langfuse


class LangfuseTrace:
    """Lightweight wrapper to create Langfuse traces for agent runs."""

    def __init__(self, name: str, session_id: str, request_id: str, prompt: str):
        self.trace = None
        self.trace_id = None
        lf = _get_langfuse()
        if lf:
            try:
                self.trace = lf.trace(
                    name=name,
                    session_id=session_id,
                    metadata={"request_id": request_id},
                    input=prompt,
                )
                self.trace_id = self.trace.id
            except Exception as e:
                logger.warning("Langfuse trace create failed: %s", e)

    def span(self, name: str, **kwargs):
        if self.trace:
            try:
                return self.trace.span(name=name, **kwargs)
            except Exception:
                pass
        return _NoOpSpan()

    def generation(self, name: str, **kwargs):
        if self.trace:
            try:
                return self.trace.generation(name=name, **kwargs)
            except Exception:
                pass
        return _NoOpSpan()

    def update(self, **kwargs):
        if self.trace:
            try:
                self.trace.update(**kwargs)
            except Exception:
                pass

    def end(self, output=None):
        if self.trace:
            try:
                self.trace.update(output=output)
            except Exception:
                pass
        lf = _get_langfuse()
        if lf:
            try:
                lf.flush()
            except Exception:
                pass


class _NoOpSpan:
    def update(self, **kwargs): pass
    def end(self, **kwargs): pass


# ── Prometheus custom metrics ───────────────────────────────────────────────

try:
    from prometheus_client import Histogram, Counter

    llm_call_duration = Histogram(
        "llm_call_duration_seconds",
        "Duration of LLM (Ollama) calls",
        ["step"],
        buckets=[1, 2, 5, 10, 20, 30, 60, 120],
    )
    tool_call_counter = Counter(
        "tool_calls_total",
        "Total tool calls made by agent",
        ["tool_name"],
    )
    agent_run_counter = Counter(
        "agent_runs_total",
        "Total agent runs",
        ["status"],
    )
except ImportError:
    # Fallback no-ops
    class _NoOpMetric:
        def labels(self, *a, **k): return self
        def observe(self, *a): pass
        def inc(self, *a): pass
    llm_call_duration = _NoOpMetric()
    tool_call_counter = _NoOpMetric()
    agent_run_counter = _NoOpMetric()


@contextmanager
def track_llm_call(step: str):
    """Context manager to time LLM calls."""
    start = time.time()
    yield
    llm_call_duration.labels(step=step).observe(time.time() - start)


# ── OTel setup ──────────────────────────────────────────────────────────────

def setup_otel(app):
    """Instrument FastAPI with OpenTelemetry and Prometheus."""
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    # OTel tracing
    if otel_endpoint:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            resource = Resource.create({"service.name": "agent-service"})
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=f"{otel_endpoint}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)

            FastAPIInstrumentor.instrument_app(app)
            HTTPXClientInstrumentor().instrument()
            logger.info("OTel tracing enabled → %s", otel_endpoint)
        except Exception as e:
            logger.warning("OTel setup failed: %s", e)

    # Prometheus /metrics endpoint
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
        logger.info("Prometheus /metrics enabled")
    except Exception as e:
        logger.warning("Prometheus instrumentator failed: %s", e)
