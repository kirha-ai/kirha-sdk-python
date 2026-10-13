<p align="center">
  <img src="https://raw.githubusercontent.com/kirha-ai/kirha-sdk-python/main/assets/banner.png" alt="KIRHA SDK" />
</p>

<p align="center">
  <a href="https://pypi.org/project/kirha/"><img src="https://img.shields.io/pypi/v/kirha" alt="PyPI version" /></a>
  <a href="https://github.com/kirha-ai/kirha-sdk-python/actions/workflows/ci.yml"><img src="https://github.com/kirha-ai/kirha-sdk-python/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://pypi.org/project/kirha/"><img src="https://img.shields.io/pypi/pyversions/kirha" alt="Python versions" /></a>
</p>

<p align="center">
  <a href="https://kirha.com"><b>🦋 KIRHA</b></a> •
  <a href="https://docs.kirha.com"><b>📚 Documentation</b></a> •
  <a href="https://app.kirha.com/auth/register"><b>🔑 Get an API key</b></a>
</p>

# KIRHA SDK

Python SDK for the KIRHA Search and Tools APIs.

## Installation

```bash
pip install kirha
# or
uv add kirha
# or
poetry add kirha
```

Requires Python 3.10 or later.

## Quick Start

```python
from kirha import Kirha

kirha = Kirha()

result = kirha.search("What does the boxed warning on Ozempic say?")

print(result.data)
```

`Kirha()` reads your API key from the `KIRHA_API_KEY` environment variable. Pass `api_key="..."` to set it in code.

## Examples

### Summarization

```python
kirha = Kirha(api_key="your-api-key")

result = kirha.search("Summarize latest NVIDIA earning calls", summarization=True)

print(result.summary)
```

### Summarization with instruction

```python
kirha = Kirha(api_key="your-api-key")

result = kirha.search(
    "List top 10 stablecoins yield on Ethereum",
    summarization={
        "instruction": "Format the response as a table with columns: Stablecoin, Protocol, APY",
    },
)

print(result.summary)
```

### Plan mode

Review the steps and the estimated cost before running the query, yourself or with an agent. Planning charges nothing until the plan runs.

```python
kirha = Kirha(api_key="your-api-key")

plan = kirha.plan(
    "Find engineers working at companies behind the latest patents in Machine Learning",
)

print(plan.steps)
print(plan.usage)

result = plan.execute()
print(result.data)
```

A plan expires 5 minutes after it is created. To run it from another process, after an approval step for example, call `kirha.execute_plan(plan_id)`.

### Direct tool calling

```python
tools = kirha.tools(focus="crypto")
print([tool.name for tool in tools])

result = kirha.execute_tool("coingecko_searchCoin", {"query": "avax", "limit": 1})
print(result.output)
```

### Async

```python
import asyncio

from kirha import AsyncKirha


async def main() -> None:
    async with AsyncKirha() as kirha:
        result = await kirha.search("What does the boxed warning on Ozempic say?")
        print(result.data)


asyncio.run(main())
```

`AsyncKirha` has the same methods as `Kirha`, as coroutines. Both clients keep a connection pool open, so close them with `close()` or use them as context managers.

## Documentation

- [Search API](https://github.com/kirha-ai/kirha-sdk-python/blob/main/docs/search-api.md) - Full API reference
- [Examples](https://github.com/kirha-ai/kirha-sdk-python/tree/main/examples) - Runnable scripts

## Errors

| Error | Description |
|-------|-------------|
| `KirhaError` | Base error class |
| `ConfigurationError` | No API key passed and `KIRHA_API_KEY` not set |
| `ApiError` | API returned an error, with `status_code`, `code` and `details` |
| `AuthenticationError` | Invalid or missing API key (401) |
| `RateLimitError` | Rate limit exceeded (429), with `retry_after` in seconds |
| `PlanExpiredError` | Plan expired (5 minute limit) |
| `NetworkError` | Network/connection failure or timeout |

`AuthenticationError` and `RateLimitError` extend `ApiError`.

## Development

```bash
uv sync
uv run pytest
```

`uv run pytest -m integration` runs the tests against the live API with your `KIRHA_API_KEY`. They spend credits.

### Releasing

1. Bump `version` in `pyproject.toml` (for example `uv version 0.2.0`) and merge it to `main`.
2. Create a GitHub release with a tag matching that version, prefixed with `v` (for example `v0.2.0`).

Publishing the release runs the [publish workflow](https://github.com/kirha-ai/kirha-sdk-python/actions/workflows/publish.yml), which checks that the tag matches the package version, runs the tests, builds the package and uploads it to [PyPI](https://pypi.org/project/kirha/) through trusted publishing. No PyPI token is stored in the repository.

## License

MIT
