"""Command-line orchestration for the complete analysis."""

from __future__ import annotations

import argparse
import json

from .analysis import (
    fit_synthetic_control,
    leave_one_out_analysis,
    outcome_matrix,
    placebo_analysis,
)
from .config import (
    FIGURE_DIR,
    PROCESSED_DIR,
    PROJECT_ROOT,
    RAW_DIR,
    REPORT_DIR,
    TABLE_DIR,
    StudyConfig,
)
from .data import fetch_world_bank_data, load_cached_data, save_data, validate_panel
from .reporting import (
    build_summary_metrics,
    plot_counterfactual,
    plot_gap,
    write_executive_summary,
)
from .sql import run_sql_analysis


def run(*, offline: bool = False) -> dict[str, object]:
    """Run data acquisition, validation, analysis, and reporting."""
    config = StudyConfig()
    raw_path = RAW_DIR / "world_bank_api.csv"
    metadata_path = RAW_DIR / "world_bank_metadata.json"

    for directory in (RAW_DIR, PROCESSED_DIR, FIGURE_DIR, TABLE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    if offline:
        frame = load_cached_data(raw_path)
    else:
        frame, metadata = fetch_world_bank_data(config)
        save_data(frame, metadata, raw_path, metadata_path)

    coverage = validate_panel(frame, config)
    processed_path = PROCESSED_DIR / "world_bank_panel.csv"
    frame.to_csv(processed_path, index=False)

    sql_summary = run_sql_analysis(PROJECT_ROOT / "sql" / "analysis.sql", PROJECT_ROOT)
    sql_summary.to_csv(TABLE_DIR / "sql_country_growth.csv", index=False)

    matrix = outcome_matrix(frame, config)
    result = fit_synthetic_control(matrix, config)
    placebos = placebo_analysis(matrix, config)
    sensitivity = leave_one_out_analysis(matrix, config)

    result.effects.to_csv(TABLE_DIR / "synthetic_control_effects.csv", index=False)
    result.weights.to_csv(TABLE_DIR / "donor_weights.csv", index=False)
    placebos.to_csv(TABLE_DIR / "placebo_diagnostics.csv", index=False)
    sensitivity.to_csv(TABLE_DIR / "leave_one_out.csv", index=False)

    plot_counterfactual(result, config, FIGURE_DIR / "counterfactual.png")
    plot_gap(result, config, FIGURE_DIR / "annual_gap.png")
    metrics = build_summary_metrics(result, placebos, sensitivity, config)
    (TABLE_DIR / "summary_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    write_executive_summary(metrics, coverage, REPORT_DIR / "executive_summary.md")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the previously downloaded raw CSV instead of calling the API.",
    )
    args = parser.parse_args()
    metrics = run(offline=args.offline)
    print("Analysis complete.")
    print(f"Mean post-period gap: {metrics['mean_post_gap_percent']:.1f}%")
    print(f"Placebo rank: {metrics['placebo_rank']} of {metrics['placebo_count']}")


if __name__ == "__main__":
    main()

