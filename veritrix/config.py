from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field

from veritrix.span import Framework


@dataclass
class VeritrixConfig:
    api_key: str = ""
    endpoint: str = "http://localhost:8001/v1/spans"
    default_tags: list[str] = field(default_factory=list)
    agent_id: str = ""
    agent_name: str = "default"
    run_id: str = ""
    trace_id: str = ""
    framework: Framework = "manual"
    auto_end: bool = True


_config: VeritrixConfig | None = None
_config_lock = threading.Lock()


def get_config() -> VeritrixConfig:
    if _config is None:
        raise RuntimeError("veritrix.init() must be called before using the SDK")
    return _config


def set_config(config: VeritrixConfig) -> None:
    global _config
    with _config_lock:
        _config = config


def reset_config() -> None:
    global _config
    with _config_lock:
        _config = None


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def resolve_endpoint(explicit: str | None) -> str:
    if explicit:
        return explicit.rstrip("/") if explicit.endswith("/v1/spans") else f"{explicit.rstrip('/')}/v1/spans"
    env_endpoint = _env("VERITRIX_ENDPOINT", "AGENTOPS_ENDPOINT")
    if env_endpoint:
        return (
            env_endpoint.rstrip("/")
            if env_endpoint.endswith("/v1/spans")
            else f"{env_endpoint.rstrip('/')}/v1/spans"
        )
    return "http://localhost:8001/v1/spans"
