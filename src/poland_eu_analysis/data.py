"""Download, normalize, and validate World Bank indicator data."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import INDICATORS, StudyConfig

API_BASE = "https://api.worldbank.org/v2"
REQUIRED_COLUMNS = {
    "country_code",
    "country_name",
    "indicator_code",
    "indicator_name",
    "year",
    "value",
}


def build_api_url(config: StudyConfig, indicator: str) -> str:
    """Build a documented World Bank V2 API request URL."""
    countries = ";".join(config.countries)
    return (
        f"{API_BASE}/country/{countries}/indicator/{indicator}"
        f"?format=json&date={config.start_year}:{config.end_year}&per_page=20000"
    )


def _parse_payload(payload: Any, indicator: str) -> list[dict[str, object]]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError(f"Unexpected World Bank response for {indicator}")

    rows: list[dict[str, object]] = []
    for record in payload[1]:
        rows.append(
            {
                "country_code": record.get("countryiso3code"),
                "country_name": (record.get("country") or {}).get("value"),
                "indicator_code": (record.get("indicator") or {}).get("id", indicator),
                "indicator_name": (record.get("indicator") or {}).get("value"),
                "year": record.get("date"),
                "value": record.get("value"),
            }
        )
    return rows


def fetch_world_bank_data(
    config: StudyConfig,
    *,
    session: requests.Session | None = None,
    timeout: int = 90,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Fetch configured indicators and return a tidy dataframe plus metadata."""
    client = session or _retrying_session()
    all_rows: list[dict[str, object]] = []
    urls: list[str] = []

    for indicator in INDICATORS:
        url = build_api_url(config, indicator)
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
        all_rows.extend(_parse_payload(response.json(), indicator))
        urls.append(url)

    frame = normalize_panel(pd.DataFrame(all_rows))
    metadata: dict[str, object] = {
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "provider": "World Bank, World Development Indicators",
        "api_version": "v2",
        "urls": urls,
        "study_window": [config.start_year, config.end_year],
    }
    return frame, metadata


def _retrying_session() -> requests.Session:
    """Create a session resilient to transient public-API failures."""
    retries = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    client = requests.Session()
    client.mount("https://", HTTPAdapter(max_retries=retries))
    return client


def normalize_panel(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply stable types and ordering to an API-shaped dataframe."""
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    result = frame.loc[:, sorted(REQUIRED_COLUMNS)].copy()
    result["year"] = pd.to_numeric(result["year"], errors="raise").astype("int64")
    result["value"] = pd.to_numeric(result["value"], errors="coerce")
    result = result.sort_values(["indicator_code", "country_code", "year"])
    return result.reset_index(drop=True)


def validate_panel(frame: pd.DataFrame, config: StudyConfig) -> dict[str, object]:
    """Fail on structural defects and summarize analytical coverage."""
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if frame.duplicated(["country_code", "indicator_code", "year"]).any():
        raise ValueError("Duplicate country-indicator-year observations detected")
    if not frame["year"].between(config.start_year, config.end_year).all():
        raise ValueError("Panel contains years outside the configured study window")
    if config.treated_country not in set(frame["country_code"]):
        raise ValueError("Treated country is absent")

    primary = frame[frame["indicator_code"] == config.primary_outcome]
    coverage = primary.groupby("country_code")["value"].apply(lambda values: values.notna().mean())
    treated_coverage = float(coverage.get(config.treated_country, 0.0))
    if treated_coverage < 1.0:
        raise ValueError("Poland's primary outcome is incomplete in the study window")

    complete_donors = coverage[coverage == 1.0].index.intersection(config.donor_countries).tolist()
    if len(complete_donors) < 5:
        raise ValueError("Fewer than five donors have complete primary-outcome coverage")

    return {
        "rows": int(len(frame)),
        "countries": int(frame["country_code"].nunique()),
        "indicators": int(frame["indicator_code"].nunique()),
        "complete_primary_donors": complete_donors,
        "overall_missing_share": float(frame["value"].isna().mean()),
    }


def save_data(
    frame: pd.DataFrame,
    metadata: dict[str, object],
    raw_path: Path,
    metadata_path: Path,
) -> None:
    """Persist normalized API data and retrieval provenance."""
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(raw_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_cached_data(raw_path: Path) -> pd.DataFrame:
    """Load a previously normalized API response."""
    if not raw_path.exists():
        raise FileNotFoundError(f"Offline input not found: {raw_path}")
    return normalize_panel(pd.read_csv(raw_path))
