"""Pluggable LLM backend.

Two implementations:

* AnthropicBackend — real LLM planning via the Claude API (used when
  ANTHROPIC_API_KEY is set).
* HeuristicBackend — deterministic rule-based planner so the whole system
  runs offline (demos, CI, unit tests). Swapping backends requires zero
  changes to any agent: they only depend on the LLMBackend interface.

This separation is a core engineering decision: agent logic is testable
without network access or API cost, and the demo is reproducible.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod


def extract_json(text: str) -> str:
    """Best-effort extraction of a JSON payload from an LLM response.

    Real models often wrap JSON in markdown fences or add commentary.
    This strips fences and surrounding prose so json.loads() is reliable —
    a robustness layer every LLM-integrated system needs.
    """
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        text = text.removeprefix("json").strip()
    starts = [i for i in (text.find("["), text.find("{")) if i != -1]
    if starts:
        start = min(starts)
        end = max(text.rfind("]"), text.rfind("}")) + 1
        if end > start:
            text = text[start:end]
    return text.strip()


class LLMBackend(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str) -> str:
        """Return the model's raw text response."""


class AnthropicBackend(LLMBackend):
    def __init__(self, model: str = "claude-sonnet-5") -> None:
        import anthropic  # lazy import; only needed when actually used
        self.client = anthropic.Anthropic()
        self.model = model

    def complete(self, system: str, prompt: str) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        # Responses may contain thinking blocks before the text block —
        # extract only text content rather than assuming content[0].
        return "".join(
            block.text for block in resp.content
            if getattr(block, "type", None) == "text"
        )


class HeuristicBackend(LLMBackend):
    """Deterministic planner for offline runs.

    Recognises the standard analysis goal and emits the same JSON plan
    format an LLM would produce, so downstream parsing is identical.
    """

    def complete(self, system: str, prompt: str) -> str:
        if "PLAN_REQUEST" in prompt:
            payload = json.loads(prompt.split("PLAN_REQUEST:", 1)[1])
            path = payload["dataset"]
            plan = [
                {"tool": "load_csv", "args": {"path": path},
                 "rationale": "Load the raw dataset into memory."},
                {"tool": "profile_data", "args": {},
                 "rationale": "Understand schema, nulls, and dtypes before touching anything."},
                {"tool": "clean_data", "args": {},
                 "rationale": "Drop duplicates, fix dtypes, handle missing values."},
                {"tool": "detect_outliers", "args": {"column": payload.get("metric", "")},
                 "rationale": "Flag anomalous values before aggregating."},
                {"tool": "aggregate", "args": {"group_by": payload.get("group_by", ""),
                                               "metric": payload.get("metric", "")},
                 "rationale": "Compute the summary the user asked for."},
                {"tool": "make_chart", "args": {"kind": "bar"},
                 "rationale": "Visualise the aggregated result."},
                {"tool": "write_report", "args": {},
                 "rationale": "Assemble findings into a markdown report."},
            ]
            return json.dumps(plan)
        if "REVIEW_REQUEST" in prompt:
            payload = json.loads(prompt.split("REVIEW_REQUEST:", 1)[1])
            issues = []
            if payload.get("rows_after_clean", 1) == 0:
                issues.append("Cleaning removed all rows — plan is invalid.")
            if not payload.get("chart_exists"):
                issues.append("Chart file was not produced.")
            verdict = "approve" if not issues else "revise"
            return json.dumps({"verdict": verdict, "issues": issues})
        if "SUMMARY_REQUEST" in prompt:
            payload = json.loads(prompt.split("SUMMARY_REQUEST:", 1)[1])
            findings = payload.get("findings", [])
            body = " ".join(findings) if findings else "No findings recorded."
            return (
                f"Executive summary: analysis of {payload.get('goal', 'the dataset')} "
                f"completed across {payload.get('n_steps', '?')} pipeline steps. "
                f"{body} Full details in the attached report and chart."
            )
        return "OK"


def default_backend() -> LLMBackend:
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicBackend()
        except Exception:
            pass
    return HeuristicBackend()
