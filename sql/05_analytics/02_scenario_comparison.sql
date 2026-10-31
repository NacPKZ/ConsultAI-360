-- ============================================================
-- CONSULTAI 360 - COMPARAISON DES SCENARIOS
-- ============================================================
-- Comparaison des KPI entre LOW, MEDIUM et CRITICAL.
-- Attention : LOW n'est pas une reference saine.
-- Les ecarts mesurent des differences entre scenarios,
-- pas necessairement la perte par rapport aux donnees originales.
WITH kpi AS (
    SELECT scenario,
        COUNT(*) AS orders,
        SUM(order_total) AS revenue,
        AVG(order_total) AS average_order_value
    FROM dw.fact_orders
    GROUP BY scenario
),
reference AS (
    SELECT revenue AS low_revenue
    FROM kpi
    WHERE scenario = 'low'
)
SELECT k.scenario,
    k.orders,
    ROUND(k.revenue, 2) AS revenue,
    ROUND(k.average_order_value, 2) AS average_order_value,
    ROUND(k.revenue - r.low_revenue, 2) AS revenue_difference_vs_low,
    ROUND(
        100.0 * (k.revenue - r.low_revenue) / NULLIF(r.low_revenue, 0),
        2
    ) AS revenue_difference_pct_vs_low
FROM kpi k
    CROSS JOIN reference r
ORDER BY CASE
        k.scenario
        WHEN 'low' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'critical' THEN 3
        ELSE 4
    END;
-- Analyse des paiements sans commande associee.
SELECT scenario,
    COUNT(*) AS total_payments,
    COUNT(*) FILTER (
        WHERE order_key IS NULL
    ) AS unmatched_payments,
    ROUND(
        SUM(payment_amount) FILTER (
            WHERE order_key IS NULL
        ),
        2
    ) AS unmatched_payment_amount,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE order_key IS NULL
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS unmatched_payment_pct
FROM dw.fact_payments
GROUP BY scenario
ORDER BY scenario;
-- Analyse du chiffre d'affaires non attribuable
-- a un client connu.
SELECT o.scenario,
    COUNT(*) FILTER (
        WHERE c.is_unknown
    ) AS unknown_customer_orders,
    ROUND(
        SUM(o.order_total) FILTER (
            WHERE c.is_unknown
        ),
        2
    ) AS revenue_without_known_customer
FROM dw.fact_orders o
    JOIN dw.dim_customers c ON c.customer_key = o.customer_key
GROUP BY o.scenario
ORDER BY o.scenario;
