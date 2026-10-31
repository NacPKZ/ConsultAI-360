-- =====================================================
-- CONSULTAI 360 - PHASE 4.5.3
-- ALIMENTATION DES DIMENSIONS
-- =====================================================
-- 1. CLIENTS
INSERT INTO dw.dim_customers (
        scenario,
        customer_id,
        first_name,
        last_name,
        city,
        region,
        registration_date,
        loyalty_tier
    )
SELECT scenario,
    customer_id,
    first_name,
    last_name,
    city,
    region,
    registration_date,
    loyalty_tier
FROM clean.customers ON CONFLICT (scenario, customer_id) DO NOTHING;
-- 2. PRODUITS
INSERT INTO dw.dim_products (
        scenario,
        product_id,
        product_name,
        category,
        subcategory,
        brand,
        base_price,
        unit_cost
    )
SELECT scenario,
    product_id,
    product_name,
    category,
    subcategory,
    brand,
    base_price,
    unit_cost
FROM clean.products ON CONFLICT (scenario, product_id) DO NOTHING;
-- 3. MAGASINS
INSERT INTO dw.dim_stores (
        scenario,
        store_id,
        store_name,
        city,
        region,
        opening_date,
        store_size_m2
    )
SELECT scenario,
    store_id,
    store_name,
    city,
    region,
    opening_date,
    store_size_m2
FROM clean.stores ON CONFLICT (scenario, store_id) DO NOTHING;
-- 4. MEMBRES INCONNUS
-- On utilise un identifiant reserve par scenario.
-- Aucune transaction n'est supprimee.
INSERT INTO dw.dim_customers (
        scenario,
        customer_id,
        first_name,
        is_unknown
    )
SELECT s.scenario,
    '__UNKNOWN__',
    'Client inconnu',
    TRUE
FROM (
        SELECT DISTINCT scenario
        FROM clean.orders
    ) s ON CONFLICT (scenario, customer_id) DO NOTHING;
INSERT INTO dw.dim_products (
        scenario,
        product_id,
        product_name,
        is_unknown
    )
SELECT s.scenario,
    '__UNKNOWN__',
    'Produit inconnu',
    TRUE
FROM (
        SELECT DISTINCT scenario
        FROM clean.order_items
    ) s ON CONFLICT (scenario, product_id) DO NOTHING;
INSERT INTO dw.dim_stores (
        scenario,
        store_id,
        store_name,
        is_unknown
    )
SELECT s.scenario,
    '__UNKNOWN__',
    'Magasin inconnu',
    TRUE
FROM (
        SELECT DISTINCT scenario
        FROM clean.orders
    ) s ON CONFLICT (scenario, store_id) DO NOTHING;
-- 5. DIMENSION DATES
-- Toutes les dates disponibles dans les commandes.
-- Les dates NULL seront gerees dans les faits.
INSERT INTO dw.dim_dates (
        date_key,
        full_date,
        year,
        quarter,
        month,
        day
    )
SELECT DISTINCT TO_CHAR(order_date, 'YYYYMMDD')::INTEGER,
    order_date,
    EXTRACT(
        YEAR
        FROM order_date
    )::INTEGER,
    EXTRACT(
        QUARTER
        FROM order_date
    )::INTEGER,
    EXTRACT(
        MONTH
        FROM order_date
    )::INTEGER,
    EXTRACT(
        DAY
        FROM order_date
    )::INTEGER
FROM clean.orders
WHERE order_date IS NOT NULL ON CONFLICT (date_key) DO NOTHING;
-- =====================================================
-- VALIDATION
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
ORDER BY table_name;
-- Vérifier les membres inconnus
SELECT 'customers' AS dimension,
    scenario,
    COUNT(*) AS unknown_members
FROM dw.dim_customers
WHERE is_unknown = TRUE
GROUP BY scenario
UNION ALL
SELECT 'products',
    scenario,
    COUNT(*)
FROM dw.dim_products
WHERE is_unknown = TRUE
GROUP BY scenario
UNION ALL
SELECT 'stores',
    scenario,
    COUNT(*)
FROM dw.dim_stores
WHERE is_unknown = TRUE
GROUP BY scenario
ORDER BY dimension,
    scenario;
