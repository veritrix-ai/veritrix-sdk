from __future__ import annotations

import veritrix
from veritrix.client import IngestClient, reset_client
from veritrix.config import get_config


def _use_transport(transport) -> None:
    reset_client()
    import veritrix.client as client_module

    client_module._client = IngestClient(transport=transport)


def test_init_sets_config_and_root_span(transport, monkeypatch) -> None:
    monkeypatch.setenv("VERITRIX_API_KEY", "test-key")

    veritrix.init(api_key="test-key", default_tags=["crewai"], framework="manual")
    _use_transport(transport)

    config = get_config()
    assert config.api_key == "test-key"
    assert config.default_tags == ["crewai"]
    assert config.run_id == config.trace_id

    veritrix.end()


def test_init_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("VERITRIX_API_KEY", raising=False)
    monkeypatch.delenv("AGENTOPS_API_KEY", raising=False)

    try:
        veritrix.init()
        raised = False
    except ValueError:
        raised = True

    assert raised


def test_trace_context_manager_sends_span(transport, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_API_KEY", "test-key")
    veritrix.init(api_key="test-key")
    _use_transport(transport)

    with veritrix.trace("manual-step", span_type="tool", input_data={"q": "hello"}):
        pass

    veritrix.end()

    assert transport.batches
    finished = next(
        span for batch in transport.batches for span in batch if span.name == "manual-step"
    )
    assert finished.attributes["agentops.span_type"] == "tool"
    assert finished.input_preview


def test_trace_records_errors(transport, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_API_KEY", "test-key")
    veritrix.init(api_key="test-key")
    _use_transport(transport)

    try:
        with veritrix.trace("failing-step"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    veritrix.end()

    finished = next(
        span for batch in transport.batches for span in batch if span.name == "failing-step"
    )
    assert finished.status == "error"
    assert finished.error_message == "boom"
