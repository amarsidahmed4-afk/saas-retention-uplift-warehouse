# Limitations

*Living document — update this whenever a design constraint in `.clinerules` gets bent, a modeling assumption changes, or something below stops being true. A stale limitations file is treated as a bug in this repo, not a formality. Last updated: [date of last real change, not last file touch].*

## Data
- **Everything in `seeds/` is synthetic.** Stripe/Segment/HubSpot/Zendesk-shaped, generated to be structurally realistic, not sourced from any real company's data. Headline metrics from this pipeline describe whether the pipeline is wired correctly, not whether the model works on real accounts.
- **The "Q2 win-back pilot" (~500 accounts) is itself synthetic.** It's designed to *behave like* a genuinely randomized experiment (unconfounded treatment assignment) so the causal estimation approach has one honest anchor to calibrate against — but it is not a real experiment that was actually run. Treat any uplift number calibrated against it as a demonstration of *method*, not a validated estimate of *real-world* retention impact.
- **The bulk of the non-pilot data has deliberately confounded treatment assignment** (CSMs semi-target healthier at-risk accounts, mirroring real CS behavior). This is intentional — it's what makes the propensity-adjustment / calibration story real rather than trivial — but it means naive comparisons (treated vs. untreated accounts, no adjustment) anywhere in this repo would be actively misleading. Any such comparison should be flagged, not just accepted, if one shows up in a query or notebook.

## Modeling
- [Fill in once v1.1's model exists: sample size, calibration method, which features are still treated as proxies, any known weak points in the propensity adjustment.]
- No claim in this repo about "who to reach out to" should be read as validated on real accounts until it's been checked against real logged CS outcomes — that's a prerequisite for production use, not a nice-to-have.

## Architecture
- **Batch only, by design** — this reads from and writes to the warehouse; there is no live API and none is planned. If that ever changes, it's a deliberate architecture decision requiring its own review, not a routine addition (see `.clinerules`).
- **No real cloud credentials in CI** — `dbt build`/`dbt test` run against DuckDB, not the real warehouse. CI passing doesn't confirm the BigQuery/Snowflake path works; that needs a manual check against a real (non-prod) target.

## What would need to be true before trusting this on a real account list
- Real logged CS-touch outcomes to calibrate against, not just the synthetic pilot.
- A sample size large enough for CATE estimation specifically — bigger than what's needed for plain churn classification, since it's estimating a difference of two noisy quantities.
- Independent review of the propensity-adjustment logic against the real (not synthetic) confounding pattern in actual CS assignment behavior, since the real pattern won't exactly match what the synthetic generator assumes.
