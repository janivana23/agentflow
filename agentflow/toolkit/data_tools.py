"""Data-analysis tools available to the Analyst agent.

Each tool operates on a shared AnalysisContext so intermediate state
(the dataframe, findings, artifacts) flows between plan steps without
serialising data through the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ..core.tools import registry


@dataclass
class AnalysisContext:
    df: pd.DataFrame | None = None
    findings: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    out_dir: Path = Path("outputs")

    def reset(self, out_dir: str | Path | None = None) -> None:
        """Clear state between runs — required for long-lived processes
        (e.g. an MCP server) that execute multiple analyses in one process,
        since ctx is a module-level singleton shared by all tool calls."""
        self.df = None
        self.findings = []
        self.artifacts = {}
        if out_dir is not None:
            self.out_dir = Path(out_dir)


ctx = AnalysisContext()


@registry.register("Load a CSV file into the working dataframe.",
                   {"path": "path to the CSV file"})
def load_csv(path: str) -> dict[str, Any]:
    ctx.df = pd.read_csv(path)
    return {"rows": len(ctx.df), "columns": list(ctx.df.columns)}


@registry.register("Profile the dataframe: dtypes, null counts, basic stats.")
def profile_data() -> dict[str, Any]:
    df = ctx.df
    profile = {
        "rows": len(df),
        "nulls": {c: int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()},
        "duplicates": int(df.duplicated().sum()),
        "numeric_summary": df.describe(include="number").round(2).to_dict(),
    }
    ctx.findings.append(
        f"Dataset has {profile['rows']} rows, "
        f"{profile['duplicates']} duplicate rows, "
        f"nulls in {list(profile['nulls']) or 'no columns'}."
    )
    return profile


@registry.register("Clean the dataframe: drop duplicates, fill/drop nulls, fix dtypes.")
def clean_data() -> dict[str, Any]:
    df = ctx.df
    before = len(df)
    df = df.drop_duplicates().copy()
    num_cols = df.select_dtypes("number").columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())
    df = df.dropna()
    ctx.df = df.reset_index(drop=True)
    removed = before - len(ctx.df)
    ctx.findings.append(f"Cleaning removed {removed} rows (duplicates + unrecoverable nulls).")
    return {"rows_before": before, "rows_after": len(ctx.df)}


@registry.register("Detect outliers in a numeric column using the IQR method.",
                   {"column": "numeric column to inspect"})
def detect_outliers(column: str) -> dict[str, Any]:
    s = ctx.df[column]
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (s < lo) | (s > hi)
    n = int(mask.sum())
    ctx.artifacts["outliers"] = ctx.df[mask].to_dict("records")[:10]
    ctx.findings.append(
        f"Outlier check on '{column}': {n} value(s) outside "
        f"[{lo:,.0f}, {hi:,.0f}] (IQR method)."
    )
    return {"outliers": n, "bounds": [round(lo, 2), round(hi, 2)]}


@registry.register("Group by a column and aggregate a numeric metric.",
                   {"group_by": "column to group by", "metric": "numeric column to sum"})
def aggregate(group_by: str, metric: str) -> dict[str, Any]:
    result = (ctx.df.groupby(group_by)[metric]
              .agg(["sum", "mean", "count"])
              .round(2)
              .sort_values("sum", ascending=False))
    ctx.artifacts["agg_table"] = result.to_markdown()
    ctx.artifacts["agg_group_by"] = group_by
    ctx.artifacts["agg_metric"] = metric
    top = result.index[0]
    ctx.findings.append(
        f"Top {group_by} by total {metric}: {top} "
        f"({result.loc[top, 'sum']:,.0f} across {int(result.loc[top, 'count'])} records)."
    )
    return {"table": result.to_dict()}


@registry.register("Render a chart of the last aggregation.", {"kind": "bar|line"})
def make_chart(kind: str = "bar") -> dict[str, Any]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    group_by = ctx.artifacts["agg_group_by"]
    metric = ctx.artifacts["agg_metric"]
    series = ctx.df.groupby(group_by)[metric].sum().sort_values(ascending=False)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    series.plot(kind=kind, ax=ax, color="#4C72B0")
    ax.set_title(f"Total {metric} by {group_by}")
    ax.set_ylabel(metric)
    fig.tight_layout()

    ctx.out_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.out_dir / "chart.png"
    fig.savefig(path, dpi=120)
    plt.close(fig)
    ctx.artifacts["chart"] = str(path)
    return {"chart_path": str(path)}


@registry.register("Write a markdown report of all findings and artifacts.")
def write_report() -> dict[str, Any]:
    ctx.out_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.out_dir / "report.md"
    lines = ["# Analysis Report", "", "## Key findings", ""]
    lines += [f"- {f}" for f in ctx.findings]
    if "agg_table" in ctx.artifacts:
        lines += ["", "## Aggregation", "", ctx.artifacts["agg_table"]]
    if "chart" in ctx.artifacts:
        lines += ["", "## Chart", "", f"![chart]({Path(ctx.artifacts['chart']).name})"]
    path.write_text("\n".join(lines))
    ctx.artifacts["report"] = str(path)
    return {"report_path": str(path)}
