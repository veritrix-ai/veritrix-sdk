from __future__ import annotations

from veritrix.pricing import (
    DEFAULT_PRICING,
    estimate_cost_usd,
    get_model_pricing,
    normalize_model_name,
)


def test_normalize_model_name_strips_provider_prefixes() -> None:
    assert normalize_model_name("openai:gpt-4o-mini") == "gpt-4o-mini"
    assert normalize_model_name("azure:gpt-4o") == "gpt-4o"
    assert normalize_model_name(None) == ""


def test_get_model_pricing_exact_and_fuzzy_match() -> None:
    assert get_model_pricing("gpt-4o-mini") == DEFAULT_PRICING
    assert get_model_pricing("openai:gpt-4o")["input"] == 2.50
    assert get_model_pricing("unknown-model-xyz") == DEFAULT_PRICING


def test_estimate_cost_usd() -> None:
    cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
    assert cost == DEFAULT_PRICING["input"]
