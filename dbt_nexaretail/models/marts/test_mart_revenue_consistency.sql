select
    scenario,
    original_revenue,
    observed_revenue,
    revenue_gap_eur,
    revenue_gap_pct,
    missing_amount_rate_pct

from {{ ref('mart_revenue_impact') }}

where original_revenue <= 0
   or observed_revenue < 0

   or revenue_gap_eur is distinct from
      round(observed_revenue - original_revenue, 2)

   or revenue_gap_pct is distinct from
      round(
          100.0 * (observed_revenue - original_revenue)
          / nullif(original_revenue, 0),
          2
      )

   or missing_amount_rate_pct is distinct from
      round(
          100.0 * orders_missing_amount
          / nullif(total_orders, 0),
          2
      )

   or orders_with_amount + orders_missing_amount <> total_orders

   or orders_missing_amount < 0
   or orders_with_amount < 0
