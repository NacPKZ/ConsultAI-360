select *
from {{ source('nexaretail_clean', 'customers') }}
