# Veritrix Python SDK

Observability for multi-agent AI systems. Install in your agent project, call `veritrix.init()`, and traces flow to your Veritrix dashboard.

## Install

Until the package is on PyPI, install from GitHub:

```bash
pip install "git+https://github.com/AgentOps-AI/agentops.git#subdirectory=sdk"
```

Optional framework extras:

```bash
pip install "git+https://github.com/AgentOps-AI/agentops.git#subdirectory=sdk[langchain,crewai]"
```

After publish to PyPI:

```bash
pip install veritrix
# or
pip install veritrix[langchain,crewai]
```

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
