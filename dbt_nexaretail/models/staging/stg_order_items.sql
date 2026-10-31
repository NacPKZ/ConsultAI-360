with source as (

    select *
    from {{ source('nexaretail_clean', 'order_items') }}

),

renamed as (

    select
        clean_id,
        scenario,
        order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price,
        discount_amount,
        line_total,
        source_file,
        source_row_number
    from source

)

select *
from renamed