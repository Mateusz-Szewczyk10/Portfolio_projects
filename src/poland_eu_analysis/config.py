"""Central analytical configuration."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR = PROJECT_ROOT / "reports"
FIGURE_DIR = REPORT_DIR / "figures"
TABLE_DIR = REPORT_DIR / "tables"

TREATED_COUNTRY = "POL"
INTERVENTION_YEAR = 2004
START_YEAR = 1995
END_YEAR = 2019

# Non-EU economies in Europe and Central Asia with plausible economic links or
# transition histories. Coverage is checked at runtime; this is not a claim
# that every donor is individually equivalent to Poland.
DONOR_COUNTRIES = (
    "ALB",
    "ARM",
    "AZE",
    "BIH",
    "GEO",
    "KAZ",
    "KGZ",
    "MDA",
    "MKD",
    "SRB",
    "TUR",
    "UKR",
    "UZB",
)

INDICATORS = {
    "NY.GDP.PCAP.KD": "Real GDP per capita (constant 2015 US$)",
    "NE.TRD.GNFS.ZS": "Trade (% of GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "FDI net inflows (% of GDP)",
    "SL.UEM.TOTL.ZS": "Unemployment (% of labor force)",
}

PRIMARY_OUTCOME = "NY.GDP.PCAP.KD"


@dataclass(frozen=True)
class StudyConfig:
    """Immutable parameters used throughout the analysis."""

    treated_country: str = TREATED_COUNTRY
    intervention_year: int = INTERVENTION_YEAR
    start_year: int = START_YEAR
    end_year: int = END_YEAR
    primary_outcome: str = PRIMARY_OUTCOME
    donor_countries: tuple[str, ...] = DONOR_COUNTRIES

    @property
    def countries(self) -> tuple[str, ...]:
        return (self.treated_country, *self.donor_countries)

    @property
    def pre_years(self) -> range:
        return range(self.start_year, self.intervention_year)

    @property
    def post_years(self) -> range:
        return range(self.intervention_year, self.end_year + 1)

