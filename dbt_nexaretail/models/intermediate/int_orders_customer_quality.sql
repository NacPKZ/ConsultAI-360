with orders as (

    select *
    from {{ ref('stg_orders') }}

),

customers as (

    select
        scenario,
        customer_id
    from {{ ref('stg_customers') }}

),

enriched as (

    select
        o.clean_id,
        o.scenario,
        o.order_id,
        o.customer_id,
        o.store_id,
        o.order_date,
        o.sales_channel,
        o.order_status,
        o.order_total,

        case
            when c.customer_id is null then 1
            else 0
        end as is_customer_missing

    from orders o

    left join customers c
        on o.scenario = c.scenario
        and o.customer_id = c.customer_id

)

select *
from enriched
