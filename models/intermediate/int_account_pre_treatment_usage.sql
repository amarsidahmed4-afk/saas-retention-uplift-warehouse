with usage as (
    select * from {{ ref('stg_segment__usage_events') }}
),

touches as (
    select * from {{ ref('stg_hubspot__cs_touches') }}
),

subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

filtered as (
    select
        u.account_id,
        u.login_frequency,
        u.feature_adoption,
        u.session_depth,
        u.event_timestamp,
        coalesce(h.treatment_date, s.snapshot_date + interval '60 days') as effective_cutoff_date
    from usage u
    inner join subs s on u.account_id = s.account_id
    left join touches h on u.account_id = h.account_id
    where u.event_timestamp <= coalesce(h.treatment_date, s.snapshot_date + interval '60 days')
),

aggregated as (
    select
        account_id,
        cast(avg(login_frequency) as integer) as login_frequency,
        cast(max(feature_adoption) as integer) as feature_adoption,
        cast(avg(session_depth) as decimal(10,2)) as session_depth
    from filtered
    group by account_id
)

select * from aggregated
