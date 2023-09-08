SELECT (CASE WHEN `Access to electricity (% of population)` < 100 THEN "Electricity developing"
ELSE "Electricity well-developed" END) as Electricity_status, Entity as "Country", lower(`Access to electricity (% of population)`) as "Lowest status"
FROM global_data
GROUP BY Electricity_status, Entity
