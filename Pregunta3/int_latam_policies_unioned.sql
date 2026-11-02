{{
    config(
        materialized='ephemeral'
    )
}}

with peru as (
    select * from {{ ref('stg_peru_policies') }}
),
chile as (
    select * from {{ ref('stg_chile_policies') }}
),
colombia as (
    select * from {{ ref('stg_colombia_policies') }}
)

select * from peru
union all
select * from chile
union all
select * from colombia