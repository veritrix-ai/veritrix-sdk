from __future__ import annotations

import atexit
import threading
from typing import Protocol

import httpx

from veritrix.buffer import MAX_BATCH_SIZE, SpanBuffer, sleep_backoff
from veritrix.config import get_config
from veritrix.span import SpanBatch, SpanSchema


class SpanTransport(Protocol):
    def send_batch(self, spans: list[SpanSchema]) -> None: ...


class HttpSpanTransport:
    def __init__(self, endpoint: str, api_key: str, timeout: float = 10.0) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout = timeout

    def send_batch(self, spans: list[SpanSchema]) -> None:
        payload = SpanBatch(spans=spans).model_dump(mode="json")
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                self._endpoint,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()


class IngestClient:
    """Sends span batches to the ingest API with fail-open buffering."""

    def __init__(self, transport: SpanTransport | None = None) -> None:
        self._buffer = SpanBuffer()
        self._transport = transport
        self._flush_lock = threading.Lock()
        self._worker = threading.Thread(target=self._flush_loop, daemon=True)
        self._stop_event = threading.Event()
        self._worker.start()
        atexit.register(self.flush)

    def _get_transport(self) -> SpanTransport:
        if self._transport is None:
            config = get_config()
            self._transport = HttpSpanTransport(config.endpoint, config.api_key)
        return self._transport

    def enqueue(self, span: SpanSchema) -> None:
        try:
            self._buffer.append(span)
            self._trigger_flush()
        except Exception:
            pass

    def enqueue_many(self, spans: list[SpanSchema]) -> None:
        try:
            self._buffer.extend(spans)
            self._trigger_flush()
        except Exception:
            pass

    def _trigger_flush(self) -> None:
        if self._flush_lock.acquire(blocking=False):
            try:
                self._flush_once()
            finally:
                self._flush_lock.release()

    def _flush_loop(self) -> None:
        while not self._stop_event.wait(2.0):
            try:
                with self._flush_lock:
                    self._flush_once()
            except Exception:
                pass

    def _flush_once(self) -> None:
        batch = self._buffer.drain(MAX_BATCH_SIZE)
        if not batch:
            return
        self._send_with_retry(batch)

    def _send_with_retry(self, batch: list[SpanSchema]) -> bool:
        for attempt in range(5):
            try:
                self._get_transport().send_batch(batch)
                return True
            except Exception:
                if attempt == 4:
                    return False
                sleep_backoff(attempt)
        return False

    def flush(self) -> None:
        try:
            with self._flush_lock:
                while len(self._buffer) > 0:
                    before = len(self._buffer)
                    self._flush_once()
                    if len(self._buffer) >= before:
                        break
        except Exception:
            pass

    def shutdown(self) -> None:
        self._stop_event.set()
        self.flush()


_client: IngestClient | None = None
_client_lock = threading.Lock()


def get_client() -> IngestClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = IngestClient()
        return _client


def reset_client() -> None:
    global _client
    with _client_lock:
        if _client is not None:
            _client.shutdown()
        _client = None
