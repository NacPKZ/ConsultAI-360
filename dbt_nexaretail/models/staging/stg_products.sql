with source as (

    select *
    from {{ source('nexaretail_clean', 'products') }}

),

renamed as (

    select
        clean_id,
        scenario,
        product_id,
        product_name,
        category,
        subcategory,
        brand,
        base_price,
        unit_cost,
        source_file,
        source_row_number
    from source

)

select *
from renamed