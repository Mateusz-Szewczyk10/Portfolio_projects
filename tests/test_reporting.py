from __future__ import annotations

import pandas as pd

from poland_eu_analysis.analysis import SyntheticControlResult
from poland_eu_analysis.config import StudyConfig
from poland_eu_analysis.reporting import build_summary_metrics


def test_summary_metrics_include_placebo_rank() -> None:
    effects = pd.DataFrame(
        {
            "year": [2003, 2004, 2005],
            "observed": [100.0, 120.0, 130.0],
            "synthetic": [100.0, 100.0, 100.0],
            "gap": [0.0, 20.0, 30.0],
            "gap_percent": [0.0, 20.0, 30.0],
            "period": ["pre", "post", "post"],
        }
    )
    weights = pd.DataFrame({"country_code": ["A", "B"], "weight": [0.7, 0.3]})
    result = SyntheticControlResult(effects, weights, 1.0, 2.0, 2.0)
    placebos = pd.DataFrame(
        {
            "country_code": ["A", "POL", "B"],
            "pre_rmspe": [2.0, 1.0, 3.0],
            "rmspe_ratio": [3.0, 2.0, 1.0],
            "is_treated": [False, True, False],
        }
    )
    sensitivity = pd.DataFrame(
        {"excluded_country": ["A"], "mean_post_gap_percent": [22.0]}
    )
    config = StudyConfig(start_year=2003, intervention_year=2004, end_year=2005)
    metrics = build_summary_metrics(result, placebos, sensitivity, config)
    assert metrics["mean_post_gap_percent"] == 25.0
    assert metrics["placebo_rank"] == 2
    assert metrics["top_donor"] == "A"
