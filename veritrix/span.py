from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SpanStatus = Literal["ok", "error"]
SpanType = Literal["agent", "tool", "llm", "delegation"]
Framework = Literal["langchain", "crewai", "manual"]


class SpanSchema(BaseModel):
    """OTel-compatible span sent to the ingest API."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    name: str
    start_time: datetime
    end_time: datetime | None = None
    status: SpanStatus = "ok"
    error_message: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    input_preview: str = ""
    output_preview: str = ""


class SpanBatch(BaseModel):
    spans: list[SpanSchema]


REQUIRED_ATTRIBUTES = (
    "agentops.agent_id",
    "agentops.agent_name",
    "agentops.run_id",
    "agentops.framework",
    "agentops.span_type",
)
