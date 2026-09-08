{{
  config(
    materialized = 'view'
  )
}}

with source as (
    select * from {{ source('raw_data', 'telco_customers') }}
),

renamed_and_cast as (
    select
        customer_id,
        gender,
        case when gender = 'Male' then 1 else 0 end as is_male,
        coalesce(senior_citizen, 0) as is_senior_citizen,
        case when partner = 'Yes' then 1 else 0 end as has_partner,
        case when dependents = 'Yes' then 1 else 0 end as has_dependents,
        coalesce(tenure, 0) as tenure_months,
        case when phone_service = 'Yes' then 1 else 0 end as has_phone_service,
        case
            when multiple_lines = 'Yes' then 'Yes'
            else 'No'
        end as multiple_lines,
        coalesce(internet_service, 'No') as internet_service,
        case when online_security = 'Yes' then 1 else 0 end as has_online_security,
        case when online_backup = 'Yes' then 1 else 0 end as has_online_backup,
        case when device_protection = 'Yes' then 1 else 0 end as has_device_protection,
        case when tech_support = 'Yes' then 1 else 0 end as has_tech_support,
        case when streaming_tv = 'Yes' then 1 else 0 end as has_streaming_tv,
        case when streaming_movies = 'Yes' then 1 else 0 end as has_streaming_movies,
        coalesce(contract, 'Month-to-month') as contract_type,
        case when paperless_billing = 'Yes' then 1 else 0 end as has_paperless_billing,
        coalesce(payment_method, 'Electronic check') as payment_method,
        cast(coalesce(monthly_charges, 0.0) as numeric(10, 2)) as monthly_charges,
        cast(coalesce(total_charges, 0.0) as numeric(10, 2)) as total_charges,
        case
            when churn = 'Yes' then 1
            when churn = 'No' then 0
            else 0
        end as churn_label,
        coalesce(ingested_at, current_timestamp) as ingested_at
    from source
)

select * from renamed_and_cast
