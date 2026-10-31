-- CONSULTAI 360 - VALIDATION FINALE DW
-- 1. Volumes CLEAN versus DW
WITH volumes AS (
    SELECT scenario,
        'orders' AS entity,
        COUNT(*) AS clean_count
    FROM clean.orders
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'sales',
        COUNT(*)
    FROM clean.order_items
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'payments',
        COUNT(*)
    FROM clean.payments
    GROUP BY scenario
),
dw_volumes AS (
    SELECT scenario,
        'orders' AS entity,
        COUNT(*) AS dw_count
    FROM dw.fact_orders
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'sales',
        COUNT(*)
    FROM dw.fact_sales
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'payments',
        COUNT(*)
    FROM dw.fact_payments
    GROUP BY scenario
)
SELECT v.scenario,
    v.entity,
    v.clean_count,
    COALESCE(d.dw_count, 0) AS dw_count,
    CASE
        WHEN v.clean_count = d.dw_count THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM volumes v
    LEFT JOIN dw_volumes d ON d.scenario = v.scenario
    AND d.entity = v.entity
ORDER BY v.scenario,
    v.entity;
-- 2. Montants CLEAN versus DW
WITH amounts AS (
    SELECT scenario,
        'orders' AS entity,
        SUM(order_total) AS clean_amount
    FROM clean.orders
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'sales',
        SUM(line_total)
    FROM clean.order_items
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'payments',
        SUM(payment_amount)
    FROM clean.payments
    GROUP BY scenario
),
dw_amounts AS (
    SELECT scenario,
        'orders' AS entity,
        SUM(order_total) AS dw_amount
    FROM dw.fact_orders
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'sales',
        SUM(line_total)
    FROM dw.fact_sales
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'payments',
        SUM(payment_amount)
    FROM dw.fact_payments
    GROUP BY scenario
)
SELECT a.scenario,
    a.entity,
    a.clean_amount,
    d.dw_amount,
    a.clean_amount - d.dw_amount AS difference,
    CASE
        WHEN a.clean_amount IS NOT DISTINCT
        FROM d.dw_amount THEN 'PASS'
            ELSE 'FAIL'
    END AS status
FROM amounts a
    LEFT JOIN dw_amounts d ON d.scenario = a.scenario
    AND d.entity = a.entity
ORDER BY a.scenario,
    a.entity;
-- 3. Controle des scenarios dans les relations
SELECT 'orders_customers' AS relation,
    COUNT(*) FILTER (
        WHERE f.scenario <> c.scenario
    ) AS mismatches
FROM dw.fact_orders f
    JOIN dw.dim_customers c ON f.customer_key = c.customer_key
UNION ALL
SELECT 'orders_stores',
    COUNT(*) FILTER (
        WHERE f.scenario <> s.scenario
    )
FROM dw.fact_orders f
    JOIN dw.dim_stores s ON f.store_key = s.store_key
UNION ALL
SELECT 'sales_products',
    COUNT(*) FILTER (
        WHERE f.scenario <> p.scenario
    )
FROM dw.fact_sales f
    JOIN dw.dim_products p ON f.product_key = p.product_key
UNION ALL
SELECT 'sales_orders',
    COUNT(*) FILTER (
        WHERE f.scenario <> o.scenario
    )
FROM dw.fact_sales f
    JOIN dw.fact_orders o ON f.order_key = o.order_key
UNION ALL
SELECT 'payments_orders',
    COUNT(*) FILTER (
        WHERE f.scenario <> o.scenario
    )
FROM dw.fact_payments f
    JOIN dw.fact_orders o ON f.order_key = o.order_key;
-- 4. References absentes et dates non resolues
SELECT 'sales_without_order' AS check_name,
    COUNT(*) AS affected_rows
FROM dw.fact_sales
WHERE order_key IS NULL
UNION ALL
SELECT 'payments_without_order',
    COUNT(*)
FROM dw.fact_payments
WHERE order_key IS NULL
UNION ALL
SELECT 'orders_without_date',
    COUNT(*)
FROM dw.fact_orders
WHERE date_key IS NULL;
