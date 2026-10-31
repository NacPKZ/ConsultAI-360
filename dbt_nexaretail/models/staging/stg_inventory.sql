with source as (

    select *
    from {{ source('nexaretail_clean', 'inventory') }}

),

renamed as (

    select
        clean_id,
        scenario,
        inventory_id,
        store_id,
        product_id,
        stock_quantity,
        reorder_point,
        reorder_quantity,
        stock_status,
        last_restock_date,
        source_file,
        source_row_number
    from source

)

select *
from renamed