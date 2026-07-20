"""Orchestrator: owns the workflow — plan -> execute -> review -> (replan)."""
from __future__ import annotations

from ..core.agent import BaseAgent
from ..core.llm import LLMBackend
from ..core.message import Message, MessageType, Role
from ..core.tools import ToolRegistry
from .analyst import AnalystAgent
from .planner import PlannerAgent
from .reporter import ReporterAgent
from .reviewer import ReviewerAgent


class Orchestrator(BaseAgent):
    role = Role.ORCHESTRATOR
    MAX_ITERATIONS = 2   # bounded replanning loop — never spins forever

    def __init__(self, llm: LLMBackend, tools: ToolRegistry) -> None:
        super().__init__(llm, tools)
        self.planner = PlannerAgent(llm, tools)
        self.analyst = AnalystAgent(llm, tools)
        self.reviewer = ReviewerAgent(llm, tools)
        self.reporter = ReporterAgent(llm, tools)

    def run(self, goal: dict) -> dict:
        """Public entry point: takes a goal, returns a final result dict."""
        task = Message(self.role, Role.PLANNER, MessageType.TASK, goal)
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            plan_msg = self.planner.receive(task)
            if plan_msg.type is MessageType.ERROR:
                return {"status": "failed", "stage": "planning",
                        "detail": plan_msg.content}

            exec_msg = self.analyst.receive(
                Message(self.role, Role.ANALYST, MessageType.TASK, plan_msg.content))
            if exec_msg.type is MessageType.ERROR:
                return {"status": "failed", "stage": "execution",
                        "detail": exec_msg.content}

            review_msg = self.reviewer.receive(
                Message(self.role, Role.REVIEWER, MessageType.TASK, exec_msg.content))

            if review_msg.content["verdict"] == "approve":
                report_msg = self.reporter.receive(
                    Message(self.role, Role.REPORTER, MessageType.TASK,
                            {"goal": goal.get("goal", ""),
                             "trace": exec_msg.content["trace"]}))
                return {"status": "success", "iterations": iteration,
                        "summary": report_msg.content["summary"],
                        "review": review_msg.content,
                        "trace": exec_msg.content["trace"]}

            # Feed reviewer issues back into the next planning round.
            task = Message(self.role, Role.PLANNER, MessageType.TASK,
                           {**goal, "revision_notes": review_msg.content["issues"]})

        return {"status": "failed", "stage": "review",
                "detail": "Max iterations reached without approval."}

    def handle(self, msg: Message) -> Message:  # satisfies BaseAgent ABC
        result = self.run(msg.content)
        return Message(self.role, self.role, MessageType.RESULT, result)
