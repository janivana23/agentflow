"""AgentFlow as an MCP server.

Exposes the multi-agent pipeline (orchestrator -> planner -> analyst ->
reviewer -> reporter) as MCP primitives so any MCP-compatible client
(Claude Desktop, Claude Code, other MCP hosts) can drive it directly:

- Tool `analyze_csv`   — invoked by Claude via natural language
                         ("analyze sales.csv grouped by region")
                         or explicitly by any client that lists tools.
- Prompt `analyze`     — surfaces as a slash command ("/agentflow:analyze")
                         in clients that support the MCP prompts primitive
                         (e.g. Claude Desktop). Prompts are the actual "/"
                         mechanism in MCP — tools are not slash-invoked.

Run standalone for local testing:
    python mcp_server.py

Wire into a client via stdio — see README "Use as an MCP server" section
for the exact Claude Desktop / Claude Code config.
"""
from __future__ import annotations

import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from agentflow.agents.orchestrator import Orchestrator
from agentflow.core.llm import default_backend
from agentflow.core.tools import registry
from agentflow.toolkit.data_tools import ctx
import agentflow.toolkit.data_tools  # noqa: F401  (registers tools)

mcp = FastMCP("agentflow")

# One shared orchestrator per server process — cheap to construct, and the
# LLM backend (real Claude or offline heuristic) is chosen once at startup.
_llm = default_backend()
_orchestrator = Orchestrator(_llm, registry)


@mcp.tool()
def analyze_csv(csv_path: str, group_by: str, metric: str, goal: str = "") -> str:
    """Run the AgentFlow multi-agent pipeline on a CSV file.

    Cleans the data, flags outliers, aggregates `metric` by `group_by`,
    renders a chart, and writes a markdown report with an executive
    summary. Returns a text summary; the full report and chart are written
    to disk next to the input file (in an `agentflow_output/` subfolder).

    Args:
        csv_path: absolute or relative path to the CSV file to analyze.
        group_by: column name to group by (e.g. "region", "product").
        metric: numeric column to aggregate (e.g. "revenue", "units").
        goal: optional free-text description of the analysis goal.
    """
    src = Path(csv_path).expanduser().resolve()
    if not src.exists():
        return f"Error: file not found: {src}"

    out_dir = src.parent / "agentflow_output" / f"{src.stem}_{int(time.time())}"
    ctx.reset(out_dir=out_dir)

    result = _orchestrator.run({
        "goal": goal or f"Analyse {src.name}",
        "dataset": str(src),
        "group_by": group_by,
        "metric": metric,
    })

    if result["status"] != "success":
        return f"Analysis failed at stage '{result.get('stage')}': {result.get('detail')}"

    return (
        f"{result['summary']}\n\n"
        f"Report: {ctx.artifacts.get('report')}\n"
        f"Chart:  {ctx.artifacts.get('chart')}"
    )


@mcp.tool()
def list_capabilities() -> str:
    """List the analysis tools available to the AgentFlow pipeline.

    Useful for understanding what steps a call to analyze_csv will run
    (load, profile, clean, detect_outliers, aggregate, chart, report).
    """
    return registry.catalog()


@mcp.prompt()
def analyze(csv_path: str, group_by: str, metric: str) -> str:
    """Slash-command entry point: /agentflow:analyze

    Scaffolds a natural-language request so the host model calls
    analyze_csv with the right arguments.
    """
    return (
        f"Use the analyze_csv tool to analyze {csv_path}, "
        f"grouping by '{group_by}' and aggregating '{metric}'. "
        f"Summarize the findings for me afterward."
    )


if __name__ == "__main__":
    mcp.run()
