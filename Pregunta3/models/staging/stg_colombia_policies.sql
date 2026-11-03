select
    policy_id as policy_key,
    client_id,
    policy_number,
    try_to_number(premium, 18, 2) as premium,
    premium is null as is_premium_missing,
    upper(currency) as currency,
    try_to_date(start_date, 'DD/MM/YYYY') as start_date,
    try_to_date(end_date, 'DD/MM/YYYY') as end_date,
    lower(status) as policy_status,
    'CO' as country_code
from {{ source('raw_colombia', 'policies') }}