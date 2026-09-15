with subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

usage as (
    select * from {{ ref('int_account_pre_treatment_usage') }}
),

touches as (
    select * from {{ ref('stg_hubspot__cs_touches') }}
),

tickets as (
    select * from {{ ref('int_account_pre_treatment_tickets') }}
),

joined as (
    select
        s.account_id,
        
        -- Subscription & Timestamps
        s.arr,
        s.plan_tier,
        s.seats,
        s.billing_interval,
        s.snapshot_date,
        h.treatment_date,
        s.churn_date,
        
        -- Pre-treatment Usage info
        coalesce(u.login_frequency, 0) as login_frequency,
        coalesce(u.feature_adoption, 0) as feature_adoption,
        coalesce(u.session_depth, 0.0) as session_depth,
        
        -- Pre-treatment Ticket info
        coalesce(t.ticket_volume, 0) as ticket_volume,
        coalesce(t.severe_tickets, 0) as severe_tickets,
        
        -- Treatment and Pilot Status
        h.is_treated,
        h.is_pilot,
        
        -- Outcome
        s.is_churned
        
    from subs s
    left join usage u on s.account_id = u.account_id
    left join touches h on s.account_id = h.account_id
    left join tickets t on s.account_id = t.account_id
)

select * from joined
