"""End-to-end demo: analyse sales data with the multi-agent pipeline.

Usage:
    python run_demo.py                # offline (heuristic planner)
    ANTHROPIC_API_KEY=... python run_demo.py   # LLM-driven planning
"""
import json
import logging

from agentflow.agents.orchestrator import Orchestrator
from agentflow.core.llm import default_backend
from agentflow.core.tools import registry
import agentflow.toolkit.data_tools  # noqa: F401  (registers tools)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    llm = default_backend()
    print(f"LLM backend: {type(llm).__name__}")
    print(f"Registered tools: {registry.names()}\n")

    orchestrator = Orchestrator(llm, registry)
    result = orchestrator.run({
        "goal": "Analyse regional sales performance",
        "dataset": "data/sales_data.csv",
        "group_by": "region",
        "metric": "revenue",
    })

    print("\n=== FINAL RESULT ===")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
