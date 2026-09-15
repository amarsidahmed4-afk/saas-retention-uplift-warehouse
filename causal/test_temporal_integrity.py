import pytest
import duckdb
import pandas as pd

def test_temporal_integrity_in_mart():
    """
    Verifies that fct_account_retention contains timestamp columns and excludes
    post-treatment events (preventing temporal leakage).
    """
    con = duckdb.connect("warehouse.duckdb", read_only=True)
    
    # 1. Fetch mart table
    df_mart = con.execute("SELECT * FROM fct_account_retention").fetchdf()
    
    # Check column presence
    assert "snapshot_date" in df_mart.columns, "snapshot_date missing in mart"
    assert "treatment_date" in df_mart.columns, "treatment_date missing in mart"
    assert "churn_date" in df_mart.columns, "churn_date missing in mart"
    
    # 2. Check timestamp logic constraints
    # Treated accounts must have a treatment_date >= snapshot_date
    treated_df = df_mart[df_mart['is_treated'] == 1]
    assert not treated_df['treatment_date'].isna().any(), "Treated accounts must have non-null treatment_date"
    assert (treated_df['treatment_date'] >= treated_df['snapshot_date']).all(), "treatment_date must be on or after snapshot_date"
    
    # Untreated accounts should have NULL treatment_date
    untreated_df = df_mart[df_mart['is_treated'] == 0]
    assert untreated_df['treatment_date'].isna().all(), "Untreated accounts should have NULL treatment_date"
    
    # Churned accounts must have churn_date
    churned_df = df_mart[df_mart['is_churned'] == 1]
    assert not churned_df['churn_date'].isna().any(), "Churned accounts must have non-null churn_date"
    
    # 3. Check for temporal leakage prevention
    # In generate_seeds.py, post-treatment events were generated with artificial values:
    # login_frequency=999, feature_adoption=99, ticket_volume=888, severe_tickets=88.
    # Verify that NONE of these post-treatment values leaked into fct_account_retention features.
    assert (df_mart['login_frequency'] < 900).all(), "Post-treatment usage login_frequency leaked into mart!"
    assert (df_mart['feature_adoption'] < 50).all(), "Post-treatment usage feature_adoption leaked into mart!"
    assert (df_mart['ticket_volume'] < 800).all(), "Post-treatment support ticket_volume leaked into mart!"
    assert (df_mart['severe_tickets'] < 50).all(), "Post-treatment support severe_tickets leaked into mart!"


def test_intermediate_filters_post_treatment_events():
    """
    Explicitly checks that raw seed table contains post-treatment events,
    but intermediate pre-treatment views successfully filter them out.
    """
    con = duckdb.connect("warehouse.duckdb", read_only=True)
    
    # Raw usage seed has post-treatment records (login_frequency = 999)
    raw_leakage_count = con.execute("SELECT count(*) FROM stg_segment__usage_events WHERE login_frequency = 999").fetchone()[0]
    assert raw_leakage_count > 0, "Raw seed should contain post-treatment test records"
    
    # Intermediate view has filtered them out
    int_leakage_count = con.execute("SELECT count(*) FROM int_account_pre_treatment_usage WHERE login_frequency = 999").fetchone()[0]
    assert int_leakage_count == 0, "Intermediate pre-treatment usage view must filter out post-treatment records"
    
    # Raw tickets seed has post-treatment records (ticket_volume = 888)
    raw_tickets_leakage = con.execute("SELECT count(*) FROM stg_zendesk__support_tickets WHERE ticket_volume = 888").fetchone()[0]
    assert raw_tickets_leakage > 0, "Raw tickets seed should contain post-treatment test records"
    
    # Intermediate view has filtered them out
    int_tickets_leakage = con.execute("SELECT count(*) FROM int_account_pre_treatment_tickets WHERE ticket_volume = 888").fetchone()[0]
    assert int_tickets_leakage == 0, "Intermediate pre-treatment tickets view must filter out post-treatment records"
