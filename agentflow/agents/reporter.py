"""Reporter: turns approved analysis results into an executive summary.

Runs only AFTER the Reviewer approves — communication is downstream of
quality control. Demonstrates how new roles plug into the framework:
subclass BaseAgent, implement handle(), wire into the Orchestrator.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.agent import BaseAgent
from ..core.message import Message, MessageType, Role
from ..toolkit.data_tools import ctx

SYSTEM = """You are a business analyst. Given findings from a data analysis,
write a crisp 3-4 sentence executive summary for a non-technical audience."""


class ReporterAgent(BaseAgent):
    role = Role.REPORTER

    def handle(self, msg: Message) -> Message:
        payload = {
            "goal": msg.content.get("goal", "the dataset"),
            "findings": ctx.findings,
            "n_steps": len(msg.content.get("trace", [])),
        }
        summary = self.llm.complete(SYSTEM, f"SUMMARY_REQUEST:{json.dumps(payload)}")

        # Prepend the summary to the markdown report.
        report_path = Path(ctx.artifacts.get("report", ""))
        if report_path.exists():
            body = report_path.read_text()
            report_path.write_text(
                body.replace("# Analysis Report",
                             f"# Analysis Report\n\n> {summary}", 1))

        return Message(self.role, Role.ORCHESTRATOR, MessageType.RESULT,
                       {"summary": summary})
