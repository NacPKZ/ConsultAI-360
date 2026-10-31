-- =====================================================
-- CONSULTAI 360 - PHASE 4.4
-- VALIDATION FINALE DE LA COUCHE CLEAN
-- =====================================================
-- TEST 1 : Volumes par scenario
WITH volumes AS (
    SELECT scenario,
        'customers' AS table_name,
        COUNT(*) AS nb
    FROM clean.customers
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'products',
        COUNT(*)
    FROM clean.products
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'orders',
        COUNT(*)
    FROM clean.orders
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'order_items',
        COUNT(*)
    FROM clean.order_items
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'payments',
        COUNT(*)
    FROM clean.payments
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'stores',
        COUNT(*)
    FROM clean.stores
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'employees',
        COUNT(*)
    FROM clean.employees
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'shipments',
        COUNT(*)
    FROM clean.shipments
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'inventory',
        COUNT(*)
    FROM clean.inventory
    GROUP BY scenario
    UNION ALL
    SELECT scenario,
        'complaints',
        COUNT(*)
    FROM clean.complaints
    GROUP BY scenario
)
SELECT scenario,
    SUM(nb) AS total_lignes,
    COUNT(*) AS tables_presentes,
    CASE
        WHEN SUM(nb) = 1006394
        AND COUNT(*) = 10 THEN 'PASS'
        ELSE 'FAIL'
    END AS statut
FROM volumes
GROUP BY scenario
ORDER BY scenario;
-- TEST 2 : Doublons et identifiants manquants
SELECT scenario,
    COUNT(*) AS total_commandes,
    COUNT(DISTINCT order_id) AS commandes_uniques,
    COUNT(*) - COUNT(DISTINCT order_id) AS doublons_ou_identifiants_manquants,
    COUNT(*) FILTER (
        WHERE order_id IS NULL
            OR TRIM(order_id) = ''
    ) AS identifiants_manquants
FROM clean.orders
GROUP BY scenario
ORDER BY scenario;
-- TEST 3 : References clients invalides
SELECT o.scenario,
    'CUSTOMER_REFERENCE' AS controle,
    COUNT(*) AS anomalies
FROM clean.orders o
WHERE NOT EXISTS (
        SELECT 1
        FROM clean.customers c
        WHERE c.scenario = o.scenario
            AND c.customer_id = o.customer_id
    )
GROUP BY o.scenario
UNION ALL
-- TEST 4 : References produits invalides
SELECT i.scenario,
    'PRODUCT_REFERENCE',
    COUNT(*)
FROM clean.order_items i
WHERE NOT EXISTS (
        SELECT 1
        FROM clean.products p
        WHERE p.scenario = i.scenario
            AND p.product_id = i.product_id
    )
GROUP BY i.scenario
UNION ALL
-- TEST 5 : References commandes invalides
SELECT p.scenario,
    'PAYMENT_ORDER_REFERENCE',
    COUNT(*)
FROM clean.payments p
WHERE NOT EXISTS (
        SELECT 1
        FROM clean.orders o
        WHERE o.scenario = p.scenario
            AND o.order_id = p.order_id
    )
GROUP BY p.scenario
ORDER BY scenario,
    controle;
