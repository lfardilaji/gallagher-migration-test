with source as (
    select * from {{ source('raw_chile', 'policies') }}
)
select
    policy_id::varchar as policy_key,
    client_id::varchar as client_key,
    trim(policy_number) as policy_number,
    try_to_number(premium, 18, 2) as premium,
    premium is null as is_premium_missing,
    upper(trim(currency)) as currency_code,
    try_to_date(start_date, 'DD/MM/YYYY') as start_date,
    try_to_date(end_date, 'DD/MM/YYYY') as end_date,
    upper(trim(status)) as source_status,
    'CL' as country_code
from source