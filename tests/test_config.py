from __future__ import annotations

from veritrix.config import VeritrixConfig, resolve_endpoint, set_config, get_config


def test_resolve_endpoint_from_explicit_url() -> None:
    assert resolve_endpoint("http://ingest.example.com") == "http://ingest.example.com/v1/spans"
    assert (
        resolve_endpoint("http://ingest.example.com/v1/spans")
        == "http://ingest.example.com/v1/spans"
    )


def test_resolve_endpoint_from_env(monkeypatch) -> None:
    monkeypatch.delenv("VERITRIX_ENDPOINT", raising=False)
    monkeypatch.setenv("AGENTOPS_ENDPOINT", "http://env.example.com")
    assert resolve_endpoint(None) == "http://env.example.com/v1/spans"


def test_resolve_endpoint_prefers_veritrix_env(monkeypatch) -> None:
    monkeypatch.setenv("VERITRIX_ENDPOINT", "http://veritrix.example.com")
    monkeypatch.setenv("AGENTOPS_ENDPOINT", "http://legacy.example.com")
    assert resolve_endpoint(None) == "http://veritrix.example.com/v1/spans"


def test_get_config_requires_init() -> None:
    try:
        get_config()
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_set_and_get_config() -> None:
    config = VeritrixConfig(api_key="abc", run_id="run", trace_id="run", agent_id="agent")
    set_config(config)
    assert get_config().api_key == "abc"
