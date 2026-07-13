"""Create stakeholder-facing figures, tables, and narrative output."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[2] / ".cache" / "matplotlib")
)

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .analysis import SyntheticControlResult
from .config import StudyConfig


def plot_counterfactual(
    result: SyntheticControlResult, config: StudyConfig, output_path: Path
) -> None:
    """Plot observed and synthetic GDP per capita."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10, 5.5))
    axis.plot(result.effects["year"], result.effects["observed"], label="Poland", linewidth=2.4)
    axis.plot(
        result.effects["year"],
        result.effects["synthetic"],
        label="Synthetic comparison",
        linewidth=2.2,
        linestyle="--",
    )
    axis.axvline(config.intervention_year, color="#5f6368", linestyle=":", linewidth=1.5)
    axis.text(config.intervention_year + 0.25, axis.get_ylim()[1] * 0.96, "EU accession")
    axis.set(
        title="Poland's real GDP-per-capita growth versus the counterfactual",
        xlabel="Year",
        ylabel=f"Real GDP per capita index ({config.start_year} = 100)",
    )
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def plot_gap(result: SyntheticControlResult, config: StudyConfig, output_path: Path) -> None:
    """Plot the annual percentage gap from the synthetic comparison."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(10, 4.8))
    colors = ["#1a73e8" if value >= 0 else "#d93025" for value in result.effects["gap_percent"]]
    axis.bar(result.effects["year"], result.effects["gap_percent"], color=colors, width=0.8)
    axis.axhline(0, color="#202124", linewidth=0.8)
    axis.axvline(config.intervention_year - 0.5, color="#5f6368", linestyle=":")
    axis.set(
        title="Observed minus synthetic real GDP per capita",
        xlabel="Year",
        ylabel="Gap (%)",
    )
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def build_summary_metrics(
    result: SyntheticControlResult,
    placebos: pd.DataFrame,
    sensitivity: pd.DataFrame,
    config: StudyConfig,
) -> dict[str, object]:
    """Calculate a compact set of decision-oriented diagnostics."""
    post = result.effects[result.effects["period"] == "post"]
    treated_placebo = placebos.loc[placebos["is_treated"]].iloc[0]
    eligible_placebos = placebos[
        placebos["pre_rmspe"] <= 5 * float(treated_placebo["pre_rmspe"])
    ]
    rank = int(
        (eligible_placebos["rmspe_ratio"] > treated_placebo["rmspe_ratio"]).sum() + 1
    )
    top_donor = result.weights.iloc[0]
    metrics: dict[str, object] = {
        "mean_post_gap_percent": float(post["gap_percent"].mean()),
        "end_year_gap_percent": float(
            post.loc[post["year"] == config.end_year, "gap_percent"].iloc[0]
        ),
        "pre_rmspe": result.pre_rmspe,
        "post_pre_rmspe_ratio": result.rmspe_ratio,
        "placebo_rank": rank,
        "placebo_count": int(len(eligible_placebos)),
        "placebo_tail_share": float(
            (eligible_placebos["rmspe_ratio"] >= treated_placebo["rmspe_ratio"]).mean()
        ),
        "top_donor": str(top_donor["country_code"]),
        "top_donor_weight": float(top_donor["weight"]),
        "effective_donor_count": float(1 / (result.weights["weight"] ** 2).sum()),
    }
    if not sensitivity.empty:
        metrics["leave_one_out_min_gap_percent"] = float(
            sensitivity["mean_post_gap_percent"].min()
        )
        metrics["leave_one_out_max_gap_percent"] = float(
            sensitivity["mean_post_gap_percent"].max()
        )
    return metrics


def write_executive_summary(
    metrics: dict[str, object], coverage: dict[str, object], output_path: Path
) -> None:
    """Write a concise, caveated summary generated from current results."""
    min_gap = metrics.get("leave_one_out_min_gap_percent", float("nan"))
    max_gap = metrics.get("leave_one_out_max_gap_percent", float("nan"))
    text = f"""# Executive summary

## Question

How did Poland's real GDP per capita evolve after its 2004 EU accession relative
to a weighted comparison of non-EU economies with similar pre-2004 trajectories?

## Result

Across 2004-2019, Poland's real GDP-per-capita growth index was on average
**{metrics['mean_post_gap_percent']:.1f}%** relative to the synthetic comparison
(negative means below). In 2019 the gap was
**{metrics['end_year_gap_percent']:.1f}%**. The post/pre RMSPE
ratio was **{metrics['post_pre_rmspe_ratio']:.2f}**, ranking
**{metrics['placebo_rank']} of {metrics['placebo_count']}** among the treated and
placebo countries whose pre-period RMSPE was no more than five times Poland's.
The descriptive placebo tail share was **{metrics['placebo_tail_share']:.3f}**.

The largest donor weight was {metrics['top_donor']} at
{metrics['top_donor_weight']:.1%}; the effective donor count was
{metrics['effective_donor_count']:.1f}. Excluding one active donor at a time
produced mean post-period gaps from **{min_gap:.1f}% to {max_gap:.1f}%**.

## Interpretation

The fitted comparison does not provide unusual evidence that Poland's growth
path diverged after 2004: placebo countries produced at least as large a
post/pre fit deterioration. This is an informative negative result, not evidence
that accession had no effect. Accession was anticipated, reforms and capital
flows occurred simultaneously, and the pre-period contains only nine annual
observations.

## Data quality

The validated panel contains {coverage['rows']:,} country-indicator-year rows,
{coverage['countries']} countries, and {coverage['indicators']} indicators. The
overall missing-value share is {coverage['overall_missing_share']:.1%}; donors
without complete primary-outcome coverage are excluded before estimation.

## Recommended next step

Use this result as a structured quantitative case study alongside historical
and institutional evidence. For a policy-grade evaluation, expand the
pre-treatment window, pre-register donor-selection rules, and test alternative
outcomes and comparison pools.
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
