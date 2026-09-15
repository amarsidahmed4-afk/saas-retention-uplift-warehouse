with source as (
    select * from {{ ref('hubspot_cs_touches') }}
),

renamed as (
    select
        account_id::varchar as account_id,
        received_cs_touch::integer as is_treated,
        is_pilot::integer as is_pilot,
        treatment_date::date as treatment_date
    from source
)

select * from renamed
