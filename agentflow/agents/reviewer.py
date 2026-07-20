"""Reviewer: independent quality gate over the Analyst's output."""
from __future__ import annotations

import json
from pathlib import Path

from ..core.agent import BaseAgent
from ..core.message import Message, MessageType, Role
from ..toolkit.data_tools import ctx

SYSTEM = """You are a QA reviewer for data analysis pipelines. Given execution
evidence, return JSON {"verdict": "approve"|"revise", "issues": [...]}."""


class ReviewerAgent(BaseAgent):
    role = Role.REVIEWER

    def handle(self, msg: Message) -> Message:
        evidence = {
            "rows_after_clean": 0 if ctx.df is None else len(ctx.df),
            "chart_exists": Path(ctx.artifacts.get("chart", "")).exists(),
            "report_exists": Path(ctx.artifacts.get("report", "")).exists(),
            "n_findings": len(ctx.findings),
            "trace_summary": [
                {"tool": t["tool"], "status": t["status"]}
                for t in msg.content["trace"]
            ],
        }
        raw = self.llm.complete(SYSTEM, f"REVIEW_REQUEST:{json.dumps(evidence)}")
        verdict = json.loads(raw)
        return Message(self.role, Role.ORCHESTRATOR, MessageType.REVIEW,
                       {"verdict": verdict["verdict"], "issues": verdict["issues"],
                        "evidence": evidence})
