from __future__ import annotations

import threading
import time
from collections import deque

from veritrix.span import SpanSchema

MAX_BUFFER_SIZE = 1000
MAX_BATCH_SIZE = 500
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 0.5


class SpanBuffer:
    """In-memory fail-open buffer with bounded size."""

    def __init__(self, max_size: int = MAX_BUFFER_SIZE) -> None:
        self._max_size = max_size
        self._spans: deque[SpanSchema] = deque()
        self._lock = threading.Lock()

    def append(self, span: SpanSchema) -> None:
        with self._lock:
            if len(self._spans) >= self._max_size:
                self._spans.popleft()
            self._spans.append(span)

    def extend(self, spans: list[SpanSchema]) -> None:
        for span in spans:
            self.append(span)

    def drain(self, limit: int = MAX_BATCH_SIZE) -> list[SpanSchema]:
        with self._lock:
            batch: list[SpanSchema] = []
            while self._spans and len(batch) < limit:
                batch.append(self._spans.popleft())
            return batch

    def requeue_front(self, spans: list[SpanSchema]) -> None:
        with self._lock:
            for span in reversed(spans):
                if len(self._spans) >= self._max_size:
                    self._spans.popleft()
                self._spans.appendleft(span)

    def __len__(self) -> int:
        with self._lock:
            return len(self._spans)


def compute_backoff(attempt: int) -> float:
    return min(BASE_BACKOFF_SECONDS * (2**attempt), 30.0)


def sleep_backoff(attempt: int) -> None:
    time.sleep(compute_backoff(attempt))
