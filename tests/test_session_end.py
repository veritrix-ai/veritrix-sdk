from __future__ import annotations

import veritrix
from veritrix.client import IngestClient, reset_client


def test_end_flushes_root_session_span(transport, monkeypatch) -> None:
    monkeypatch.setenv("AGENTOPS_API_KEY", "test-key")
    veritrix.init(api_key="test-key", framework="manual")

    reset_client()
    import veritrix.client as client_module

    client_module._client = IngestClient(transport=transport)

    veritrix.end()

    assert transport.batches
    assert any(span.name == "session" for batch in transport.batches for span in batch)
