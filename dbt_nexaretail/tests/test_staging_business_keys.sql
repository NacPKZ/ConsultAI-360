with business_keys as (

    select scenario, customer_id as business_id, 'customers' as table_name
    from {{ ref('stg_customers') }}

    union all

    select scenario, order_id, 'orders'
    from {{ ref('stg_orders') }}

    union all

    select scenario, order_item_id, 'order_items'
    from {{ ref('stg_order_items') }}

    union all

    select scenario, product_id, 'products'
    from {{ ref('stg_products') }}

    union all

    select scenario, payment_id, 'payments'
    from {{ ref('stg_payments') }}

    union all

    select scenario, shipment_id, 'shipments'
    from {{ ref('stg_shipments') }}

    union all

    select scenario, store_id, 'stores'
    from {{ ref('stg_stores') }}

    union all

    select scenario, employee_id, 'employees'
    from {{ ref('stg_employees') }}

    union all

    select scenario, inventory_id, 'inventory'
    from {{ ref('stg_inventory') }}

    union all

    select scenario, complaint_id, 'complaints'
    from {{ ref('stg_complaints') }}

),

violations as (

    select
        table_name,
        scenario,
        business_id,
        count(*) as nb_occurrences

    from business_keys

    group by table_name, scenario, business_id

    having count(*) > 1
        or business_id is null

)

select *
from violations
