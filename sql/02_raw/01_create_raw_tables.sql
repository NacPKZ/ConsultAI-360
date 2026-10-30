-- CONSULTAI 360 - PHASE 4.2
-- Creation des tables RAW
-- Colonnes metier conservees en TEXT

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.customers (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "customer_id" TEXT,
    "first_name" TEXT,
    "last_name" TEXT,
    "city" TEXT,
    "region" TEXT,
    "registration_date" TEXT,
    "loyalty_tier" TEXT
);

CREATE TABLE IF NOT EXISTS raw.products (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "product_id" TEXT,
    "product_name" TEXT,
    "category" TEXT,
    "subcategory" TEXT,
    "brand" TEXT,
    "base_price" TEXT,
    "unit_cost" TEXT
);

CREATE TABLE IF NOT EXISTS raw.stores (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "store_id" TEXT,
    "store_name" TEXT,
    "city" TEXT,
    "region" TEXT,
    "opening_date" TEXT,
    "store_size_m2" TEXT
);

CREATE TABLE IF NOT EXISTS raw.employees (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "employee_id" TEXT,
    "store_id" TEXT,
    "department" TEXT,
    "job_title" TEXT,
    "hire_date" TEXT
);

CREATE TABLE IF NOT EXISTS raw.orders (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "order_id" TEXT,
    "customer_id" TEXT,
    "store_id" TEXT,
    "order_date" TEXT,
    "sales_channel" TEXT,
    "order_status" TEXT,
    "order_total" TEXT
);

CREATE TABLE IF NOT EXISTS raw.order_items (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "order_item_id" TEXT,
    "order_id" TEXT,
    "product_id" TEXT,
    "quantity" TEXT,
    "unit_price" TEXT,
    "discount_amount" TEXT,
    "line_total" TEXT
);

CREATE TABLE IF NOT EXISTS raw.payments (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "payment_id" TEXT,
    "order_id" TEXT,
    "payment_method" TEXT,
    "payment_status" TEXT,
    "payment_amount" TEXT,
    "payment_date" TEXT
);

CREATE TABLE IF NOT EXISTS raw.shipments (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "shipment_id" TEXT,
    "order_id" TEXT,
    "carrier" TEXT,
    "shipping_method" TEXT,
    "shipping_date" TEXT,
    "estimated_delivery_date" TEXT,
    "actual_delivery_date" TEXT,
    "shipment_status" TEXT,
    "delivery_delay_days" TEXT,
    "is_late" TEXT
);

CREATE TABLE IF NOT EXISTS raw.inventory (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "inventory_id" TEXT,
    "store_id" TEXT,
    "product_id" TEXT,
    "stock_quantity" TEXT,
    "reorder_point" TEXT,
    "reorder_quantity" TEXT,
    "stock_status" TEXT,
    "last_restock_date" TEXT
);

CREATE TABLE IF NOT EXISTS raw.complaints (
    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number BIGINT NOT NULL,
    "complaint_id" TEXT,
    "order_id" TEXT,
    "customer_id" TEXT,
    "complaint_date" TEXT,
    "complaint_reason" TEXT,
    "severity" TEXT,
    "complaint_status" TEXT,
    "resolution_date" TEXT,
    "satisfaction_score" TEXT
);
