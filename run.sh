#!/bin/bash
cat << 'EOF' > dbt_project.yml
name: 'saas_retention_uplift'
version: '1.0.0'
config-version: 2

profile: 'saas_retention_uplift'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

clean-targets:
  - "target"
  - "dbt_packages"

models:
  saas_retention_uplift:
    staging:
      +materialized: view
    intermediate:
      +materialized: view
    marts:
      +materialized: table
EOF

cat << 'EOF' > profiles.yml
saas_retention_uplift:
  outputs:
    dev:
      type: duckdb
      path: 'warehouse.duckdb'
      threads: 4
  target: dev
EOF

./venv/bin/python scripts/generate_seeds.py
./venv/bin/dbt seed --profiles-dir .
