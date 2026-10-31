select *
from {{ source('nexaretail_clean', 'order_items') }}
