# AgentFlow — Multi-Agent Data Analysis System

A from-scratch multi-agent framework that turns a natural-language analysis goal into a cleaned dataset, chart, and markdown report — with a reviewer agent as an automated quality gate.

Built to demonstrate the full agent development lifecycle: **capability planning → framework design → engineering implementation**.

## Architecture

```
                 ┌──────────────┐
   goal ────────▶│ Orchestrator │  owns the workflow, bounded retry loop
                 └──────┬───────┘
     ┌──────────────┬─┴──────────────┬───────────────┐
     ▼              ▼                ▼               ▼
┌──────────┐  ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Planner  │  │ Analyst  │    │ Reviewer │    │ Reporter │
│ goal →   │  │ executes │    │ QA gate: │    │ exec     │
│ tool plan│  │ plan via │    │ approve/ │    │ summary  │
│ (JSON)   │  │ registry │    │ revise   │    │ (post-QA)│
└──────────┘  └────┬─────┘    └──────────┘    └──────────┘
                   ▼
          ┌─────────────────┐
          │  Tool Registry  │  load_csv · profile · clean · outliers ·
          │  (discoverable) │  aggregate · chart · report
          └─────────────────┘
```

Control flow: `plan → execute → review → report`. If the Reviewer returns `revise`, its issues are fed back to the Planner for one bounded replanning round (`MAX_ITERATIONS = 2`) — self-correction without infinite loops. The Reporter runs only after approval: communication is downstream of quality control.

## Design decisions

**1. Capability planning first.** The system's capabilities are defined as a tool catalog (`agentflow/toolkit/data_tools.py`), not hard-coded into agents. Adding a capability = registering one function. The Planner discovers tools at runtime via `registry.catalog()`, the same pattern as LLM function-calling APIs.

**2. Typed message protocol.** All inter-agent communication uses `Message(sender, recipient, type, content)` dataclasses (`core/message.py`) — observable, traceable, and easy to extend with new roles.

**3. Pluggable LLM backend.** Agents depend only on the `LLMBackend` interface (`core/llm.py`):
- `AnthropicBackend` — real LLM planning via Claude (set `ANTHROPIC_API_KEY`)
- `HeuristicBackend` — deterministic offline planner for demos, CI, and tests

Swapping backends requires zero agent changes; the whole system runs and is testable without network access.

**4. Guardrails at every layer.**
- Planner rejects hallucinated tool names before execution
- Analyst has a per-step retry budget; failures return structured error traces
- Reviewer validates against *evidence* (row counts, file existence), not the Analyst's self-report
- Orchestrator caps replanning iterations

**5. Separation of data and control planes.** Dataframes flow through a shared `AnalysisContext`; only compact JSON summaries pass through the LLM. Keeps token cost low and avoids serialising large data through prompts.

## Project layout

```
agentflow/
├── core/            # framework (reusable for any domain)
│   ├── agent.py     # BaseAgent: perceive → reason → act
│   ├── message.py   # typed message protocol
│   ├── tools.py     # tool registry + @register decorator
│   └── llm.py       # pluggable LLM backends
├── agents/          # roles built on the framework
│   ├── orchestrator.py
│   ├── planner.py
│   ├── analyst.py
│   ├── reviewer.py
│   └── reporter.py
└── toolkit/
    └── data_tools.py  # domain capabilities (swap for another domain)

mcp_server.py          # exposes the pipeline as MCP tools/prompts
run_demo.py             # standalone CLI demo (no MCP client needed)
```

## Run it

```bash
pip install -r requirements.txt
python run_demo.py                      # offline, deterministic
ANTHROPIC_API_KEY=... python run_demo.py  # LLM-driven planning
```

Output: `outputs/report.md` + `outputs/chart.png`. The demo dataset (`data/sales_data.csv`) intentionally contains duplicates and nulls to exercise the cleaning step.

Sample run:

```
LLM backend: HeuristicBackend
Registered tools: ['load_csv', 'profile_data', 'clean_data', 'detect_outliers', 'aggregate', 'make_chart', 'write_report']
...
"status": "success", "iterations": 1, "verdict": "approve"
```

## Use as an MCP server

`mcp_server.py` exposes the pipeline over the [Model Context Protocol](https://modelcontextprotocol.io), so any MCP-compatible client — Claude Desktop, Claude Code, or another MCP host — can run it directly:

- **Tool `analyze_csv(csv_path, group_by, metric, goal)`** — Claude calls this itself when you ask in plain language, e.g. *"analyze data/sales_data.csv, grouped by region, summing revenue."* This is how a friend would use it: point Claude at a CSV and describe what they want, no code required.
- **Prompt `analyze`** — this is the actual "/" mechanism in MCP (tools are *not* slash-invoked). Once connected, it shows up as `/agentflow:analyze` in clients that support MCP prompts (Claude Desktop does; Claude Code support varies by version).

Install and register with Claude Desktop — edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "agentflow": {
      "command": "python3",
      "args": ["/absolute/path/to/agentflow/mcp_server.py"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

Restart Claude Desktop, then either type `/agentflow:analyze` or just ask: *"Use agentflow to analyze my sales CSV by region."*

For Claude Code, register the same server with:

```bash
claude mcp add agentflow python3 /absolute/path/to/agentflow/mcp_server.py
```

Test it standalone first (no client needed) with the bundled [MCP Inspector](https://modelcontextprotocol.io/docs/tools/inspector):

```bash
pip install -r requirements.txt
mcp dev mcp_server.py
```

Each call writes its report/chart to `<csv folder>/agentflow_output/<name>_<timestamp>/`, so concurrent analyses never collide.

## Extending

- **New domain**: write a new toolkit module with `@registry.register` functions — the framework is domain-agnostic.
- **New role** (e.g., a Critic or Researcher): subclass `BaseAgent`, implement `handle()`, wire into the Orchestrator.
- **Parallel execution**: plan steps carry no hidden coupling beyond `AnalysisContext`; independent steps could run concurrently.
