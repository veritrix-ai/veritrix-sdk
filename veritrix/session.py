from __future__ import annotations

import atexit
import os
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

from veritrix.client import get_client, reset_client
from veritrix.config import VeritrixConfig, reset_config, resolve_endpoint, set_config
from veritrix.integrations import setup_crewai, setup_langchain
from veritrix.span import Framework, SpanType
from veritrix.tracer import ActiveSpan, get_tracer, new_run_ids, reset_tracer

_initialized = False


def init(
    *,
    api_key: str | None = None,
    default_tags: list[str] | None = None,
    endpoint: str | None = None,
    agent_name: str = "default",
    agent_id: str | None = None,
    framework: Framework = "manual",
    auto_start_session: bool = True,
) -> None:
    """Initialize Veritrix and optionally auto-instrument supported frameworks."""
    global _initialized

    resolved_key = api_key or os.getenv("VERITRIX_API_KEY") or os.getenv("AGENTOPS_API_KEY")
    if not resolved_key:
        raise ValueError(
            "Veritrix API key is required. Pass api_key or set VERITRIX_API_KEY."
        )

    config = VeritrixConfig(
        api_key=resolved_key,
        endpoint=resolve_endpoint(endpoint),
        default_tags=list(default_tags or []),
        agent_name=agent_name,
        agent_id=agent_id or uuid.uuid4().hex,
        framework=framework,
    )
    config = new_run_ids(config)
    set_config(config)
    reset_tracer()
    reset_client()

    if auto_start_session:
        tracer = get_tracer()
        root_span = tracer.start_span("session", span_type="agent", framework=framework)
        _store_root_span(root_span)

    setup_langchain()
    setup_crewai()

    if not _initialized:
        atexit.register(end)
        _initialized = True


_root_span: ActiveSpan | None = None


def _store_root_span(span: ActiveSpan) -> None:
    global _root_span
    _root_span = span


@contextmanager
def trace(
    name: str,
    *,
    span_type: SpanType = "agent",
    framework: Framework | None = None,
    attributes: dict[str, Any] | None = None,
    input_data: Any = None,
) -> Iterator[ActiveSpan]:
    """Open a span for manual instrumentation."""
    tracer = get_tracer()
    client = get_client()
    span = tracer.start_span(
        name,
        span_type=span_type,
        framework=framework,
        attributes=attributes,
        input_data=input_data,
    )
    try:
        yield span
    except Exception as exc:
        finished = tracer.end_span(span, status="error", error_message=str(exc))
        client.enqueue(finished)
        raise
    else:
        finished = tracer.end_span(
            span,
            status="ok",
            output_data=span._output_data,
        )
        client.enqueue(finished)


def end() -> None:
    """End the current session, flush spans, and reset SDK state."""
    global _initialized, _root_span

    try:
        tracer = get_tracer()
        client = get_client()

        if _root_span is not None:
            finished = tracer.end_span(_root_span, status="ok")
            client.enqueue(finished)
            _root_span = None

        for finished in tracer.finish_all_open_spans(status="ok"):
            client.enqueue(finished)

        client.flush()
    except Exception:
        pass
    finally:
        reset_client()
        reset_tracer()
        reset_config()
        _initialized = False
        _root_span = None
