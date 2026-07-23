from __future__ import annotations

from typing import Any

from veritrix.client import get_client
from veritrix.tracer import get_tracer

_patched = False


def setup_crewai() -> None:
    global _patched
    if _patched:
        return

    try:
        from crewai import Crew
    except Exception:
        return

    original_init = Crew.__init__

    def patched_init(self: Crew, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        existing_callback = getattr(self, "step_callback", None)
        veritrix_callback = _build_step_callback()

        if existing_callback is None:
            self.step_callback = veritrix_callback
        else:
            self.step_callback = _compose_callbacks(existing_callback, veritrix_callback)

    Crew.__init__ = patched_init  # type: ignore[method-assign]
    _patched = True


def _compose_callbacks(existing: Any, veritrix_callback: Any) -> Any:
    def composed(step: Any) -> None:
        existing(step)
        veritrix_callback(step)

    return composed


def _build_step_callback() -> Any:
    def step_callback(step: Any) -> None:
        try:
            tracer = get_tracer()
            agent_name = _extract_agent_name(step)
            span = tracer.start_span(
                agent_name,
                span_type="agent",
                framework="crewai",
                input_data=_step_input(step),
            )
            finished = tracer.end_span(
                span,
                status="error" if _step_has_error(step) else "ok",
                error_message=_step_error(step),
                output_data=_step_output(step),
                attributes={"agentops.delegation": _is_delegation(step)},
            )
            get_client().enqueue(finished)
        except Exception:
            pass

    return step_callback


def _extract_agent_name(step: Any) -> str:
    agent = getattr(step, "agent", None)
    if agent is not None:
        role = getattr(agent, "role", None)
        if role:
            return str(role)
    return getattr(step, "agent_name", None) or "crew found agent step"


def _step_input(step: Any) -> Any:
    for attr in ("input", "task", "prompt"):
        value = getattr(step, attr, None)
        if value is not None:
            return value
    return None


def _step_output(step: Any) -> Any:
    for attr in ("output", "result", "raw"):
        value = getattr(step, attr, None)
        if value is not None:
            return value
    return None


def _step_has_error(step: Any) -> bool:
    return bool(getattr(step, "error", None) or getattr(step, "exception", None))


def _step_error(step: Any) -> str | None:
    error = getattr(step, "error", None) or getattr(step, "exception", None)
    return str(error) if error else None


def _is_delegation(step: Any) -> bool:
    action = str(getattr(step, "action", "") or "").lower()
    return "delegate" in action
