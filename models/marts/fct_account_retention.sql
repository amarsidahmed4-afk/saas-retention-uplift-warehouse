with subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

usage as (
    select * from {{ ref('stg_segment__usage_events') }}
),

touches as (
    select * from {{ ref('stg_hubspot__cs_touches') }}
),

tickets as (
    select * from {{ ref('stg_zendesk__support_tickets') }}
),

joined as (
    select
        s.account_id,
        
        -- Subscription info
        s.arr,
        s.plan_tier,
        s.seats,
        s.billing_interval,
        
        -- Usage info
        u.login_frequency,
        u.feature_adoption,
        u.session_depth,
        
        -- Ticket info
        t.ticket_volume,
        t.severe_tickets,
        
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
