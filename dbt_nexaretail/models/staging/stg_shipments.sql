with source as (

    select *
    from {{ source('nexaretail_clean', 'shipments') }}

),

renamed as (

    select
        clean_id,
        scenario,
        shipment_id,
        order_id,
        carrier,
        shipping_method,
        shipping_date,
        estimated_delivery_date,
        actual_delivery_date,
        shipment_status,
        delivery_delay_days,
        is_late,
        source_file,
        source_row_number
    from source

)

select *
from renamed