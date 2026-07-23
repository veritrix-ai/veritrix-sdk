from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import httpx

from veritrix.client import HttpSpanTransport
from veritrix.span import SpanSchema


def _span() -> SpanSchema:
    now = datetime.now(tz=UTC)
    return SpanSchema(
        trace_id="trace",
        span_id="span",
        name="demo",
        start_time=now,
        end_time=now,
    )


def test_http_transport_posts_span_batch() -> None:
    transport = HttpSpanTransport("http://localhost:8001/v1/spans", "test-key")
    response = MagicMock()
    response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = response

    with patch("veritrix.client.httpx.Client", return_value=mock_client):
        transport.send_batch([_span()])

    mock_client.post.assert_called_once()
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_http_transport_raises_on_error() -> None:
    transport = HttpSpanTransport("http://localhost:8001/v1/spans", "test-key")
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error",
        request=MagicMock(),
        response=MagicMock(),
    )

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.post.return_value = response

    with patch("veritrix.client.httpx.Client", return_value=mock_client):
        try:
            transport.send_batch([_span()])
            raised = False
        except httpx.HTTPStatusError:
            raised = True

    assert raised
