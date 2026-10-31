-- =====================================================
-- CONSULTAI 360 - PHASE 4.5.4
-- ALIMENTATION DES TABLES DE FAITS
-- =====================================================
BEGIN;
-- 1. COMMANDES
-- Une ligne par commande et par scenario.
INSERT INTO dw.fact_orders (
        scenario,
        order_id,
        customer_key,
        store_key,
        date_key,
        sales_channel,
        order_status,
        order_total
    )
SELECT o.scenario,
    o.order_id,
    COALESCE(c.customer_key, cu.customer_key),
    COALESCE(s.store_key, su.store_key),
    d.date_key,
    o.sales_channel,
    o.order_status,
    o.order_total
FROM clean.orders o
    LEFT JOIN dw.dim_customers c ON c.scenario = o.scenario
    AND c.customer_id = o.customer_id
    AND c.is_unknown = FALSE
    LEFT JOIN dw.dim_customers cu ON cu.scenario = o.scenario
    AND cu.customer_id = '__UNKNOWN__'
    LEFT JOIN dw.dim_stores s ON s.scenario = o.scenario
    AND s.store_id = o.store_id
    AND s.is_unknown = FALSE
    LEFT JOIN dw.dim_stores su ON su.scenario = o.scenario
    AND su.store_id = '__UNKNOWN__'
    LEFT JOIN dw.dim_dates d ON d.full_date = o.order_date ON CONFLICT (scenario, order_id) DO NOTHING;
-- 2. LIGNES DE VENTE
-- Une ligne par order_item CLEAN.
INSERT INTO dw.fact_sales (
        scenario,
        order_item_id,
        source_clean_id,
        order_key,
        product_key,
        quantity,
        unit_price,
        discount_amount,
        line_total
    )
SELECT i.scenario,
    i.order_item_id,
    i.clean_id,
    o.order_key,
    COALESCE(p.product_key, pu.product_key),
    i.quantity,
    i.unit_price,
    i.discount_amount,
    i.line_total
FROM clean.order_items i
    LEFT JOIN dw.fact_orders o ON o.scenario = i.scenario
    AND o.order_id = i.order_id
    LEFT JOIN dw.dim_products p ON p.scenario = i.scenario
    AND p.product_id = i.product_id
    AND p.is_unknown = FALSE
    LEFT JOIN dw.dim_products pu ON pu.scenario = i.scenario
    AND pu.product_id = '__UNKNOWN__' ON CONFLICT (scenario, source_clean_id) DO NOTHING;
-- 3. PAIEMENTS
-- Une ligne par paiement CLEAN.
INSERT INTO dw.fact_payments (
        scenario,
        payment_id,
        source_clean_id,
        order_key,
        payment_method,
        payment_status,
        payment_amount,
        payment_date
    )
SELECT p.scenario,
    p.payment_id,
    p.clean_id,
    o.order_key,
    p.payment_method,
    p.payment_status,
    p.payment_amount,
    p.payment_date
FROM clean.payments p
    LEFT JOIN dw.fact_orders o ON o.scenario = p.scenario
    AND o.order_id = p.order_id ON CONFLICT (scenario, source_clean_id) DO NOTHING;
COMMIT;
-- =====================================================
-- VALIDATION DES VOLUMES
-- =====================================================
SELECT 'dim_customers' AS table_name,
    COUNT(*) AS total
FROM dw.dim_customers
UNION ALL
SELECT 'dim_products',
    COUNT(*)
FROM dw.dim_products
UNION ALL
SELECT 'dim_stores',
    COUNT(*)
FROM dw.dim_stores
UNION ALL
SELECT 'dim_dates',
    COUNT(*)
FROM dw.dim_dates
UNION ALL
SELECT 'fact_orders',
    COUNT(*)
FROM dw.fact_orders
UNION ALL
SELECT 'fact_sales',
    COUNT(*)
FROM dw.fact_sales
UNION ALL
SELECT 'fact_payments',
    COUNT(*)
FROM dw.fact_payments
ORDER BY table_name;
-- =====================================================
-- VALIDATION DES REFERENCES NON RESOLUES
-- =====================================================
SELECT f.scenario,
    'UNKNOWN_CUSTOMER' AS anomaly_type,
    COUNT(*) AS affected_rows
FROM dw.fact_orders f
    JOIN dw.dim_customers c ON c.customer_key = f.customer_key
WHERE c.is_unknown = TRUE
GROUP BY f.scenario
UNION ALL
SELECT f.scenario,
    'UNKNOWN_PRODUCT',
    COUNT(*)
FROM dw.fact_sales f
    JOIN dw.dim_products p ON p.product_key = f.product_key
WHERE p.is_unknown = TRUE
GROUP BY f.scenario
UNION ALL
SELECT f.scenario,
    'UNMATCHED_PAYMENT_ORDER',
    COUNT(*)
FROM dw.fact_payments f
WHERE f.order_key IS NULL
GROUP BY f.scenario
ORDER BY scenario,
    anomaly_type;
