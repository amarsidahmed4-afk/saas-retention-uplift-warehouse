with source as (
    select * from {{ ref('zendesk_support_tickets') }}
),

renamed as (
    select
        account_id::varchar as account_id,
        ticket_volume::integer as ticket_volume,
        severe_tickets::integer as severe_tickets
    from source
)

select * from renamed
