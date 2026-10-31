-- =====================================================
-- CONSULTAI 360 - PHASE 4.5
-- CREATION DU DATA WAREHOUSE
-- =====================================================
CREATE SCHEMA IF NOT EXISTS dw;
-- =====================================================
-- DIMENSIONS
-- =====================================================
CREATE TABLE IF NOT EXISTS dw.dim_customers (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    city TEXT,
    region TEXT,
    registration_date DATE,
    loyalty_tier TEXT,
    is_unknown BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (scenario, customer_id)
);
CREATE TABLE IF NOT EXISTS dw.dim_products (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT,
    category TEXT,
    subcategory TEXT,
    brand TEXT,
    base_price NUMERIC(14, 2),
    unit_cost NUMERIC(14, 2),
    is_unknown BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (scenario, product_id)
);
CREATE TABLE IF NOT EXISTS dw.dim_stores (
    store_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    store_id TEXT NOT NULL,
    store_name TEXT,
    city TEXT,
    region TEXT,
    opening_date DATE,
    store_size_m2 INTEGER,
    is_unknown BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (scenario, store_id)
);
CREATE TABLE IF NOT EXISTS dw.dim_dates (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL
);
-- =====================================================
-- TABLES DE FAITS
-- =====================================================
CREATE TABLE IF NOT EXISTS dw.fact_orders (
    order_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    order_id TEXT NOT NULL,
    customer_key BIGINT NOT NULL REFERENCES dw.dim_customers(customer_key),
    store_key BIGINT NOT NULL REFERENCES dw.dim_stores(store_key),
    date_key INTEGER REFERENCES dw.dim_dates(date_key),
    sales_channel TEXT,
    order_status TEXT,
    order_total NUMERIC(14, 2),
    UNIQUE (scenario, order_id)
);
CREATE TABLE IF NOT EXISTS dw.fact_sales (
    sale_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    order_item_id TEXT,
    source_clean_id BIGINT NOT NULL,
    order_key BIGINT REFERENCES dw.fact_orders(order_key),
    product_key BIGINT NOT NULL REFERENCES dw.dim_products(product_key),
    quantity INTEGER,
    unit_price NUMERIC(14, 2),
    discount_amount NUMERIC(14, 2),
    line_total NUMERIC(14, 2),
    UNIQUE (scenario, source_clean_id)
);
CREATE TABLE IF NOT EXISTS dw.fact_payments (
    payment_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    payment_id TEXT,
    source_clean_id BIGINT NOT NULL,
    order_key BIGINT REFERENCES dw.fact_orders(order_key),
    payment_method TEXT,
    payment_status TEXT,
    payment_amount NUMERIC(14, 2),
    payment_date DATE,
    UNIQUE (scenario, source_clean_id)
);
-- =====================================================
-- VALIDATION
-- =====================================================
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'dw'
    AND table_type = 'BASE TABLE'
ORDER BY table_name;
