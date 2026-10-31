-- =====================================================
-- CONSULTAI 360 - PHASE 4.5
-- INSPECTION DU MODELE DIMENSIONNEL
-- =====================================================
-- 1. Colonnes des tables principales
SELECT table_name,
    ordinal_position,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'clean'
    AND table_name IN (
        'customers',
        'products',
        'stores',
        'orders',
        'order_items',
        'payments'
    )
ORDER BY table_name,
    ordinal_position;
-- 2. Verification des identifiants metier
SELECT 'customers' AS table_name,
    COUNT(*) AS total,
    COUNT(DISTINCT (scenario, customer_id)) AS ids_uniques
FROM clean.customers
UNION ALL
SELECT 'products',
    COUNT(*),
    COUNT(DISTINCT (scenario, product_id))
FROM clean.products
UNION ALL
SELECT 'stores',
    COUNT(*),
    COUNT(DISTINCT (scenario, store_id))
FROM clean.stores
UNION ALL
SELECT 'orders',
    COUNT(*),
    COUNT(DISTINCT (scenario, order_id))
FROM clean.orders;
-- 3. Verification des montants de ventes
SELECT scenario,
    COUNT(*) AS lignes,
    SUM(line_total) AS montant_lignes,
    SUM(discount_amount) AS remises
FROM clean.order_items
GROUP BY scenario
ORDER BY scenario;
-- 4. Verification des montants de commandes
SELECT scenario,
    COUNT(*) AS commandes,
    SUM(order_total) AS montant_commandes
FROM clean.orders
GROUP BY scenario
ORDER BY scenario;
