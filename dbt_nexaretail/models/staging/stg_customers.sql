with source as (
    select *
    from {{ source('nexaretail_clean', 'customers') }}
),
renamed as (
    select clean_id,
        scenario,
        customer_id,
        trim(first_name) as first_name,
        trim(last_name) as last_name,
        trim(city) as city,
        trim(region) as region,
        registration_date,
        lower(trim(loyalty_tier)) as loyalty_tier,
        source_file,
        source_row_number
    from source
)
select *
from renamed
