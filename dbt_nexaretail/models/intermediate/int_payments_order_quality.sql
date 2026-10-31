with payments as (

    select *
    from {{ ref('stg_payments') }}

),

orders as (

    select
        scenario,
        order_id
    from {{ ref('stg_orders') }}

),

enriched as (

    select
        p.clean_id,
        p.scenario,
        p.payment_id,
        p.order_id,
        p.payment_method,
        p.payment_status,
        p.payment_amount,
        p.payment_date,

        case
            when o.order_id is null then 1
            else 0
        end as is_order_missing

    from payments p

    left join orders o
        on p.scenario = o.scenario
        and p.order_id = o.order_id

)

select *
from enriched
