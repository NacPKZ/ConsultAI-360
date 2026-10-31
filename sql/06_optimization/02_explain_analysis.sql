-- CONSULTAI 360 - ANALYSE DES PERFORMANCES
-- Requete 1 : analyse mensuelle
EXPLAIN (ANALYZE, BUFFERS)
SELECT o.scenario,
    d.year,
    d.month,
    SUM(o.order_total) AS revenue
FROM dw.fact_orders o
    JOIN dw.dim_dates d ON d.date_key = o.date_key
GROUP BY o.scenario,
    d.year,
    d.month;
-- Requete 2 : chiffre d'affaires par produit
EXPLAIN (ANALYZE, BUFFERS)
SELECT f.scenario,
    p.category,
    SUM(f.line_total) AS revenue
FROM dw.fact_sales f
    JOIN dw.dim_products p ON p.product_key = f.product_key
GROUP BY f.scenario,
    p.category;
-- Requete 3 : commandes d'un scenario
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*),
    SUM(order_total)
FROM dw.fact_orders
WHERE scenario = 'critical'
    AND date_key IS NOT NULL;
