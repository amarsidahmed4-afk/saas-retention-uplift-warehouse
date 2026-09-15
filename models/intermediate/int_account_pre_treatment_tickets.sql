with tickets as (
    select * from {{ ref('stg_zendesk__support_tickets') }}
),

touches as (
    select * from {{ ref('stg_hubspot__cs_touches') }}
),

subs as (
    select * from {{ ref('stg_stripe__subscriptions') }}
),

filtered as (
    select
        t.account_id,
        t.ticket_volume,
        t.severe_tickets,
        t.ticket_timestamp,
        coalesce(h.treatment_date, s.snapshot_date + interval '60 days') as effective_cutoff_date
    from tickets t
    inner join subs s on t.account_id = s.account_id
    left join touches h on t.account_id = h.account_id
    where t.ticket_timestamp <= coalesce(h.treatment_date, s.snapshot_date + interval '60 days')
),

aggregated as (
    select
        account_id,
        cast(sum(ticket_volume) as integer) as ticket_volume,
        cast(sum(severe_tickets) as integer) as severe_tickets
    from filtered
    group by account_id
)

select * from aggregated
