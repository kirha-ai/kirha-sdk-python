# Search API

Full access to the KIRHA Search API with search, planning, and tool execution.

## Configuration

```python
from kirha import Kirha

kirha = Kirha(api_key="your-api-key", summarization=True)
```

### Constructor Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `api_key` | `str` | No | Your KIRHA API key. Defaults to the `KIRHA_API_KEY` environment variable |
| `focus` | `str` | No | Default focus for all requests. Vertical slug to focus on (`crypto`, `insurance`, `company`, ...). Omit it to search every vertical |
| `summarization` | `bool \| Summarization` | No | Default summarization config |
| `timeout` | `float` | No | Request timeout in seconds, `120` by default |

`AsyncKirha` takes the same parameters. Its methods are coroutines, and its `plan()` returns an `AsyncPlan` whose `execute()` you await.

Both clients keep a connection pool open. Close them with `close()`, or use them as context managers:

```python
with Kirha() as kirha:
    result = kirha.search("What does the boxed warning on Ozempic say?")
```

### Summarization

```python
class Summarization(TypedDict, total=False):
    instruction: str
```

Pass `summarization=True` to add a summary, or a `Summarization` dict to shape it with an instruction: a format, a language, the fields to keep. Methods also accept `False` to turn off a default set in the constructor.

---

## Methods

### `search(query, ...)`

Execute a search query with optional summarization.

```python
result = kirha.search(
    "List top 10 stablecoins yield on Ethereum",
    focus="crypto",
    summarization={"instruction": "Be concise"},
    include_data=True,
    include_planning=True,
)

print(result.summary)
print(result.usage.consumed)
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | Yes | The search query |

#### Keyword arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `focus` | `str` | Constructor default | Vertical slug to focus on (`crypto`, `insurance`, `company`, ...). Omit it to search every vertical |
| `summarization` | `bool \| Summarization` | Constructor default | Summarization config or `False` to disable |
| `include_data` | `bool` | `True` | Include provider data |
| `include_planning` | `bool` | `False` | Include execution plan details |
| `planning_runtime` | `"standard" \| "fast"` | `"standard"` | `"standard"` is more accurate, `"fast"` answers sooner but is less accurate |

#### Returns: `SearchResult`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Search identifier |
| `summary` | `str \| None` | AI-generated summary |
| `data` | `list[dict] \| None` | Data from providers, one entry per tool call with `step_id`, `tool_name`, `parameters` and `output` |
| `planning` | `Planning \| None` | Execution plan details: `status`, `steps`, `reason` |
| `usage` | `Usage` | API usage for this request: `estimated`, `consumed` |
| `account` | `Account` | Account balance info: `balance`, `balance_timestamp` |

---

### `plan(query, ...)`

Generate an execution plan without executing it. Plans are valid for 5 minutes.

```python
plan = kirha.plan(
    "Summarize latest NVIDIA earning calls",
    summarization=True,
    planning_runtime="fast",
)

print(plan.id)
print(plan.status)
print(plan.steps)
print(plan.usage)
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | `str` | Yes | The search query |

#### Keyword arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `focus` | `str` | Constructor default | Vertical slug to focus on (`crypto`, `insurance`, `company`, ...). Omit it to search every vertical |
| `summarization` | `bool \| Summarization` | Constructor default | Summarization for execution |
| `planning_runtime` | `"standard" \| "fast"` | `"standard"` | `"standard"` is more accurate, `"fast"` answers sooner but is less accurate |

#### Returns: `Plan`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique plan identifier |
| `query` | `str` | Original query |
| `focus` | `str \| None` | Focus used |
| `status` | `str` | `pending_confirmation`, `clarification` or `no_plan` |
| `steps` | `list[PlanStep]` | Planned execution steps |
| `reason` | `str \| None` | Reasoning for the plan |
| `usage` | `Usage` | API usage for planning |
| `account` | `Account` | Account balance info |

#### PlanStep

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Step identifier |
| `status` | `str` | `pending`, `executing`, `done`, `failed`, `skipped` or `timeout` |
| `tool_name` | `str` | Tool to execute |
| `parameters` | `dict[str, Any]` | Tool parameters. A step can take its input from an earlier step's output (`$fromStep`) |
| `reasoning` | `str \| None` | Why this step is needed |

---

### `plan.execute(...)`

Execute a previously created plan.

```python
result = plan.execute(
    summarization={"instruction": "Answer in French"},
    include_data=True,
    include_planning=True,
)
```

#### Keyword arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `summarization` | `bool \| Summarization` | Plan default | Override summarization |
| `include_data` | `bool` | `True` | Include provider data |
| `include_planning` | `bool` | `False` | Include execution plan details |

#### Returns: `SearchResult`

Raises `PlanExpiredError` if the plan is older than 5 minutes.

---

### `execute_plan(plan_id, ...)`

Execute a plan from its id, for example after an approval step that runs in another process.

```python
result = kirha.execute_plan("search_xUVm7HF80ZLjy0varLYGr")
```

Takes the same keyword arguments as `plan.execute()`, with `summarization` defaulting to the constructor value. Returns a `SearchResult` and raises `PlanExpiredError` the same way.

---

### `tools(...)`

List the tools of the catalogue.

```python
tools = kirha.tools(focus="crypto")

for tool in tools:
    print(tool.name, tool.description)
```

#### Keyword arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `focus` | `str` | Constructor value | Vertical slug (`crypto`, `insurance`, `company`, ...), empty for the whole catalogue |
| `provider` | `str` | All providers | Provider slug (`coingecko`, `defillama`, ...) |
| `page` | `int` | — | Page number, from 1 to 1000 |
| `limit` | `int` | `20` when `page` is sent | Tools per page, from 1 to 100 |

Without `page` and `limit`, the whole list comes back in one call.

#### Returns: `list[Tool]`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Tool identifier |
| `name` | `str` | Tool name |
| `description` | `str` | Tool description |
| `provider` | `str` | Provider slug |
| `credits_per_call` | `int` | Credits spent per call, `0` when free |
| `input_schema` | `dict[str, Any]` | JSON Schema of the tool input |
| `output_schema` | `dict[str, Any]` | JSON Schema of the tool output |
| `related` | `bool` | `True` when `match()` surfaced the tool through relation expansion |
| `related_to` | `list[str]` | Names of the ranked tools that brought it in |
| `related_tools` | `list[str]` | Other tools of the same provider, filled by `get()` only |

---

### `tools_page(...)`

Same arguments and same tools as `tools()`, plus the pagination window.

```python
page = kirha.tools_page(focus="crypto", page=3)

print(page.total, page.limit, page.skip)
```

#### Returns: `ToolPage`

| Field | Type | Description |
|-------|------|-------------|
| `tools` | `list[Tool]` | The tools of this window |
| `total` | `int` | Tools matching the filter, all pages together |
| `limit` | `int` | Window size actually applied |
| `skip` | `int` | Tools skipped before this window |

---

### `match(query, *, focus=None, limit=None)`

Rank the catalogue against an intent written in plain language.

```python
for tool in kirha.match("what is the price of a coin", focus="crypto"):
    print(tool.name, tool.related, tool.related_to)
```

#### Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `query` | `str` | Required | The intent, in plain language |
| `focus` | `str` | Constructor value | Vertical slug, empty for the whole catalogue |
| `limit` | `int` | `10` | Tools to return, from 1 to 50 |

#### Returns: `list[Tool]`

Ranked tools first, then the tools that relation expansion brought in — those carry `related=True` and `related_to`, the names of the ranked tools that pulled them in. A catalogue with no ranking returns an empty list.

---

### `get(tool_name)`

Read one tool by name.

```python
tool = kirha.get("coingecko_searchCoin")

print(tool.credits_per_call, tool.related_tools)
```

#### Returns: `Tool`

`related_tools` holds the names of the other tools of the same provider. An unknown name, or a name without its provider prefix, raises `ApiError` with status 404.

---

### `execute_tool(tool_name, input=None)`

Execute a specific tool directly.

```python
result = kirha.execute_tool("coingecko_searchCoin", {"query": "avax", "limit": 1})

if not result.is_error:
    print(result.output)
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_name` | `str` | Yes | Name of the tool to execute |
| `input` | `dict[str, Any]` | No | Input matching the tool's input schema, `{}` by default |

#### Returns: `ToolExecutionResult`

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Executed tool name |
| `output` | `Any` | Tool output |
| `is_error` | `bool` | Whether execution failed |
| `error_message` | `str \| None` | Error message if failed |
| `usage` | `Usage` | API usage |
