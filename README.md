# saas-retention-uplift-warehouse

A warehouse-native (dbt) causal uplift model designed for SaaS retention. Rather than just identifying which accounts are "at risk" (churn propensity), this project models which accounts would *actually be saved* by a Customer Success (CS) intervention.

By applying causal modeling (T-learner) inside a warehouse-native structure, it explicitly addresses the problem of *uplift*—optimizing CS time by intervening only when the Expected Value (EV) of the intervention exceeds the cost. 

## Features
- **Warehouse-Native**: Built with `dbt` and tested against `DuckDB` (for local/CI) with `BigQuery` (for prod).
- **Causal Uplift Model**: T-learner logic designed to adjust for confounded treatment (CSMs already call healthy/cooperative accounts) using a small, truly randomized pilot as an anchor.
- **ARR-denominated Gates**: Decisions scale dynamically with account ARR, not arbitrary absolute dollar values.
- **No External Value Spoofing**: All financial inputs come directly from warehouse (e.g., Stripe staging tables), ensuring data integrity.

## Architecture & Layout
```
saas-retention-uplift-warehouse/
├── seeds/                     # synthetic Stripe/Segment/HubSpot/Zendesk tables
├── models/
│   ├── staging/                stg_stripe__subscriptions.sql, etc.
│   └── marts/                  fct_account_retention.sql
├── causal/
│   └── train_uplift_model.py   # Propensity-adjusted uplift model (T-learner in v1.1)
├── tests/                      # Pytest tests for model and threshold logic
├── scripts/                    # Scripts to generate seeds
├── dbt_project.yml             # dbt configuration
└── LIMITATIONS.md              # Living document documenting synthetic nature and constraints
```

## Running the Project Locally
### 1. Setup Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install dbt-duckdb pandas numpy scikit-learn pytest
```

### 2. Generate Synthetic Seeds
```bash
python scripts/generate_seeds.py
```

### 3. Build dbt Models (DuckDB)
```bash
dbt build --profiles-dir . --threads 1
```

### 4. Run the Proxy Model (v1)
```bash
python causal/train_uplift_model.py
```

## Caveats and Limitations
Please read `LIMITATIONS.md` carefully. This repository leverages structurally realistic synthetic data, and the modeled pilot is simulated, not real. It stands as a demonstrative architectural pattern for causal uplift on retention, not a pre-trained model applicable out-of-the-box on your dataset.
