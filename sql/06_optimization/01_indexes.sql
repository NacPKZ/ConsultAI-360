-- CONSULTAI 360 - PHASE 4.7
-- INDEXATION DU DATA WAREHOUSE
-- Recherche des commandes par scenario et date
CREATE INDEX IF NOT EXISTS idx_dw_orders_scenario_date ON dw.fact_orders (scenario, date_key);
-- Analyse des clients
CREATE INDEX IF NOT EXISTS idx_dw_orders_customer ON dw.fact_orders (customer_key);
-- Analyse des magasins
CREATE INDEX IF NOT EXISTS idx_dw_orders_store ON dw.fact_orders (store_key);
-- Ventes par produit
CREATE INDEX IF NOT EXISTS idx_dw_sales_product ON dw.fact_sales (product_key);
-- Ventes par commande
CREATE INDEX IF NOT EXISTS idx_dw_sales_order ON dw.fact_sales (order_key);
-- Paiements par commande
CREATE INDEX IF NOT EXISTS idx_dw_payments_order ON dw.fact_payments (order_key);
-- Statistiques pour l'optimiseur PostgreSQL
ANALYZE dw.fact_orders;
ANALYZE dw.fact_sales;
ANALYZE dw.fact_payments;
ANALYZE dw.dim_customers;
ANALYZE dw.dim_products;
ANALYZE dw.dim_stores;
ANALYZE dw.dim_dates;
-- VERIFICATION DES INDEX
SELECT tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'dw'
ORDER BY tablename,
    indexname;
