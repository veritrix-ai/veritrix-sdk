# Veritrix examples

Colab / GitHub notebooks for onboarding and demos.

## Notebooks

| Notebook | Description |
|---|---|
| [`getting_started.ipynb`](./getting_started.ipynb) | Minimal manual trace — install SDK, send a sample run |
| [`customer_support_agent.ipynb`](./customer_support_agent.ipynb) | Airline multi-agent demo (OpenAI Agents SDK) with tools + handoffs |

## Open in Google Colab

- [Getting Started](https://colab.research.google.com/github/veritrix-ai/veritrix-sdk/blob/master/examples/getting_started.ipynb)
- [Customer Support Agent](https://colab.research.google.com/github/veritrix-ai/veritrix-sdk/blob/master/examples/customer_support_agent.ipynb)

## How Colab installs the SDK

```python
!pip install -q "git+https://github.com/veritrix-ai/veritrix-sdk.git"
```

After PyPI publish:

```python
!pip install -q veritrix
```

The customer-support notebook also installs `openai-agents`.

## Keys

| Variable | Required for | Notes |
|---|---|---|
| `VERITRIX_API_KEY` | Both notebooks | From Veritrix → Settings → API Keys |
| `VERITRIX_ENDPOINT` | Both notebooks | Default `https://veritrix-ingest.onrender.com` |
| `OPENAI_API_KEY` | Customer support only | Needed for real LLM turns |
