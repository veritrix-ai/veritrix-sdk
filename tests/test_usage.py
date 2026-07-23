from __future__ import annotations

from types import SimpleNamespace

from veritrix.usage import extract_llm_usage, parse_usage, usage_attributes


def test_usage_attributes_computes_total() -> None:
    attrs = usage_attributes(prompt_tokens=100, completion_tokens=25, model="gpt-4o-mini")
    assert attrs["agentops.prompt_tokens"] == 100
    assert attrs["agentops.completion_tokens"] == 25
    assert attrs["agentops.total_tokens"] == 125
    assert attrs["agentops.cost_usd"] > 0


def test_parse_usage_reads_agentops_keys() -> None:
    usage = parse_usage(
        {
            "agentops.prompt_tokens": 50,
            "agentops.completion_tokens": 10,
            "agentops.model": "gpt-4o",
        }
    )
    assert usage["prompt_tokens"] == 50
    assert usage["completion_tokens"] == 10
    assert usage["total_tokens"] == 60
    assert usage["model"] == "gpt-4o"


def test_extract_llm_usage_from_llm_output() -> None:
    class Response:
        llm_output = {
            "token_usage": {
                "prompt_tokens": 20,
                "completion_tokens": 5,
                "total_tokens": 25,
            },
            "model_name": "gpt-4o-mini",
        }

    attrs = extract_llm_usage(Response())
    assert attrs["agentops.total_tokens"] == 25
    assert attrs["agentops.model"] == "gpt-4o-mini"


def test_extract_llm_usage_from_generations() -> None:
    generation = SimpleNamespace(
        generation_info={"usage": {"input_tokens": 12, "output_tokens": 3}},
        message=SimpleNamespace(response_metadata={"model_name": "gpt-4o"}),
    )

    class Response:
        llm_output = None
        generations = [[generation]]

    attrs = extract_llm_usage(Response())
    assert attrs["agentops.prompt_tokens"] == 12
    assert attrs["agentops.completion_tokens"] == 3
    assert attrs["agentops.model"] == "gpt-4o"


def test_parse_usage_reads_gen_ai_keys() -> None:
    usage = parse_usage(
        {
            "gen_ai.usage.input_tokens": 30,
            "gen_ai.usage.output_tokens": 7,
            "gen_ai.request.model": "claude-3-5-sonnet",
            "agentops.cost_usd": 0.0123,
        }
    )
    assert usage["prompt_tokens"] == 30
    assert usage["completion_tokens"] == 7
    assert usage["total_tokens"] == 37
    assert usage["model"] == "claude-3-5-sonnet"
    assert usage["cost_usd"] == 0.0123
