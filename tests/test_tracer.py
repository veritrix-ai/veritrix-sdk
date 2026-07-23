from __future__ import annotations

import veritrix
from veritrix.config import VeritrixConfig, set_config
from veritrix.tracer import get_tracer


def test_tracer_nests_spans() -> None:
    set_config(
        VeritrixConfig(
            api_key="key",
            run_id="run",
            trace_id="run",
            agent_id="agent",
        )
    )
    tracer = get_tracer()

    parent = tracer.start_span("parent", span_type="agent")
    child = tracer.start_span("child", span_type="tool")

    assert child.parent_span_id == parent.span_id

    finished_child = tracer.end_span(child)
    finished_parent = tracer.end_span(parent)

    assert finished_child.attributes["agentops.span_type"] == "tool"
    assert finished_parent.attributes["agentops.span_type"] == "agent"
    assert finished_child.parent_span_id == parent.span_id


def test_tracer_truncates_previews() -> None:
    set_config(
        VeritrixConfig(
            api_key="key",
            run_id="run",
            trace_id="run",
            agent_id="agent",
        )
    )
    tracer = get_tracer()
    span = tracer.start_span("long", span_type="llm", input_data="x" * 1000)
    finished = tracer.end_span(span, output_data={"value": "y" * 1000})

    assert len(finished.input_preview) == 500
    assert len(finished.output_preview) == 500
