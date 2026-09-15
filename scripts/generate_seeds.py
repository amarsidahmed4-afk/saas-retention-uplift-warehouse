import os

import numpy as np
import pandas as pd

np.random.seed(42)

NUM_ACCOUNTS = 5000
NUM_PILOT = 500

def generate_seeds():
    # 1. Base account parameters
    account_ids = [f"acc_{i:04d}" for i in range(NUM_ACCOUNTS)]

    # Latent health score (0 to 1, higher is better)
    health = np.random.beta(2, 2, size=NUM_ACCOUNTS)

    # Is Pilot
    is_pilot = np.zeros(NUM_ACCOUNTS, dtype=bool)
    is_pilot[:NUM_PILOT] = True
    np.random.shuffle(is_pilot) # Randomize pilot assignment across the dataset

    # Plan info
    plans = ["Starter", "Professional", "Enterprise"]
    plan_tier = np.random.choice(plans, size=NUM_ACCOUNTS, p=[0.4, 0.4, 0.2])

    seats = np.zeros(NUM_ACCOUNTS)
    seats[plan_tier == "Starter"] = np.random.randint(1, 10, size=(plan_tier == "Starter").sum())
    seats[plan_tier == "Professional"] = np.random.randint(10, 50, size=(plan_tier == "Professional").sum())
    seats[plan_tier == "Enterprise"] = np.random.randint(50, 200, size=(plan_tier == "Enterprise").sum())

    billing_intervals = ["monthly", "annual"]
    billing_interval = np.random.choice(billing_intervals, size=NUM_ACCOUNTS, p=[0.7, 0.3])

    # ARR
    price_per_seat = {"Starter": 20, "Professional": 50, "Enterprise": 100}
    arr = [seats[i] * price_per_seat[plan_tier[i]] * 12 * np.random.uniform(0.9, 1.1) for i in range(NUM_ACCOUNTS)]
    arr = np.round(arr, 2)

    # Segment usage metrics (positively correlated with health)
    login_frequency = np.round(health * 30 + np.random.normal(0, 5, size=NUM_ACCOUNTS))
    login_frequency = np.clip(login_frequency, 0, 100)

    feature_adoption = np.round(health * 10 + np.random.normal(0, 2, size=NUM_ACCOUNTS))
    feature_adoption = np.clip(feature_adoption, 0, 15)

    session_depth = health * 5 + np.random.normal(0, 1, size=NUM_ACCOUNTS)
    session_depth = np.clip(session_depth, 0.1, 10)

    # Zendesk metrics (negatively correlated with health)
    ticket_volume = np.round((1 - health) * 15 + np.random.normal(0, 2, size=NUM_ACCOUNTS))
    ticket_volume = np.clip(ticket_volume, 0, 50)

    severe_tickets = np.round((1 - health) * 3 + np.random.normal(0, 1, size=NUM_ACCOUNTS))
    severe_tickets = np.clip(severe_tickets, 0, ticket_volume)

    # Treatment assignment (confounded in bulk, randomized in pilot)
    received_cs_touch = np.zeros(NUM_ACCOUNTS, dtype=int)

    # Bulk assignment: probability of treatment depends on health (healthier = more likely to get touch)
    bulk_mask = ~is_pilot
    bulk_prob = np.clip(health[bulk_mask] * 0.6 + 0.1, 0.0, 1.0)
    received_cs_touch[bulk_mask] = np.random.binomial(1, bulk_prob)

    # Pilot assignment: completely randomized 50/50
    pilot_mask = is_pilot
    received_cs_touch[pilot_mask] = np.random.binomial(1, 0.5, size=pilot_mask.sum())

    # Outcome: Churned (0 = retained, 1 = churned)
    # True control churn probability (decreases with health)
    churn_prob_control = np.clip(0.8 - 0.6 * health, 0.05, 0.95)

    # True treatment effect (uplift in retention, i.e., decrease in churn prob)
    # Peak effect for middle-health (the "persuadables").
    # High health = sure thing (low effect). Low health = lost cause (low effect).
    uplift = 0.3 * np.exp(-((health - 0.5) ** 2) / 0.05)

    churn_prob_treat = np.clip(churn_prob_control - uplift, 0.05, 0.95)

    # Final outcome
    actual_churn_prob = np.where(received_cs_touch, churn_prob_treat, churn_prob_control)
    churned = np.random.binomial(1, actual_churn_prob)

    # Timestamps
    # snapshot_date: cohort baseline date (2026-01-01)
    snapshot_date = ["2026-01-01"] * NUM_ACCOUNTS

    # treatment_date: between 2026-02-01 and 2026-03-31 for treated accounts, None for untreated
    treatment_dates = []
    base_date = pd.Timestamp("2026-02-01")
    for i in range(NUM_ACCOUNTS):
        if received_cs_touch[i] == 1:
            days_offset = np.random.randint(0, 59) # 2026-02-01 to 2026-03-31
            t_date = (base_date + pd.Timedelta(days=days_offset)).strftime("%Y-%m-%d")
            treatment_dates.append(t_date)
        else:
            treatment_dates.append(None)

    # churn_date: between 2026-04-15 and 2026-06-30 for churned accounts, None for retained
    churn_dates = []
    churn_base = pd.Timestamp("2026-04-15")
    for i in range(NUM_ACCOUNTS):
        if churned[i] == 1:
            days_offset = np.random.randint(0, 76)
            c_date = (churn_base + pd.Timedelta(days=days_offset)).strftime("%Y-%m-%d")
            churn_dates.append(c_date)
        else:
            churn_dates.append(None)

    # Create DataFrames
    df_stripe = pd.DataFrame({
        "account_id": account_ids,
        "arr": arr,
        "plan_tier": plan_tier,
        "seats": seats.astype(int),
        "billing_interval": billing_interval,
        "churned": churned,
        "snapshot_date": snapshot_date,
        "churn_date": churn_dates
    })

    # Generate timestamped usage events (Pre-treatment & Post-treatment events to test leakage prevention)
    # Pre-treatment events: Jan 15, 2026 (strictly before treatment_date and 60-day cutoff)
    # Post-treatment events: Apr 15, 2026 (strictly after treatment_date and 60-day cutoff)
    df_segment_pre = pd.DataFrame({
        "account_id": account_ids,
        "event_timestamp": "2026-01-15",
        "login_frequency": login_frequency.astype(int),
        "feature_adoption": feature_adoption.astype(int),
        "session_depth": np.round(session_depth, 2)
    })

    # Post-treatment usage features (with artificially distorted values to make leakage detectable)
    df_segment_post = pd.DataFrame({
        "account_id": account_ids,
        "event_timestamp": "2026-04-15",
        "login_frequency": 999, # Artificial value to detect leakage if included
        "feature_adoption": 99,
        "session_depth": 99.99
    })

    df_segment = pd.concat([df_segment_pre, df_segment_post], ignore_index=True)

    df_hubspot = pd.DataFrame({
        "account_id": account_ids,
        "received_cs_touch": received_cs_touch,
        "is_pilot": is_pilot.astype(int),
        "treatment_date": treatment_dates
    })

    # Generate timestamped support tickets (Pre-treatment & Post-treatment events)
    df_zendesk_pre = pd.DataFrame({
        "account_id": account_ids,
        "ticket_timestamp": "2026-01-20",
        "ticket_volume": ticket_volume.astype(int),
        "severe_tickets": severe_tickets.astype(int)
    })

    df_zendesk_post = pd.DataFrame({
        "account_id": account_ids,
        "ticket_timestamp": "2026-04-20",
        "ticket_volume": 888, # Artificial value to detect leakage if included
        "severe_tickets": 88
    })

    df_zendesk = pd.concat([df_zendesk_pre, df_zendesk_post], ignore_index=True)

    # Ensure seeds directory exists
    os.makedirs("seeds", exist_ok=True)

    # Write to CSV
    df_stripe.to_csv("seeds/stripe_subscriptions.csv", index=False)
    df_segment.to_csv("seeds/segment_usage_events.csv", index=False)
    df_hubspot.to_csv("seeds/hubspot_cs_touches.csv", index=False)
    df_zendesk.to_csv("seeds/zendesk_support_tickets.csv", index=False)

    print("Seed data generated successfully in seeds/ directory.")
    print(f"Total Accounts: {NUM_ACCOUNTS}, Pilot Accounts: {NUM_PILOT}")
    print(f"Bulk Treatment Rate: {received_cs_touch[bulk_mask].mean():.2f}")
    print(f"Pilot Treatment Rate: {received_cs_touch[pilot_mask].mean():.2f}")
    print(f"Overall Churn Rate: {churned.mean():.2f}")

if __name__ == "__main__":
    generate_seeds()
