# Methodology and limitations

## Estimand

The analysis estimates the difference between Poland's observed real GDP per
capita after 2004 and the path predicted by a weighted combination of donor
countries that resembles Poland before 2004. The average post-period gap is a
descriptive counterfactual estimate, not an independently identified causal
effect of EU membership.

## Design choices

The primary series is World Bank indicator `NY.GDP.PCAP.KD` (GDP per capita in
constant 2015 US dollars). Each country is indexed to 100 in 1995 before weights
are estimated, so the comparison targets cumulative growth trajectories rather
than absolute income levels. The 1995-2019 window provides nine pre-accession
observations and avoids treating the pandemic and later geopolitical shocks as
ordinary post-treatment years.

Donor weights are non-negative and sum to one. They minimize mean squared
prediction error during 1995-2003, with a small regularization term to improve
numerical stability. Countries missing primary-outcome values anywhere in the
study window are excluded automatically.

## Diagnostics

- Pre-period RMSPE measures whether the counterfactual reproduces Poland before
  accession.
- The post/pre RMSPE ratio measures whether the divergence is unusually large
  relative to baseline mismatch.
- In-space placebos treat each donor as if it joined in 2004 and compare its
  RMSPE ratio with Poland's. The reported rank retains placebo countries whose
  pre-period RMSPE is no more than five times Poland's, because badly fitted
  placebos do not provide a meaningful reference distribution.
- Leave-one-donor-out estimates show whether the headline result depends on a
  single high-weight country.

## Important limitations

1. EU accession was anticipated and accompanied by domestic reforms, capital
   flows, migration, and global economic changes. The intervention is not a
   randomized event.
2. Nine pre-treatment annual observations limit the ability to validate a
   flexible counterfactual.
3. Donor countries can experience their own shocks and may differ from Poland
   on unobserved determinants of growth.
4. World Bank series are revised, so exact results may change between runs.
5. Placebo ranks are descriptive with a small donor pool; they are not a
   conventional randomized-test p-value.
6. Results should be interpreted alongside institutional and historical
   evidence, not as a standalone policy evaluation.
