with source as (

    select *
    from {{ source('nexaretail_clean', 'orders') }}

),

renamed as (

    select
        clean_id,
        scenario,
        order_id,
        customer_id,
        store_id,
        order_date,
        sales_channel,
        order_status,
        order_total,
        source_file,
        source_row_number
    from source

)

select *
from renamed