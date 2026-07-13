from __future__ import annotations

import numpy as np
import pandas as pd

from poland_eu_analysis.analysis import (
    fit_synthetic_control,
    leave_one_out_analysis,
    outcome_matrix,
)
from poland_eu_analysis.config import StudyConfig


def synthetic_matrix() -> tuple[pd.DataFrame, StudyConfig]:
    years = np.arange(1995, 2010)
    t = years - years.min()
    matrix = pd.DataFrame(
        {
            "A": 80 + 2.0 * t + 0.08 * t**2,
            "B": 110 + 1.2 * t + 0.03 * t**2,
            "C": 65 + 2.7 * t,
            "D": 95 + 1.4 * t + 2 * np.sin(t / 2),
            "E": 75 + 2.1 * t + 1.5 * np.cos(t / 3),
        },
        index=years,
    )
    matrix.insert(0, "POL", 0.55 * matrix["A"] + 0.45 * matrix["B"])
    matrix.loc[matrix.index >= 2004, "POL"] += 12
    config = StudyConfig(
        intervention_year=2004,
        start_year=1995,
        end_year=2009,
        donor_countries=("A", "B", "C", "D", "E"),
    )
    return matrix, config


def test_synthetic_control_recovers_pre_fit_and_positive_post_gap() -> None:
    matrix, config = synthetic_matrix()
    result = fit_synthetic_control(matrix, config)
    assert np.isclose(result.weights["weight"].sum(), 1.0)
    assert (result.weights["weight"] >= 0).all()
    assert result.pre_rmspe < 0.1
    post = result.effects[result.effects["period"] == "post"]
    assert post["gap"].mean() > 10


def test_leave_one_out_returns_active_donor_sensitivity() -> None:
    matrix, config = synthetic_matrix()
    sensitivity = leave_one_out_analysis(matrix, config)
    assert not sensitivity.empty
    assert set(sensitivity.columns) == {
        "excluded_country",
        "mean_post_gap_percent",
        "pre_rmspe",
    }


def test_outcome_matrix_indexes_each_country_to_start_year() -> None:
    matrix, config = synthetic_matrix()
    rows = []
    for year, values in matrix.reset_index(names="year").set_index("year").iterrows():
        for country, value in values.items():
            rows.append(
                {
                    "country_code": country,
                    "indicator_code": config.primary_outcome,
                    "year": year,
                    "value": value,
                }
            )
    indexed = outcome_matrix(pd.DataFrame(rows), config)
    assert np.allclose(indexed.iloc[0], 100)
