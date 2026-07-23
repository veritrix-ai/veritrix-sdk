from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from veritrix.client import IngestClient, reset_client
from veritrix.config import VeritrixConfig, set_config
from veritrix.integrations.crewai import _build_step_callback, setup_crewai
from veritrix.integrations.langchain import setup_langchain
from veritrix.tracer import get_tracer, reset_tracer


def test_langchain_handler_creates_spans(monkeypatch) -> None:
    langchain_core = pytest.importorskip("langchain_core")
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.callbacks.manager import CallbackManager

    set_config(
        VeritrixConfig(
            api_key="key",
            run_id="run",
            trace_id="run",
            agent_id="agent",
            framework="langchain",
        )
    )
    reset_tracer()
    transport_batches: list = []

    class FakeTransport:
        def send_batch(self, spans):  # type: ignore[no-untyped-def]
            transport_batches.append(spans)

    reset_client()
    client = IngestClient(transport=FakeTransport())

    monkeypatch.setattr("veritrix.integrations.langchain.get_client", lambda: client)

    setup_langchain()
    manager = CallbackManager.configure(local_callbacks=[])

    handler = next(
        callback for callback in manager.handlers if isinstance(callback, BaseCallbackHandler)
    )

    run_id = uuid4()
    handler.on_chain_start({"name": "test-chain"}, {"input": "hello"}, run_id=run_id)
    handler.on_chain_end({"output": "world"}, run_id=run_id)
    client.flush()

    assert transport_batches
    span = transport_batches[0][0]
    assert span.name == "test-chain"
    assert span.attributes["agentops.framework"] == "langchain"


def test_crewai_step_callback_enqueues_span(monkeypatch) -> None:
    set_config(
        VeritrixConfig(
            api_key="key",
            run_id="run",
            trace_id="run",
            agent_id="agent",
            framework="crewai",
        )
    )
    reset_tracer()
    transport_batches: list = []

    class FakeTransport:
        def send_batch(self, spans):  # type: ignore[no-untyped-def]
            transport_batches.append(spans)

    reset_client()
    client = IngestClient(transport=FakeTransport())
    monkeypatch.setattr("veritrix.integrations.crewai.get_client", lambda: client)

    callback = _build_step_callback()
    step = SimpleNamespace(
        agent=SimpleNamespace(role="Research Analyst"),
        output="Completed research",
        error=None,
        action="research",
    )
    callback(step)
    client.flush()

    assert transport_batches
    assert transport_batches[0][0].name == "Research Analyst"


def test_crewai_patch_wraps_existing_callback(monkeypatch) -> None:
    import sys
    from types import ModuleType

    import veritrix.integrations.crewai as crewai_mod

    calls: list[str] = []

    class FakeCrew:
        def __init__(self) -> None:
            self.step_callback = lambda step: calls.append("existing")

    fake_crewai = ModuleType("crewai")
    fake_crewai.Crew = FakeCrew

    crewai_mod._patched = False
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    setup_crewai()

    crew = FakeCrew()
    assert crew.step_callback is not None
    crew.step_callback(
        SimpleNamespace(
            agent=SimpleNamespace(role="Writer"),
            output="ok",
            error=None,
            action="run",
        )
    )
    assert "existing" in calls
