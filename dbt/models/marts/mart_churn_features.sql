{{
  config(
    materialized = 'table'
  )
}}

with int_features as (
    select * from {{ ref('int_customer_features') }}
),

final_mart as (
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
        tenure_cohort,
        total_services_count,
        has_security_tech_pack,
        has_streaming_bundle,
        contract_risk_index,
        is_electronic_check_payment,
        charge_consistency_ratio,
        is_high_monthly_charge,
        churn_label,
        ingested_at,
        current_timestamp as feature_created_at
    from int_features
)

select * from final_mart
