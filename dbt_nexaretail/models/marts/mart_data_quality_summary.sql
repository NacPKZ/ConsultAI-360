with customer_quality as (

    select
        scenario,
        'missing_customer' as anomaly_type,
        count(*) as total_records,
        sum(is_customer_missing) as anomaly_count
    from {{ ref('int_orders_customer_quality') }}
    group by scenario

),

product_quality as (

    select
        scenario,
        'missing_product' as anomaly_type,
        count(*) as total_records,
        sum(is_product_missing) as anomaly_count
    from {{ ref('int_order_items_product_quality') }}
    group by scenario

),

payment_quality as (

    select
        scenario,
        'missing_order_payment' as anomaly_type,
        count(*) as total_records,
        sum(is_order_missing) as anomaly_count
    from {{ ref('int_payments_order_quality') }}
    group by scenario

),

combined as (

    select * from customer_quality
    union all
    select * from product_quality
    union all
    select * from payment_quality

)

select
    scenario,
    anomaly_type,
    total_records,
    anomaly_count,
    round(
        100.0 * anomaly_count / nullif(total_records, 0),
        2
    ) as anomaly_rate_pct
from combined
