-- =====================================================
-- CONSULTAI 360 - FINAL DW TESTS
-- =====================================================
WITH tests AS (
    -- Nombre de commandes
    SELECT 'FACT_ORDERS_COUNT' AS test_name,
        COUNT(*) = 360000 AS passed
    FROM dw.fact_orders
    UNION ALL
    -- Nombre de lignes de vente
    SELECT 'FACT_SALES_COUNT',
        COUNT(*) = 818859
    FROM dw.fact_sales
    UNION ALL
    -- Nombre de paiements
    SELECT 'FACT_PAYMENTS_COUNT',
        COUNT(*) = 376503
    FROM dw.fact_payments
    UNION ALL
    -- Aucun produit sans dimension
    SELECT 'PRODUCT_KEY_NOT_NULL',
        COUNT(*) = 0
    FROM dw.fact_sales
    WHERE product_key IS NULL
    UNION ALL
    -- Aucune commande sans client technique
    SELECT 'CUSTOMER_KEY_NOT_NULL',
        COUNT(*) = 0
    FROM dw.fact_orders
    WHERE customer_key IS NULL
    UNION ALL
    -- Aucun melange de scenario pour les produits
    SELECT 'PRODUCT_SCENARIO_MATCH',
        COUNT(*) = 0
    FROM dw.fact_sales f
        JOIN dw.dim_products p ON p.product_key = f.product_key
    WHERE f.scenario <> p.scenario
    UNION ALL
    -- Paiements non rattaches attendus
    SELECT 'UNMATCHED_PAYMENTS',
        COUNT(*) = 20080
    FROM dw.fact_payments
    WHERE order_key IS NULL
    UNION ALL
    -- Dates manquantes attendues
    SELECT 'MISSING_ORDER_DATES',
        COUNT(*) = 19200
    FROM dw.fact_orders
    WHERE date_key IS NULL
    UNION ALL
    -- Membres clients inconnus
    SELECT 'UNKNOWN_CUSTOMERS',
        COUNT(*) = 19200
    FROM dw.fact_orders o
        JOIN dw.dim_customers c ON c.customer_key = o.customer_key
    WHERE c.is_unknown = TRUE
    UNION ALL
    -- Membres produits inconnus
    SELECT 'UNKNOWN_PRODUCTS',
        COUNT(*) = 43673
    FROM dw.fact_sales f
        JOIN dw.dim_products p ON p.product_key = f.product_key
    WHERE p.is_unknown = TRUE
)
SELECT test_name,
    CASE
        WHEN passed THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM tests
ORDER BY test_name;
