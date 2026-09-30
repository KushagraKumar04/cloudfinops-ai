from typing import Any

from app.ai.tools import TOOLS


def tool_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for name, entry in TOOLS.items():
        args_model = entry.get("args_model")
        if args_model is None:
            schema: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}
        else:
            schema = args_model.model_json_schema()
            schema.pop("title", None)
        specs.append(
            {
                "name": name,
                "description": entry["description"],
                "parameters": schema,
            }
        )
    return specs