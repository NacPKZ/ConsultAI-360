with original_reference as (

    select
        round(sum(order_total::numeric), 2) as original_revenue

    from {{ source('nexaretail_raw', 'orders') }}

    where scenario = 'original'

),

revenue_by_scenario as (

    select
        scenario,
        count(*) as total_orders,
        count(order_total) as orders_with_amount,
        count(*) - count(order_total) as orders_missing_amount,
        round(sum(order_total), 2) as observed_revenue

    from {{ ref('stg_orders') }}

    group by scenario

),

final as (

    select
        s.scenario,
        s.total_orders,
        s.orders_with_amount,
        s.orders_missing_amount,
        r.original_revenue,
        s.observed_revenue,

        round(
            s.observed_revenue - r.original_revenue,
            2
        ) as revenue_gap_eur,

        round(
            100.0 * (s.observed_revenue - r.original_revenue)
            / nullif(r.original_revenue, 0),
            2
        ) as revenue_gap_pct,

        round(
            100.0 * s.orders_missing_amount
            / nullif(s.total_orders, 0),
            2
        ) as missing_amount_rate_pct

    from revenue_by_scenario s

    cross join original_reference r

)

select *
from final
