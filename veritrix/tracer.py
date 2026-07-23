from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from datetime import UTC, datetime
from typing import Any

from veritrix.config import VeritrixConfig, get_config
from veritrix.span import Framework, SpanSchema, SpanStatus, SpanType


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _preview(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, default=str)
        except (TypeError, ValueError):
            text = str(value)
    return text[:limit]


class ActiveSpan:
    __slots__ = (
        "span_id",
        "trace_id",
        "parent_span_id",
        "name",
        "span_type",
        "framework",
        "start_time",
        "attributes",
        "input_preview",
        "_output_data",
    )

    def __init__(
        self,
        *,
        name: str,
        span_type: SpanType,
        framework: Framework | None,
        parent_span_id: str | None,
        attributes: dict[str, Any] | None = None,
        input_preview: str = "",
    ) -> None:
        config = get_config()
        self.span_id = uuid.uuid4().hex
        self.trace_id = config.trace_id
        self.parent_span_id = parent_span_id
        self.name = name
        self.span_type = span_type
        self.framework = framework or config.framework
        self.start_time = _utcnow()
        self.attributes = dict(attributes or {})
        self.input_preview = input_preview
        self._output_data: Any = None

    def set_output(self, output_data: Any) -> None:
        """Attach output to be sent when the span ends."""
        self._output_data = output_data

    def record_usage(
        self,
        *,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        model: str | None = None,
        cost_usd: float | None = None,
    ) -> None:
        from veritrix.usage import usage_attributes

        self.attributes.update(
            usage_attributes(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=model,
                cost_usd=cost_usd,
            )
        )


class Tracer:
    def __init__(self) -> None:
        self._span_stack: deque[ActiveSpan] = deque()
        self._lock = threading.Lock()

    def start_span(
        self,
        name: str,
        *,
        span_type: SpanType = "agent",
        framework: Framework | None = None,
        attributes: dict[str, Any] | None = None,
        input_data: Any = None,
    ) -> ActiveSpan:
        config = get_config()
        parent_span_id = self._span_stack[-1].span_id if self._span_stack else None
        merged_attributes = dict(attributes or {})
        for tag in config.default_tags:
            merged_attributes.setdefault("agentops.tag", tag)

        span = ActiveSpan(
            name=name,
            span_type=span_type,
            framework=framework,
            parent_span_id=parent_span_id,
            attributes=merged_attributes,
            input_preview=_preview(input_data),
        )
        with self._lock:
            self._span_stack.append(span)
        return span

    def end_span(
        self,
        span: ActiveSpan,
        *,
        status: SpanStatus = "ok",
        error_message: str | None = None,
        output_data: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> SpanSchema:
        config = get_config()
        end_time = _utcnow()
        merged_attributes = dict(span.attributes)
        if attributes:
            merged_attributes.update(attributes)

        merged_attributes.update(
            {
                "agentops.agent_id": config.agent_id,
                "agentops.agent_name": config.agent_name,
                "agentops.span_name": span.name,
                "agentops.run_id": config.run_id,
                "agentops.framework": span.framework,
                "agentops.span_type": span.span_type,
            }
        )

        duration_ms = max(int((end_time - span.start_time).total_seconds() * 1000), 0)
        merged_attributes["agentops.duration_ms"] = duration_ms

        resolved_output = output_data if output_data is not None else span._output_data

        finished = SpanSchema(
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            name=span.name,
            start_time=span.start_time,
            end_time=end_time,
            status=status,
            error_message=error_message,
            attributes=merged_attributes,
            input_preview=span.input_preview,
            output_preview=_preview(resolved_output),
        )

        with self._lock:
            if self._span_stack and self._span_stack[-1].span_id == span.span_id:
                self._span_stack.pop()
            else:
                self._span_stack = deque(s for s in self._span_stack if s.span_id != span.span_id)

        return finished

    def finish_all_open_spans(self, *, status: SpanStatus = "ok") -> list[SpanSchema]:
        finished: list[SpanSchema] = []
        with self._lock:
            open_spans = list(self._span_stack)
            self._span_stack.clear()
        for span in reversed(open_spans):
            finished.append(self.end_span(span, status=status))
        return finished


_tracer: Tracer | None = None
_tracer_lock = threading.Lock()


def get_tracer() -> Tracer:
    global _tracer
    with _tracer_lock:
        if _tracer is None:
            _tracer = Tracer()
        return _tracer


def reset_tracer() -> None:
    global _tracer
    with _tracer_lock:
        _tracer = None


def new_run_ids(config: VeritrixConfig) -> VeritrixConfig:
    run_id = uuid.uuid4().hex
    config.run_id = run_id
    config.trace_id = run_id
    config.agent_id = config.agent_id or uuid.uuid4().hex
    return config
