-- Stakeholder-facing descriptive analysis of the validated World Bank panel.
-- The synthetic-control estimator is implemented in Python because it requires
-- constrained numerical optimization; all descriptive transformations remain
-- independently inspectable in SQL.

CREATE OR REPLACE VIEW panel AS
SELECT
    country_code,
    country_name,
    indicator_code,
    indicator_name,
    CAST(year AS INTEGER) AS year,
    CAST(value AS DOUBLE) AS value
FROM read_csv_auto('data/processed/world_bank_panel.csv', header = true);

CREATE OR REPLACE VIEW gdp_per_capita AS
SELECT *
FROM panel
WHERE indicator_code = 'NY.GDP.PCAP.KD';

WITH endpoints AS (
    SELECT
        country_code,
        ANY_VALUE(country_name) AS country_name,
        MAX(value) FILTER (WHERE year = 2003) AS value_2003,
        MAX(value) FILTER (WHERE year = 2019) AS value_2019
    FROM gdp_per_capita
    GROUP BY country_code
),
period_averages AS (
    SELECT
        country_code,
        AVG(value) FILTER (WHERE year < 2004) AS pre_2004_average,
        AVG(value) FILTER (WHERE year >= 2004) AS post_2004_average,
        COUNT(value) AS observed_years
    FROM gdp_per_capita
    GROUP BY country_code
)
SELECT
    e.country_code,
    e.country_name,
    ROUND(e.value_2003, 2) AS value_2003,
    ROUND(e.value_2019, 2) AS value_2019,
    ROUND(100 * (POWER(e.value_2019 / e.value_2003, 1.0 / 16) - 1), 2) AS cagr_percent,
    ROUND(p.pre_2004_average, 2) AS pre_2004_average,
    ROUND(p.post_2004_average, 2) AS post_2004_average,
    p.observed_years
FROM endpoints e
JOIN period_averages p USING (country_code)
ORDER BY cagr_percent DESC;

