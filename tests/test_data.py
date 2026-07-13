from __future__ import annotations

import pandas as pd
import pytest

from poland_eu_analysis.config import StudyConfig
from poland_eu_analysis.data import build_api_url, normalize_panel, validate_panel


def make_panel(config: StudyConfig) -> pd.DataFrame:
    rows = []
    for country_number, country in enumerate(config.countries, start=1):
        for year in range(config.start_year, config.end_year + 1):
            rows.append(
                {
                    "country_code": country,
                    "country_name": country,
                    "indicator_code": config.primary_outcome,
                    "indicator_name": "Outcome",
                    "year": str(year),
                    "value": country_number * 100 + year,
                }
            )
    return pd.DataFrame(rows)


def test_build_api_url_contains_study_scope() -> None:
    config = StudyConfig(start_year=2000, end_year=2005, donor_countries=("ALB", "TUR"))
    url = build_api_url(config, config.primary_outcome)
    assert "country/POL;ALB;TUR" in url
    assert "date=2000:2005" in url
    assert "format=json" in url


def test_normalize_and_validate_complete_panel() -> None:
    config = StudyConfig(
        start_year=2000,
        end_year=2004,
        intervention_year=2002,
        donor_countries=("A", "B", "C", "D", "E"),
    )
    frame = normalize_panel(make_panel(config))
    coverage = validate_panel(frame, config)
    assert frame["year"].dtype == "int64"
    assert coverage["countries"] == 6
    assert len(coverage["complete_primary_donors"]) == 5


def test_validation_rejects_duplicate_keys() -> None:
    config = StudyConfig(
        start_year=2000,
        end_year=2004,
        intervention_year=2002,
        donor_countries=("A", "B", "C", "D", "E"),
    )
    frame = normalize_panel(make_panel(config))
    duplicate = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        validate_panel(duplicate, config)

