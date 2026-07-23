from __future__ import annotations

from veritrix.buffer import SpanBuffer, compute_backoff
from veritrix.span import SpanSchema
from datetime import UTC, datetime


def _span(name: str = "test") -> SpanSchema:
    now = datetime.now(tz=UTC)
    return SpanSchema(
        trace_id="trace",
        span_id=name,
        name=name,
        start_time=now,
        end_time=now,
    )


def test_buffer_drops_oldest_when_full() -> None:
    buffer = SpanBuffer(max_size=2)
    buffer.append(_span("a"))
    buffer.append(_span("b"))
    buffer.append(_span("c"))

    drained = buffer.drain()
    assert [span.span_id for span in drained] == ["b", "c"]


def test_buffer_requeue_front() -> None:
    buffer = SpanBuffer(max_size=2)
    batch = [_span("a"), _span("b")]
    buffer.requeue_front(batch)

    assert len(buffer) == 2
    assert buffer.drain()[0].span_id == "a"


def test_compute_backoff_grows_exponentially() -> None:
    assert compute_backoff(0) == 0.5
    assert compute_backoff(1) == 1.0
    assert compute_backoff(6) == 30.0
