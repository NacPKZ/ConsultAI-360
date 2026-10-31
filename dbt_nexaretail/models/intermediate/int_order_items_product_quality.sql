with order_items as (

    select *
    from {{ ref('stg_order_items') }}

),

products as (

    select
        scenario,
        product_id
    from {{ ref('stg_products') }}

),

enriched as (

    select
        oi.clean_id,
        oi.scenario,
        oi.order_item_id,
        oi.order_id,
        oi.product_id,
        oi.quantity,
        oi.unit_price,
        oi.discount_amount,
        oi.line_total,

        case
            when p.product_id is null then 1
            else 0
        end as is_product_missing

    from order_items oi

    left join products p
        on oi.scenario = p.scenario
        and oi.product_id = p.product_id

)

select *
from enriched
