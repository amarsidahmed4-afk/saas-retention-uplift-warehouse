# Dashboard & Output Strategy

As specified in `.clinerules` and `PLAN.md`, this repository explicitly avoids building a hosted Streamlit or FastAPI web app.

Instead, the output of this model is designed to be fed back into the data warehouse (e.g., BigQuery), where it can be visualized by standard BI tools like **Looker Studio**. 

This decision is structural: a warehouse-native solution shouldn't require maintaining a separate live application. It should sit where the rest of the business logic sits.

## What the Dashboard Shows

A standard BI dashboard built on top of the `fct_account_retention` mart + the model output should visualize:

1. **The 4 Causal Quadrants:**
   - **Persuadable:** High Risk, High Uplift -> This is the CSM daily target list.
   - **Sleeping Dog:** Low Risk, High Uplift -> Do not touch (risk of triggering churn).
   - **Lost Cause:** High Risk, Low Uplift -> Do not waste expensive CSM time here.
   - **Sure Thing:** Low Risk, Low Uplift -> Safe without intervention.

2. **The ARR Value Gate:**
   - Visualizing accounts where `Expected Value (EV) = ARR * CATE` exceeds the `CSM_hourly_cost * Required_ROI`.
   - A table listing only the accounts that clear this financial threshold.

## Loom Walkthrough
*Note: A video walkthrough demonstrating this architecture and the Looker Studio implementation should be linked here once recorded.*
