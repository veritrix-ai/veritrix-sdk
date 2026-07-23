from __future__ import annotations

from typing import Any

PROMPT_TOKEN_KEYS = (
    "agentops.prompt_tokens",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.prompt_tokens",
    "llm.usage.prompt_tokens",
)

COMPLETION_TOKEN_KEYS = (
    "agentops.completion_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.usage.completion_tokens",
    "llm.usage.completion_tokens",
)

TOTAL_TOKEN_KEYS = (
    "agentops.total_tokens",
    "gen_ai.usage.total_tokens",
    "llm.usage.total_tokens",
)

MODEL_KEYS = (
    "agentops.model",
    "gen_ai.request.model",
    "gen_ai.response.model",
    "llm.model_name",
)

COST_KEYS = ("agentops.cost_usd", "gen_ai.usage.cost")


def usage_attributes(
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    model: str | None = None,
    cost_usd: float | None = None,
) -> dict[str, Any]:
    """Build OTel-compatible usage attributes for LLM spans."""
    attrs: dict[str, Any] = {}
    if prompt_tokens is not None:
        attrs["agentops.prompt_tokens"] = prompt_tokens
        attrs["gen_ai.usage.input_tokens"] = prompt_tokens
    if completion_tokens is not None:
        attrs["agentops.completion_tokens"] = completion_tokens
        attrs["gen_ai.usage.output_tokens"] = completion_tokens
    if total_tokens is not None:
        attrs["agentops.total_tokens"] = total_tokens
        attrs["gen_ai.usage.total_tokens"] = total_tokens
    elif prompt_tokens is not None and completion_tokens is not None:
        computed = prompt_tokens + completion_tokens
        attrs["agentops.total_tokens"] = computed
        attrs["gen_ai.usage.total_tokens"] = computed
    if model:
        attrs["agentops.model"] = model
        attrs["gen_ai.request.model"] = model
    if cost_usd is None and (prompt_tokens or completion_tokens):
        from veritrix.pricing import estimate_cost_usd

        cost_usd = estimate_cost_usd(model, prompt_tokens or 0, completion_tokens or 0)
    if cost_usd is not None:
        attrs["agentops.cost_usd"] = cost_usd
    return attrs


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_int(attributes: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        parsed = _coerce_int(attributes.get(key))
        if parsed is not None:
            return parsed
    return None


def _first_str(attributes: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def parse_usage(attributes: dict[str, Any]) -> dict[str, Any]:
    """Extract normalized usage fields from span attributes."""
    prompt_tokens = _first_int(attributes, PROMPT_TOKEN_KEYS)
    completion_tokens = _first_int(attributes, COMPLETION_TOKEN_KEYS)
    total_tokens = _first_int(attributes, TOTAL_TOKEN_KEYS)
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "model": _first_str(attributes, MODEL_KEYS),
        "cost_usd": _first_float(attributes, COST_KEYS),
    }


def _first_float(attributes: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        parsed = _coerce_float(attributes.get(key))
        if parsed is not None:
            return parsed
    return None


def extract_llm_usage(response: Any) -> dict[str, Any]:
    """Best-effort token extraction from LangChain LLMResult / chat responses."""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    model: str | None = None

    llm_output = getattr(response, "llm_output", None)
    token_usage: Any = None
    if isinstance(llm_output, dict):
        token_usage = llm_output.get("token_usage") or llm_output.get("usage")
        model = llm_output.get("model_name") or llm_output.get("model")

    if token_usage is None and hasattr(response, "generations"):
        try:
            generation = response.generations[0][0]
            generation_info = getattr(generation, "generation_info", None) or {}
            if isinstance(generation_info, dict):
                token_usage = generation_info.get("usage") or generation_info.get("token_usage")
            message = getattr(generation, "message", None)
            response_metadata = getattr(message, "response_metadata", None) or {}
            if isinstance(response_metadata, dict):
                token_usage = token_usage or response_metadata.get("token_usage")
                model = model or response_metadata.get("model_name") or response_metadata.get("model")
        except (IndexError, TypeError, AttributeError):
            pass

    if isinstance(token_usage, dict):
        prompt_tokens = _coerce_int(
            token_usage.get("prompt_tokens")
            or token_usage.get("input_tokens")
            or token_usage.get("prompt_token_count")
        )
        completion_tokens = _coerce_int(
            token_usage.get("completion_tokens")
            or token_usage.get("output_tokens")
            or token_usage.get("completion_token_count")
        )
        total_tokens = _coerce_int(token_usage.get("total_tokens") or token_usage.get("total_token_count"))

    return usage_attributes(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
    )
