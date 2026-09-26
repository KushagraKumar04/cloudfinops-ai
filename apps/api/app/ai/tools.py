import time
import uuid
from typing import Any, Callable

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class ToolContext:
    def __init__(self, db: Session, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id


class ToolResult(BaseModel):
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0


TOOLS: dict[str, dict[str, Any]] = {}


def register(name: str, description: str, args_model: type[BaseModel] | None = None):
    def decorator(fn: Callable):
        TOOLS[name] = {
            "name": name,
            "description": description,
            "args_model": args_model,
            "handler": fn,
        }
        return fn
    return decorator


def execute_tool(name: str, ctx: ToolContext, raw_args: dict[str, Any]) -> ToolResult:
    spec = TOOLS.get(name)
    if spec is None:
        return ToolResult(summary=f"Unknown tool: {name}")

    args_model = spec["args_model"]
    try:
        args = args_model(**raw_args) if args_model else None
    except Exception as exc:
        return ToolResult(summary=f"Invalid args for {name}: {exc}")

    start = time.perf_counter()
    try:
        if args is None:
            result = spec["handler"](ctx)
        else:
            result = spec["handler"](ctx, **args.model_dump())
    except Exception as exc:
        return ToolResult(summary=f"Tool {name} failed: {exc}", duration_ms=int((time.perf_counter() - start) * 1000))

    result.duration_ms = int((time.perf_counter() - start) * 1000)
    return result


def tool_catalog() -> list[dict[str, str]]:
    return [{"name": spec["name"], "description": spec["description"]} for spec in TOOLS.values()]


from app.ai import tools_impl  # noqa: E402, F401