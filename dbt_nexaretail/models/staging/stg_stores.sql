with source as (

    select *
    from {{ source('nexaretail_clean', 'stores') }}

),

renamed as (

    select
        clean_id,
        scenario,
        store_id,
        store_name,
        city,
        region,
        opening_date,
        store_size_m2,
        source_file,
        source_row_number
    from source

)

select *
from renamed