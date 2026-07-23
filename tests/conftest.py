from __future__ import annotations

from typing import Any

import pytest

from veritrix import end, init, trace
from veritrix.client import IngestClient, reset_client
from veritrix.config import get_config, reset_config
from veritrix.span import SpanSchema
from veritrix.tracer import get_tracer, reset_tracer


class RecordingTransport:
    def __init__(self) -> None:
        self.batches: list[list[SpanSchema]] = []
        self.failures_before_success = 0
        self.calls = 0
        self.should_fail = False

    def send_batch(self, spans: list[SpanSchema]) -> None:
        self.calls += 1
        if self.should_fail:
            raise ConnectionError("transport unavailable")
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise ConnectionError("temporary failure")
        self.batches.append(spans)


@pytest.fixture(autouse=True)
def reset_sdk_state() -> None:
    end()
    reset_config()
    reset_tracer()
    reset_client()
    yield
    end()
    reset_config()
    reset_tracer()
    reset_client()


@pytest.fixture
def transport() -> RecordingTransport:
    return RecordingTransport()


@pytest.fixture
def client(transport: RecordingTransport) -> IngestClient:
    reset_client()
    return IngestClient(transport=transport)
