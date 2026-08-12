with source as (
    select * from {{ ref('segment_usage_events') }}
),

renamed as (
    select
        account_id::varchar as account_id,
        login_frequency::integer as login_frequency,
        feature_adoption::integer as feature_adoption,
        session_depth::decimal(10,2) as session_depth
    from source
)

select * from renamed
