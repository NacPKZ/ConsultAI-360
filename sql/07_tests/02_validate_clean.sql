-- CONSULTAI 360
-- Contrôles d'intégrité de la couche CLEAN
WITH scenarios AS (
    SELECT DISTINCT scenario
    FROM clean.orders
),
checks AS (
    -- Commandes sans client valide
    SELECT o.scenario,
        'orders_without_customer' AS test,
        COUNT(*) AS anomalies
    FROM clean.orders o
        LEFT JOIN clean.customers c ON o.customer_id = c.customer_id
        AND o.scenario = c.scenario
    WHERE c.customer_id IS NULL
    GROUP BY o.scenario
    UNION ALL
    -- Lignes de commande sans commande valide
    SELECT i.scenario,
        'items_without_order',
        COUNT(*)
    FROM clean.order_items i
        LEFT JOIN clean.orders o ON i.order_id = o.order_id
        AND i.scenario = o.scenario
    WHERE o.order_id IS NULL
    GROUP BY i.scenario
    UNION ALL
    -- Lignes de commande sans produit valide
    SELECT i.scenario,
        'items_without_product',
        COUNT(*)
    FROM clean.order_items i
        LEFT JOIN clean.products p ON i.product_id = p.product_id
        AND i.scenario = p.scenario
    WHERE p.product_id IS NULL
    GROUP BY i.scenario
    UNION ALL
    -- Paiements sans commande valide
    SELECT p.scenario,
        'payments_without_order',
        COUNT(*)
    FROM clean.payments p
        LEFT JOIN clean.orders o ON p.order_id = o.order_id
        AND p.scenario = o.scenario
    WHERE o.order_id IS NULL
    GROUP BY p.scenario
    UNION ALL
    -- Livraisons sans commande valide
    SELECT s.scenario,
        'shipments_without_order',
        COUNT(*)
    FROM clean.shipments s
        LEFT JOIN clean.orders o ON s.order_id = o.order_id
        AND s.scenario = o.scenario
    WHERE o.order_id IS NULL
    GROUP BY s.scenario
)
SELECT s.scenario,
    c.test,
    COALESCE(c.anomalies, 0) AS anomalies,
    CASE
        WHEN COALESCE(c.anomalies, 0) = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS statut
FROM scenarios s
    JOIN checks c ON s.scenario = c.scenario
ORDER BY s.scenario,
    c.test;
-- =====================================================
-- DIAGNOSTIC : REFERENCES CLIENTS CORROMPUES
-- =====================================================
--
-- LOW      : 1 200 commandes affectées
-- MEDIUM   : 6 000 commandes affectées
-- CRITICAL : 12 000 commandes affectées
--
-- TOTAL : 19 200 commandes
--
-- Toutes les commandes ont une correspondance unique
-- dans raw.orders (scenario = 'original').
--
-- Aucune correction appliquée à ce stade.
-- Les anomalies CLEAN V2 sont conservées pour mesurer
-- la qualité réelle du nettoyage automatique.
-- =====================================================
-- DIAGNOSTIC 2 : PRODUITS INTROUVABLES
-- =====================================================
SELECT i.scenario,
    i.product_id,
    COUNT(*) AS lignes_affectees
FROM clean.order_items i
    LEFT JOIN clean.products p ON i.product_id = p.product_id
    AND i.scenario = p.scenario
WHERE p.product_id IS NULL
GROUP BY i.scenario,
    i.product_id
ORDER BY i.scenario,
    lignes_affectees DESC;
-- =====================================================
-- DIAGNOSTIC 3 : PAIEMENTS SANS COMMANDE
-- =====================================================
SELECT p.scenario,
    p.order_id,
    COUNT(*) AS paiements_affectes
FROM clean.payments p
    LEFT JOIN clean.orders o ON p.order_id = o.order_id
    AND p.scenario = o.scenario
WHERE o.order_id IS NULL
GROUP BY p.scenario,
    p.order_id
ORDER BY p.scenario,
    paiements_affectes DESC;
-- =====================================================
-- TEST 4 : RECUPERATION DES REFERENCES PRODUITS
-- =====================================================
SELECT c.scenario,
    COUNT(*) AS lignes_affectees,
    COUNT(r.raw_id) AS lignes_originales_retrouvees,
    COUNT(*) FILTER (
        WHERE r.raw_id IS NOT NULL
            AND r.product_id IS NOT NULL
            AND r.product_id <> ''
    ) AS references_recuperables
FROM clean.order_items c
    LEFT JOIN raw.order_items r ON r.scenario = 'original'
    AND r.source_row_number = c.source_row_number
WHERE c.product_id = 'BROKEN_REF_PRODUCTS'
GROUP BY c.scenario
ORDER BY c.scenario;
-- =====================================================
-- TEST 5 : RECUPERATION DES REFERENCES PAIEMENTS
-- =====================================================
SELECT c.scenario,
    COUNT(*) AS lignes_affectees,
    COUNT(r.raw_id) AS lignes_originales_retrouvees,
    COUNT(*) FILTER (
        WHERE r.raw_id IS NOT NULL
            AND r.order_id IS NOT NULL
            AND r.order_id <> ''
    ) AS references_recuperables
FROM clean.payments c
    LEFT JOIN raw.payments r ON r.scenario = 'original'
    AND r.source_row_number = c.source_row_number
WHERE c.order_id = 'BROKEN_REF_ORDERS'
GROUP BY c.scenario
ORDER BY c.scenario;
-- Vérification des rapprochements PRODUITS
SELECT c.scenario,
    COUNT(*) AS lignes,
    COUNT(*) FILTER (
        WHERE c.order_id IS NOT DISTINCT
        FROM r.order_id
    ) AS commandes_identiques,
    COUNT(*) FILTER (
        WHERE c.quantity::TEXT IS NOT DISTINCT
        FROM r.quantity
    ) AS quantites_identiques
FROM clean.order_items c
    JOIN raw.order_items r ON r.scenario = 'original'
    AND r.source_row_number = c.source_row_number
WHERE c.product_id = 'BROKEN_REF_PRODUCTS'
GROUP BY c.scenario
ORDER BY c.scenario;
-- Vérification des rapprochements PAIEMENTS
SELECT c.scenario,
    COUNT(*) AS lignes,
    COUNT(*) FILTER (
        WHERE c.payment_amount = NULLIF(TRIM(r.payment_amount), '')::NUMERIC
    ) AS montants_identiques
FROM clean.payments c
    JOIN raw.payments r ON r.scenario = 'original'
    AND r.source_row_number = c.source_row_number
WHERE c.order_id = 'BROKEN_REF_ORDERS'
GROUP BY c.scenario
ORDER BY c.scenario;
-- =====================================================
-- TEST : FIABILITE DE LA PROVENANCE
-- =====================================================
-- 1. Unicité des numéros de ligne dans les données originales
SELECT 'order_items' AS table_name,
    COUNT(*) AS total_lignes,
    COUNT(DISTINCT source_row_number) AS numeros_uniques
FROM raw.order_items
WHERE scenario = 'original'
UNION ALL
SELECT 'payments',
    COUNT(*),
    COUNT(DISTINCT source_row_number)
FROM raw.payments
WHERE scenario = 'original';
-- 2. Vérifier la cohérence des lignes de paiement
-- avec plusieurs attributs supplémentaires
SELECT c.scenario,
    COUNT(*) AS lignes,
    COUNT(*) FILTER (
        WHERE c.payment_id IS NOT DISTINCT
        FROM r.payment_id
    ) AS payment_ids_identiques,
    COUNT(*) FILTER (
        WHERE c.payment_date::TEXT IS NOT DISTINCT
        FROM r.payment_date
    ) AS dates_identiques
FROM clean.payments c
    JOIN raw.payments r ON r.scenario = 'original'
    AND r.source_row_number = c.source_row_number
WHERE c.order_id = 'BROKEN_REF_ORDERS'
GROUP BY c.scenario
ORDER BY c.scenario;
