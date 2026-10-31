with source as (

    select *
    from {{ source('nexaretail_clean', 'complaints') }}

),

renamed as (

    select
        clean_id,
        scenario,
        complaint_id,
        order_id,
        customer_id,
        complaint_date,
        complaint_reason,
        severity,
        complaint_status,
        resolution_date,
        satisfaction_score,
        source_file,
        source_row_number
    from source

)

select *
from renamed