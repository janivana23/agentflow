"""Tool registry.

Tools are plain Python functions registered with the @tool decorator.
The registry exposes JSON-schema-like specs so an LLM planner can discover
what actions are available — the same pattern used by function-calling APIs.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, str]   # param name -> description
    fn: Callable

    def to_prompt(self) -> str:
        params = ", ".join(f"{k}: {v}" for k, v in self.parameters.items())
        return f"- {self.name}({params}): {self.description}"


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, description: str, parameters: dict[str, str] | None = None):
        """Decorator: @registry.register("desc", {"path": "csv path"})"""
        def wrapper(fn: Callable) -> Callable:
            params = parameters or {
                p: "" for p in inspect.signature(fn).parameters
            }
            self._tools[fn.__name__] = ToolSpec(
                name=fn.__name__,
                description=description,
                parameters=params,
                fn=fn,
            )
            return fn
        return wrapper

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}. Available: {list(self._tools)}")
        return self._tools[name]

    def call(self, name: str, **kwargs: Any) -> Any:
        return self.get(name).fn(**kwargs)

    def catalog(self) -> str:
        """Human/LLM-readable list of available tools."""
        return "\n".join(t.to_prompt() for t in self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools)


# Global default registry used by the toolkit modules.
registry = ToolRegistry()
