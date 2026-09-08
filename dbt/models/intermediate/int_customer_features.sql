{{
  config(
    materialized = 'view'
  )
}}

with stg as (
    select * from {{ ref('stg_customers') }}
),

engineered as (
    select
        customer_id,
        is_male,
        is_senior_citizen,
        has_partner,
        has_dependents,
        tenure_months,
        has_phone_service,
        multiple_lines,
        internet_service,
        has_online_security,
        has_online_backup,
        has_device_protection,
        has_tech_support,
        has_streaming_tv,
        has_streaming_movies,
        contract_type,
        has_paperless_billing,
        payment_method,
        monthly_charges,
        total_charges,
        churn_label,

        -- Tenure grouping
        case
            when tenure_months <= 12 then '0-12_months'
            when tenure_months <= 24 then '13-24_months'
            when tenure_months <= 48 then '25-48_months'
            else '49+_months'
        end as tenure_cohort,

        -- Count of subscribed value-added services
        (
            has_phone_service +
            has_online_security +
            has_online_backup +
            has_device_protection +
            has_tech_support +
            has_streaming_tv +
            has_streaming_movies
        ) as total_services_count,

        -- Premium security pack indicator
        case
            when has_online_security = 1 and has_tech_support = 1 then 1
            else 0
        end as has_security_tech_pack,

        -- Streaming bundle indicator
        case
            when has_streaming_tv = 1 and has_streaming_movies = 1 then 1
            else 0
        end as has_streaming_bundle,

        -- Contract risk tier (Month-to-month is highest churn propensity)
        case
            when contract_type = 'Month-to-month' then 3
            when contract_type = 'One year' then 2
            when contract_type = 'Two year' then 1
            else 2
        end as contract_risk_index,

        -- Payment method risk flag (Electronic check has highest churn rate)
        case
            when payment_method = 'Electronic check' then 1
            else 0
        end as is_electronic_check_payment,

        -- Historical charges consistency ratio
        case
            when tenure_months > 0 and monthly_charges > 0
            then round(cast(total_charges / (tenure_months * monthly_charges) as numeric), 4)
            else 1.0
        end as charge_consistency_ratio,

        -- High monthly charges indicator (above median $70)
        case
            when monthly_charges >= 70.0 then 1
            else 0
        end as is_high_monthly_charge,

        ingested_at
    from stg
)

select * from engineered
