"""Synthetic-control estimation and robustness diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .config import StudyConfig


@dataclass(frozen=True)
class SyntheticControlResult:
    effects: pd.DataFrame
    weights: pd.DataFrame
    pre_rmspe: float
    post_rmspe: float
    rmspe_ratio: float


def outcome_matrix(frame: pd.DataFrame, config: StudyConfig) -> pd.DataFrame:
    """Return complete GDP-per-capita series indexed to 100 in the start year."""
    subset = frame[
        (frame["indicator_code"] == config.primary_outcome)
        & frame["year"].between(config.start_year, config.end_year)
    ]
    matrix = subset.pivot(index="year", columns="country_code", values="value").sort_index()
    required_years = list(range(config.start_year, config.end_year + 1))
    matrix = matrix.reindex(required_years)
    if config.treated_country not in matrix:
        raise ValueError("Treated country missing from primary-outcome matrix")
    complete = matrix.columns[matrix.notna().all()].tolist()
    donors = [country for country in config.donor_countries if country in complete]
    if len(donors) < 2:
        raise ValueError("At least two complete donor countries are required")
    complete_matrix = matrix[[config.treated_country, *donors]]
    base_values = complete_matrix.iloc[0]
    if (base_values <= 0).any():
        raise ValueError("Base-year values must be positive for index normalization")
    return complete_matrix.div(base_values).mul(100)


def _optimize_weights(treated_pre: np.ndarray, donor_pre: np.ndarray) -> np.ndarray:
    scale = float(np.mean(np.abs(treated_pre)))
    if not np.isfinite(scale) or scale == 0:
        raise ValueError("Treated pre-period outcome has no usable scale")
    y = treated_pre / scale
    x = donor_pre / scale
    n_donors = x.shape[1]

    def objective(weights: np.ndarray) -> float:
        residual = y - x @ weights
        return float(np.mean(residual**2) + 1e-8 * np.sum(weights**2))

    result = minimize(
        objective,
        x0=np.repeat(1 / n_donors, n_donors),
        method="SLSQP",
        bounds=[(0.0, 1.0)] * n_donors,
        constraints={"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
        options={"maxiter": 2_000, "ftol": 1e-12},
    )
    if not result.success:
        raise RuntimeError(f"Weight optimization failed: {result.message}")
    weights = np.clip(result.x, 0.0, 1.0)
    return weights / weights.sum()


def fit_synthetic_control(matrix: pd.DataFrame, config: StudyConfig) -> SyntheticControlResult:
    """Fit the constrained counterfactual and calculate period diagnostics."""
    treated = matrix[config.treated_country].to_numpy(dtype=float)
    donors = matrix.drop(columns=config.treated_country)
    pre_mask = matrix.index < config.intervention_year
    post_mask = ~pre_mask
    weights = _optimize_weights(
        treated[pre_mask], donors.to_numpy(dtype=float)[pre_mask, :]
    )
    synthetic = donors.to_numpy(dtype=float) @ weights
    gap = treated - synthetic
    pre_rmspe = float(np.sqrt(np.mean(gap[pre_mask] ** 2)))
    post_rmspe = float(np.sqrt(np.mean(gap[post_mask] ** 2)))
    ratio = post_rmspe / pre_rmspe if pre_rmspe > 0 else float("inf")

    effects = pd.DataFrame(
        {
            "year": matrix.index.astype(int),
            "observed": treated,
            "synthetic": synthetic,
            "gap": gap,
            "gap_percent": np.divide(
                gap,
                synthetic,
                out=np.full_like(gap, np.nan),
                where=synthetic != 0,
            )
            * 100,
            "period": np.where(pre_mask, "pre", "post"),
        }
    )
    weight_frame = pd.DataFrame(
        {"country_code": donors.columns, "weight": weights}
    ).sort_values("weight", ascending=False, ignore_index=True)
    return SyntheticControlResult(effects, weight_frame, pre_rmspe, post_rmspe, ratio)


def placebo_analysis(matrix: pd.DataFrame, config: StudyConfig) -> pd.DataFrame:
    """Treat each available country as Poland and calculate placebo diagnostics."""
    rows: list[dict[str, object]] = []
    countries = matrix.columns.tolist()
    for treated in countries:
        donors = tuple(country for country in countries if country != treated)
        placebo_config = StudyConfig(
            treated_country=treated,
            intervention_year=config.intervention_year,
            start_year=config.start_year,
            end_year=config.end_year,
            primary_outcome=config.primary_outcome,
            donor_countries=donors,
        )
        try:
            result = fit_synthetic_control(matrix[[treated, *donors]], placebo_config)
        except (RuntimeError, ValueError):
            continue
        rows.append(
            {
                "country_code": treated,
                "pre_rmspe": result.pre_rmspe,
                "post_rmspe": result.post_rmspe,
                "rmspe_ratio": result.rmspe_ratio,
                "is_treated": treated == config.treated_country,
            }
        )
    return pd.DataFrame(rows).sort_values("rmspe_ratio", ascending=False, ignore_index=True)


def leave_one_out_analysis(matrix: pd.DataFrame, config: StudyConfig) -> pd.DataFrame:
    """Measure sensitivity to excluding each positive-weight donor."""
    baseline = fit_synthetic_control(matrix, config)
    active = baseline.weights.loc[baseline.weights["weight"] > 1e-4, "country_code"]
    rows: list[dict[str, object]] = []
    for excluded in active:
        reduced = matrix.drop(columns=excluded)
        reduced_config = StudyConfig(
            treated_country=config.treated_country,
            intervention_year=config.intervention_year,
            start_year=config.start_year,
            end_year=config.end_year,
            primary_outcome=config.primary_outcome,
            donor_countries=tuple(
                country for country in config.donor_countries if country != excluded
            ),
        )
        result = fit_synthetic_control(reduced, reduced_config)
        post = result.effects[result.effects["period"] == "post"]
        rows.append(
            {
                "excluded_country": excluded,
                "mean_post_gap_percent": float(post["gap_percent"].mean()),
                "pre_rmspe": result.pre_rmspe,
            }
        )
    return pd.DataFrame(rows).sort_values("excluded_country", ignore_index=True)
