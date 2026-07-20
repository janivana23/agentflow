"""Planner: decomposes a goal into an ordered tool-call plan."""
from __future__ import annotations

import json

from ..core.agent import BaseAgent
from ..core.message import Message, MessageType, PlanStep, Role

SYSTEM = """You are a data-analysis planner. Given a goal and a tool catalog,
return a JSON array of steps: [{"tool": ..., "args": {...}, "rationale": ...}].
Only use tools from the catalog. Order matters."""


class PlannerAgent(BaseAgent):
    role = Role.PLANNER

    def handle(self, msg: Message) -> Message:
        goal = msg.content
        prompt = (
            f"Tool catalog:\n{self.tools.catalog()}\n\n"
            f"PLAN_REQUEST:{json.dumps(goal)}"
        )
        raw = self.llm.complete(SYSTEM, prompt)
        steps = [
            PlanStep(step_id=i, tool=s["tool"], args=s["args"], rationale=s["rationale"])
            for i, s in enumerate(json.loads(raw), start=1)
        ]
        # Guardrail: reject hallucinated tools before execution.
        unknown = [s.tool for s in steps if s.tool not in self.tools.names()]
        if unknown:
            return Message(self.role, Role.ORCHESTRATOR, MessageType.ERROR,
                           {"error": f"Planner produced unknown tools: {unknown}"})
        return Message(self.role, Role.ORCHESTRATOR, MessageType.RESULT,
                       {"plan": steps})
