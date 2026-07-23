# Veritrix Python SDK

Observability for multi-agent AI systems. Install in your agent project, call `veritrix.init()`, and traces flow to your Veritrix dashboard.

## Install

Until the package is on PyPI, install from GitHub:

```bash
pip install "git+https://github.com/veritrix-ai/veritrix-sdk.git"
```

Optional framework extras:

```bash
pip install "veritrix[langchain,crewai] @ git+https://github.com/veritrix-ai/veritrix-sdk.git"
```

After publish to PyPI:

```bash
pip install veritrix
# or
pip install veritrix[langchain,crewai]
```

## Examples

Colab notebooks live in [`examples/`](./examples/):

- [Getting Started](https://colab.research.google.com/github/veritrix-ai/veritrix-sdk/blob/master/examples/getting_started.ipynb)
- [Customer Support Agent](https://colab.research.google.com/github/veritrix-ai/veritrix-sdk/blob/master/examples/customer_support_agent.ipynb)

## Quick start

```python
import os
import veritrix

veritrix.init(
    api_key=os.getenv("VERITRIX_API_KEY"),
    default_tags=["crewai"],
)

# Your agent code runs here — LangChain and CrewAI are auto-instrumented when installed.

veritrix.end()
```

## Manual tracing

```python
with veritrix.trace("research-task", span_type="agent", input_data={"query": "..."}) as span:
    result = run_task()
```

## Environment variables

| Variable | Description |
|---|---|
| `VERITRIX_API_KEY` | Project API key from the Veritrix console (`AGENTOPS_API_KEY` still accepted) |
| `VERITRIX_ENDPOINT` | Ingest API base URL (default: `http://localhost:8001`; `AGENTOPS_ENDPOINT` still accepted) |

## Development

```bash
cd sdk
uv sync --extra dev
uv run pytest
```
