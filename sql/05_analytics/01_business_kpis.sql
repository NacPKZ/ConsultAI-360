-- ============================================================
-- CONSULTAI 360 - BUSINESS ANALYTICS & KPI
-- PHASE 4.6
-- ============================================================
-- KPI 1 : VUE GENERALE PAR SCENARIO
-- On calcule les commandes, le CA et le panier moyen
-- sans joindre directement les paiements ou lignes de vente.
SELECT scenario,
    COUNT(*) AS total_orders,
    ROUND(SUM(order_total), 2) AS revenue,
    ROUND(AVG(order_total), 2) AS average_order_value,
    COUNT(DISTINCT customer_key) AS customer_keys,
    COUNT(*) FILTER (
        WHERE date_key IS NULL
    ) AS orders_without_date
FROM dw.fact_orders
GROUP BY scenario
ORDER BY scenario;
-- KPI 2 : CHIFFRE D'AFFAIRES PAR CANAL
SELECT scenario,
    COALESCE(sales_channel, 'UNKNOWN') AS channel,
    COUNT(*) AS orders,
    ROUND(SUM(order_total), 2) AS revenue,
    ROUND(AVG(order_total), 2) AS average_order_value
FROM dw.fact_orders
GROUP BY scenario,
    COALESCE(sales_channel, 'UNKNOWN')
ORDER BY scenario,
    revenue DESC NULLS LAST;
-- KPI 3 : PERFORMANCE DES PRODUITS
-- Les montants proviennent exclusivement des lignes de vente.
SELECT f.scenario,
    p.category,
    COUNT(*) AS sales_lines,
    SUM(f.quantity) AS units_sold,
    ROUND(SUM(f.line_total), 2) AS revenue,
    COUNT(*) FILTER (
        WHERE p.is_unknown
    ) AS unknown_product_lines
FROM dw.fact_sales f
    JOIN dw.dim_products p ON p.product_key = f.product_key
GROUP BY f.scenario,
    p.category
ORDER BY f.scenario,
    revenue DESC NULLS LAST;
-- KPI 4 : PERFORMANCE DES MAGASINS
SELECT o.scenario,
    s.store_name,
    s.region,
    COUNT(*) AS orders,
    ROUND(SUM(o.order_total), 2) AS revenue,
    ROUND(AVG(o.order_total), 2) AS average_order_value
FROM dw.fact_orders o
    JOIN dw.dim_stores s ON s.store_key = o.store_key
GROUP BY o.scenario,
    s.store_name,
    s.region
ORDER BY o.scenario,
    revenue DESC NULLS LAST;
-- KPI 5 : EVOLUTION MENSUELLE
-- Les commandes sans date sont exclues de cette analyse.
-- Elles restent comptabilisees dans le KPI 1.
SELECT o.scenario,
    d.year,
    d.month,
    COUNT(*) AS orders,
    ROUND(SUM(o.order_total), 2) AS revenue
FROM dw.fact_orders o
    JOIN dw.dim_dates d ON d.date_key = o.date_key
GROUP BY o.scenario,
    d.year,
    d.month
ORDER BY o.scenario,
    d.year,
    d.month;
-- KPI 6 : FIABILITE DES DONNEES
WITH quality AS (
    SELECT o.scenario,
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (
            WHERE c.is_unknown
        ) AS unknown_customers,
        COUNT(*) FILTER (
            WHERE o.date_key IS NULL
        ) AS missing_dates
    FROM dw.fact_orders o
        JOIN dw.dim_customers c ON c.customer_key = o.customer_key
    GROUP BY o.scenario
)
SELECT scenario,
    total_orders,
    unknown_customers,
    missing_dates,
    ROUND(
        100.0 * unknown_customers / NULLIF(total_orders, 0),
        2
    ) AS unknown_customer_pct,
    ROUND(
        100.0 * missing_dates / NULLIF(total_orders, 0),
        2
    ) AS missing_date_pct
FROM quality
ORDER BY scenario;
