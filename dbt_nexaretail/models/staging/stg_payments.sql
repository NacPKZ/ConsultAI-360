with source as (

    select *
    from {{ source('nexaretail_clean', 'payments') }}

),

renamed as (

    select
        clean_id,
        scenario,
        payment_id,
        order_id,
        payment_method,
        payment_status,
        payment_amount,
        payment_date,
        source_file,
        source_row_number
    from source

)

select *
from renamed