# Presenting AgentFlow as your project

## 30-second pitch

"I built AgentFlow, a multi-agent data analysis system. An orchestrator coordinates three specialist agents — a planner that decomposes goals into tool-call plans, an analyst that executes them, and a reviewer that acts as an automated quality gate with evidence-based checks. I designed the framework from scratch: typed message protocol, discoverable tool registry, and a pluggable LLM backend so the whole pipeline runs deterministically offline for testing but uses Claude for planning in production."

## Mapping to the job requirement

| Requirement | Where it shows |
|---|---|
| Understanding of agent working principles | perceive→reason→act loop in `BaseAgent`; plan/execute/review separation; why the reviewer checks evidence rather than trusting the analyst |
| Effectively leveraging agent tools | tool registry with runtime discovery — same pattern as function-calling APIs / MCP |
| Capability planning | capabilities defined as a tool catalog, not hard-coded; adding one = registering one function |
| Framework design | typed message protocol, pluggable LLM interface, domain-agnostic core vs. swappable toolkit |
| Engineering implementation | guardrails (hallucinated-tool rejection, retry budgets, bounded replanning), structured error traces, runs offline in CI |

## Questions you should be ready for

**Why multi-agent instead of one agent with all the tools?**
Separation of concerns: the reviewer must be independent from the executor or it just rubber-stamps. Also smaller, focused prompts per role plan better than one giant prompt.

**How do you stop the agent looping forever or hallucinating?**
Bounded iterations at the orchestrator; the planner's output is validated against the registry before execution; the reviewer checks filesystem/dataframe evidence, not model claims.

**How would you scale this?**
Message protocol already decouples agents — swap direct calls for a queue; run independent plan steps in parallel; add persistent memory (vector store) for cross-run learning.

**Why the heuristic backend?**
Determinism for tests and demos, zero API cost in CI, and it proves the agent logic is decoupled from the model. Same JSON contract as the LLM path.

## Good talking points

- Token economics: dataframes never pass through the LLM — only compact JSON summaries do (data plane vs. control plane).
- The reviewer feeding issues back into replanning is a simple self-correction loop — the core idea behind reflection-style agent patterns.
- The framework core is domain-agnostic; the data-analysis toolkit is one plug-in. You could ship a research-agent toolkit against the same core.
