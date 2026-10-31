-- =====================================================
-- CONSULTAI 360 — PHASE 4.4
-- CREATION DES TABLES CLEAN
-- =====================================================
CREATE SCHEMA IF NOT EXISTS clean;
DO $$
DECLARE t TEXT;
tables TEXT [] := ARRAY [
        'customers',
        'products',
        'stores',
        'employees',
        'orders',
        'order_items',
        'payments',
        'shipments',
        'inventory',
        'complaints'
    ];
column_definitions TEXT;
BEGIN FOREACH t IN ARRAY tables LOOP
SELECT string_agg(
        format(
            '%I %s',
            column_name,
            CASE
                WHEN column_name IN (
                    'registration_date',
                    'opening_date',
                    'hire_date',
                    'order_date',
                    'payment_date',
                    'shipping_date',
                    'estimated_delivery_date',
                    'actual_delivery_date',
                    'last_restock_date',
                    'complaint_date',
                    'resolution_date'
                ) THEN 'DATE'
                WHEN column_name IN (
                    'base_price',
                    'unit_cost',
                    'order_total',
                    'unit_price',
                    'discount_amount',
                    'line_total',
                    'payment_amount',
                    'delivery_delay_days',
                    'is_late',
                    'satisfaction_score'
                ) THEN 'NUMERIC(14,2)'
                WHEN column_name IN (
                    'store_size_m2',
                    'quantity',
                    'stock_quantity',
                    'reorder_point',
                    'reorder_quantity'
                ) THEN 'INTEGER'
                ELSE 'TEXT'
            END
        ),
        ', '
        ORDER BY ordinal_position
    ) INTO column_definitions
FROM information_schema.columns
WHERE table_schema = 'raw'
    AND table_name = t
    AND column_name NOT IN (
        'raw_id',
        'scenario',
        'source_file',
        'source_row_number'
    );
IF column_definitions IS NULL THEN RAISE EXCEPTION 'Table RAW introuvable : %',
t;
END IF;
EXECUTE format(
    'CREATE TABLE IF NOT EXISTS clean.%I (
                clean_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                scenario TEXT NOT NULL,
                source_file TEXT NOT NULL,
                source_row_number BIGINT NOT NULL,
                %s
            )',
    t,
    column_definitions
);
RAISE NOTICE 'Table CLEAN créée : %',
t;
END LOOP;
END $$;
