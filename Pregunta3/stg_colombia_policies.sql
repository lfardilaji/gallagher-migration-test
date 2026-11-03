select
    policy_id as policy_key,
    client_id,
    policy_number,
    coalesce(premium, 0) as premium,
    upper(currency) as currency,
    try_to_date(start_date, 'DD/MM/YYYY') as start_date,
    try_to_date(end_date, 'DD/MM/YYYY') as end_date,
    lower(status) as policy_status,
    'CO' as country_code
from {{ source('raw_colombia', 'policies') }}