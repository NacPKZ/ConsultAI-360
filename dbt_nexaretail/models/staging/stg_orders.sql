select *
from {{ source('nexaretail_clean', 'orders') }}
