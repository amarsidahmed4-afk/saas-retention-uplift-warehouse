with source as (
    select * from {{ ref('stripe_subscriptions') }}
),

renamed as (
    select
        account_id::varchar as account_id,
        arr::decimal(10,2) as arr,
        plan_tier::varchar as plan_tier,
        seats::integer as seats,
        billing_interval::varchar as billing_interval,
        churned::integer as is_churned
    from source
)

select * from renamed
