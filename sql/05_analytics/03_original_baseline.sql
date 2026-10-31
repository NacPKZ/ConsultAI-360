-- CONSULTAI 360 - BASELINE ORIGINAL VS SCENARIOS
-- Le RAW contient des montants TEXT.
-- On controle d'abord leur format avant conversion.
SELECT COUNT(*) AS original_orders,
    COUNT(*) FILTER (
        WHERE order_total IS NULL
            OR TRIM(order_total) = ''
    ) AS missing_amounts,
    COUNT(*) FILTER (
        WHERE order_total IS NOT NULL
            AND TRIM(order_total) <> ''
            AND TRIM(order_total) !~ '^[+-]?[0-9]+(\.[0-9]+)?$'
    ) AS invalid_amounts
FROM raw.orders
WHERE scenario = 'original';
-- Comparaison des montants uniquement si les formats
-- sont valides (controle precedent).
WITH baseline AS (
    SELECT COUNT(*) AS orders,
        SUM(TRIM(order_total)::NUMERIC) AS revenue
    FROM raw.orders
    WHERE scenario = 'original'
        AND TRIM(order_total) ~ '^[+-]?[0-9]+(\.[0-9]+)?$'
),
scenarios AS (
    SELECT scenario,
        COUNT(*) AS orders,
        SUM(order_total) AS revenue
    FROM dw.fact_orders
    GROUP BY scenario
)
SELECT s.scenario,
    b.orders AS original_orders,
    s.orders AS scenario_orders,
    ROUND(b.revenue, 2) AS original_revenue,
    ROUND(s.revenue, 2) AS scenario_revenue,
    ROUND(s.revenue - b.revenue, 2) AS difference_eur,
    ROUND(
        100 * (s.revenue - b.revenue) / NULLIF(b.revenue, 0),
        2
    ) AS difference_pct
FROM scenarios s
    CROSS JOIN baseline b
ORDER BY CASE
        s.scenario
        WHEN 'low' THEN 1
        WHEN 'medium' THEN 2
        WHEN 'critical' THEN 3
    END;
