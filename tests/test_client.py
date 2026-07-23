from __future__ import annotations

import time

from veritrix.client import IngestClient
from veritrix.config import VeritrixConfig, set_config
from veritrix.span import SpanSchema
from datetime import UTC, datetime


def _span() -> SpanSchema:
    now = datetime.now(tz=UTC)
    return SpanSchema(
        trace_id="trace-1",
        span_id="span-1",
        name="test-span",
        start_time=now,
        end_time=now,
        attributes={
            "agentops.agent_id": "agent",
            "agentops.agent_name": "default",
            "agentops.run_id": "run",
            "agentops.framework": "manual",
            "agentops.span_type": "agent",
        },
    )


def test_client_sends_enqueued_span(transport) -> None:
    set_config(
        VeritrixConfig(
            api_key="test-key",
            endpoint="http://localhost:8001/v1/spans",
            run_id="run",
            trace_id="run",
            agent_id="agent",
        )
    )
    client = IngestClient(transport=transport)
    client.enqueue(_span())
    client.flush()

    assert len(transport.batches) == 1
    assert transport.batches[0][0].name == "test-span"


def test_client_retries_then_succeeds(transport, monkeypatch) -> None:
    set_config(
        VeritrixConfig(
            api_key="test-key",
            endpoint="http://localhost:8001/v1/spans",
            run_id="run",
            trace_id="run",
            agent_id="agent",
        )
    )
    transport.failures_before_success = 1
    monkeypatch.setattr("veritrix.client.sleep_backoff", lambda attempt: None)
    client = IngestClient(transport=transport)
    client.enqueue(_span())
    client.flush()

    assert transport.calls >= 2
    assert len(transport.batches) == 1


def test_client_fail_open_on_persistent_failure(transport, monkeypatch) -> None:
    set_config(
        VeritrixConfig(
            api_key="test-key",
            endpoint="http://localhost:8001/v1/spans",
            run_id="run",
            trace_id="run",
            agent_id="agent",
        )
    )
    transport.should_fail = True
    monkeypatch.setattr("veritrix.client.sleep_backoff", lambda attempt: None)
    client = IngestClient(transport=transport)

    try:
        client.enqueue(_span())
        client.flush()
    except Exception as exc:
        raise AssertionError("client must not raise") from exc

    assert transport.calls >= 1
    assert len(transport.batches) == 0
