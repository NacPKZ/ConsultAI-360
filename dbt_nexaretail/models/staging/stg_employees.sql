with source as (

    select *
    from {{ source('nexaretail_clean', 'employees') }}

),

renamed as (

    select
        clean_id,
        scenario,
        employee_id,
        store_id,
        department,
        job_title,
        hire_date,
        source_file,
        source_row_number
    from source

)

select *
from renamed