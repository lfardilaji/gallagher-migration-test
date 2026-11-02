{{
    config(
        materialized='table',
        schema='ANALYTICS',
        tags=['finance', 'latam', 'policies']
    )
}}

select
    {{ dbt_utils.generate_surrogate_key(['country_code', 'policy_key']) }} as policy_sk,
    policy_key as policy_id,
    client_id,
    policy_number,
    country_code,
    premium,
    currency,
    start_date,
    end_date,
    policy_status,
    current_timestamp() as dbt_updated_at
from {{ ref('int_latam_policies_unioned') }}