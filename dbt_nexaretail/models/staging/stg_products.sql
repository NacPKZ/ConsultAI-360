select *
from {{ source('nexaretail_clean', 'products') }}
