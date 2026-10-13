from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

PlanningRuntime = Literal["standard", "fast"]


class Summarization(TypedDict, total=False):
    instruction: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Usage:
    estimated: float
    consumed: float


@dataclass(frozen=True, slots=True, kw_only=True)
class Account:
    balance: float
    balance_timestamp: str


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanStep:
    id: str
    status: str
    tool_name: str
    parameters: dict[str, Any]
    reasoning: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Planning:
    status: str
    steps: list[PlanStep]
    reason: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchResult:
    id: str
    usage: Usage
    account: Account
    summary: str | None = None
    data: list[dict[str, Any]] | None = None
    planning: Planning | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Tool:
    id: str
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class ToolExecutionResult:
    tool_name: str
    output: Any
    is_error: bool
    usage: Usage
    error_message: str | None = None


def parse_usage(data: Any) -> Usage:
    return Usage(estimated=data["estimated"], consumed=data["consumed"])


def parse_account(data: Any) -> Account:
    return Account(balance=data["balance"], balance_timestamp=data["balance_timestamp"])


def parse_steps(data: Any) -> list[PlanStep]:
    return [
        PlanStep(
            id=step["id"],
            status=step["status"],
            tool_name=step["tool_name"],
            parameters=step["parameters"],
            reasoning=step.get("reasoning"),
        )
        for step in data
    ]


def parse_search_result(data: Any) -> SearchResult:
    planning = data.get("planning")
    return SearchResult(
        id=data["id"],
        usage=parse_usage(data["usage"]),
        account=parse_account(data["account"]),
        summary=data.get("summary"),
        data=data.get("raw_data"),
        planning=Planning(
            status=planning["status"],
            steps=parse_steps(planning["steps"]),
            reason=planning.get("reason"),
        )
        if planning
        else None,
    )


def parse_plan(data: Any) -> dict[str, Any]:
    return {
        "id": data["id"],
        "status": data["status"],
        "steps": parse_steps(data["steps"]),
        "usage": parse_usage(data["usage"]),
        "account": parse_account(data["account"]),
        "reason": data.get("reason"),
    }


def parse_tools(data: Any) -> list[Tool]:
    return [
        Tool(
            id=tool["id"],
            name=tool["name"],
            description=tool["description"],
            input_schema=tool.get("input_schema") or {},
            output_schema=tool.get("output_schema") or {},
        )
        for tool in data
    ]


def parse_tool_execution_result(data: Any) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool_name=data["tool_name"],
        output=data["output"],
        is_error=data["is_error"],
        usage=parse_usage(data["usage"]),
        error_message=data.get("error_message"),
    )
