"""Analyst: executes a plan step-by-step against the tool registry."""
from __future__ import annotations

from ..core.agent import BaseAgent
from ..core.message import Message, MessageType, Role


class AnalystAgent(BaseAgent):
    role = Role.ANALYST

    MAX_RETRIES = 1  # simple per-step retry budget

    def handle(self, msg: Message) -> Message:
        plan = msg.content["plan"]
        trace = []
        for step in plan:
            attempts = 0
            while True:
                try:
                    step.result = self.tools.call(step.tool, **step.args)
                    step.status = "done"
                    trace.append({"step": step.step_id, "tool": step.tool,
                                  "status": "done", "result": step.result})
                    break
                except Exception as exc:
                    attempts += 1
                    if attempts > self.MAX_RETRIES:
                        step.status = "failed"
                        trace.append({"step": step.step_id, "tool": step.tool,
                                      "status": "failed", "error": str(exc)})
                        return Message(self.role, Role.ORCHESTRATOR, MessageType.ERROR,
                                       {"trace": trace, "failed_step": step.step_id,
                                        "error": str(exc)})
        return Message(self.role, Role.ORCHESTRATOR, MessageType.RESULT,
                       {"trace": trace, "plan": plan})
