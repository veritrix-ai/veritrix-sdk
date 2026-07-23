from __future__ import annotations

from typing import Any
from uuid import UUID

from veritrix.client import get_client
from veritrix.config import get_config
from veritrix.tracer import get_tracer

_handler: Any | None = None
_patched = False


def setup_langchain() -> None:
    global _handler, _patched
    if _patched:
        return

    try:
        from langchain_core.callbacks.base import BaseCallbackHandler
        from langchain_core.callbacks.manager import CallbackManager
    except Exception:
        return

    class VeritrixCallbackHandler(BaseCallbackHandler):
        def __init__(self) -> None:
            super().__init__()
            self._run_spans: dict[UUID, Any] = {}

        def _start(
            self,
            run_id: UUID,
            name: str,
            *,
            span_type: str,
            input_data: Any = None,
        ) -> None:
            tracer = get_tracer()
            span = tracer.start_span(
                name,
                span_type=span_type,  # type: ignore[arg-type]
                framework="langchain",
                input_data=input_data,
            )
            self._run_spans[run_id] = span

        def _finish(
            self,
            run_id: UUID,
            *,
            status: str = "ok",
            error_message: str | None = None,
            output_data: Any = None,
        ) -> None:
            span = self._run_spans.pop(run_id, None)
            if span is None:
                return
            finished = get_tracer().end_span(
                span,
                status=status,  # type: ignore[arg-type]
                error_message=error_message,
                output_data=output_data,
            )
            get_client().enqueue(finished)

        def on_chain_start(
            self,
            serialized: dict[str, Any] | None,
            inputs: dict[str, Any],
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            name = (serialized or {}).get("name") or (serialized or {}).get("id") or "chain"
            self._start(run_id, str(name), span_type="agent", input_data=inputs)

        def on_chain_end(
            self,
            outputs: dict[str, Any],
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            self._finish(run_id, output_data=outputs)

        def on_chain_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            self._finish(run_id, status="error", error_message=str(error))

        def on_tool_start(
            self,
            serialized: dict[str, Any] | None,
            input_str: str,
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            name = (serialized or {}).get("name") or "tool"
            self._start(run_id, str(name), span_type="tool", input_data=input_str)

        def on_tool_end(
            self,
            output: str,
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            self._finish(run_id, output_data=output)

        def on_tool_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            self._finish(run_id, status="error", error_message=str(error))

        def on_llm_start(
            self,
            serialized: dict[str, Any] | None,
            prompts: list[str],
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            name = (serialized or {}).get("name") or "llm"
            self._start(run_id, str(name), span_type="llm", input_data=prompts)

        def on_llm_end(
            self,
            response: Any,
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            span = self._run_spans.get(run_id)
            if span is not None:
                from veritrix.usage import extract_llm_usage

                span.attributes.update(extract_llm_usage(response))
            self._finish(run_id, output_data=_llm_response_preview(response))

        def on_llm_error(
            self,
            error: BaseException,
            *,
            run_id: UUID,
            **kwargs: Any,
        ) -> None:
            self._finish(run_id, status="error", error_message=str(error))

    original_configure = CallbackManager.configure

    def patched_configure(
        cls: type[CallbackManager],
        inheritable_callbacks: Any = None,
        local_callbacks: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> CallbackManager:
        handler = get_handler()
        if handler is not None:
            if local_callbacks is None:
                local_callbacks = [handler]
            elif isinstance(local_callbacks, list):
                if handler not in local_callbacks:
                    local_callbacks = [*local_callbacks, handler]
            else:
                local_callbacks = [local_callbacks, handler]
        return original_configure(
            inheritable_callbacks,
            local_callbacks,
            *args,
            **kwargs,
        )

    def get_handler() -> VeritrixCallbackHandler | None:
        try:
            get_config()
        except RuntimeError:
            return None
        global _handler
        if _handler is None:
            _handler = VeritrixCallbackHandler()
        return _handler

    CallbackManager.configure = classmethod(patched_configure)  # type: ignore[assignment]
    _patched = True


def _llm_response_preview(response: Any) -> Any:
    if hasattr(response, "generations"):
        try:
            return [
                [generation.text for generation in generation_list]
                for generation_list in response.generations
            ]
        except Exception:
            return str(response)
    return response


def get_langchain_handler() -> Any | None:
    try:
        from veritrix.integrations.langchain import _handler as handler

        return handler
    except Exception:
        return None
