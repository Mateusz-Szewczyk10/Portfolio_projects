# Data

All showcased-project data is generated locally from the public World Bank V2
Indicators API.

- `raw/world_bank_api.csv`: normalized API response
- `processed/world_bank_panel.csv`: validated analytical panel

These files are ignored by Git because World Bank values may be revised. Run
`python -m poland_eu_analysis.pipeline` to recreate them. The pipeline records
the retrieval timestamp and source URL in `raw/world_bank_metadata.json`.

The archived World Bank export from the original exercise remains under
`archive/learning-exercises/European Union impact on Poland/data/` for
provenance, but it is not used by the rebuilt analysis.

