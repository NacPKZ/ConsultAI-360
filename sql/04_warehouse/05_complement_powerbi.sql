
-- ConsultAI 360 : vues complémentaires Power BI
-- Aucun changement sur les tables RAW existantes.

CREATE SCHEMA IF NOT EXISTS dw;

CREATE OR REPLACE VIEW dw.v_shipments_powerbi AS
SELECT
    scenario,
    shipment_id,
    order_id,
    carrier,
    shipping_method,
    shipping_date,
    estimated_delivery_date,
    actual_delivery_date,
    shipment_status,
    delivery_delay_days,
    is_late
FROM raw.shipments;

CREATE OR REPLACE VIEW dw.v_order_channels_powerbi AS
SELECT
    scenario,
    order_id,
    sales_channel
FROM raw.orders;

-- Contrôles des données
SELECT
    scenario,
    COUNT(*) AS nb_expeditions,
    COUNT(*) FILTER (
        WHERE shipment_id IS NULL OR TRIM(shipment_id) = ''
    ) AS ids_expedition_manquants,
    COUNT(*) - COUNT(DISTINCT shipment_id)
        AS ids_expedition_dupliques
FROM raw.shipments
GROUP BY scenario
ORDER BY scenario;

SELECT
    scenario,
    COUNT(*) AS nb_commandes,
    COUNT(*) FILTER (
        WHERE sales_channel IS NULL OR TRIM(sales_channel) = ''
    ) AS canaux_manquants,
    COUNT(*) - COUNT(DISTINCT order_id)
        AS ids_commande_dupliques
FROM raw.orders
GROUP BY scenario
ORDER BY scenario;

SELECT
    s.scenario,
    COUNT(*) AS expeditions_sans_commande
FROM raw.shipments s
LEFT JOIN raw.orders o
    ON s.scenario = o.scenario
   AND s.order_id = o.order_id
WHERE o.order_id IS NULL
GROUP BY s.scenario
ORDER BY s.scenario;


-- CONSULTAI 360 - Complément Data Warehouse
-- Table de faits logistique
-- Une expédition par shipment_id et scénario

CREATE TABLE IF NOT EXISTS dw.fact_shipments (
    shipment_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    shipment_id TEXT NOT NULL,
    order_key BIGINT,
    order_id TEXT,
    carrier TEXT,
    shipping_method TEXT,
    shipping_date DATE,
    estimated_delivery_date DATE,
    actual_delivery_date DATE,
    shipment_status TEXT,
    delivery_delay_days NUMERIC,
    is_late BOOLEAN,
    CONSTRAINT uq_fact_shipments
        UNIQUE (scenario, shipment_id)
);

-- Chargement depuis RAW.
-- La clé de commande est récupérée depuis le DW.
-- On évite les jointures directes sur raw.orders.

WITH unique_orders AS (
    SELECT
        scenario,
        order_id,
        MIN(order_key) AS order_key
    FROM dw.fact_orders
    WHERE order_id IS NOT NULL
    GROUP BY scenario, order_id
    HAVING COUNT(*) = 1
)
INSERT INTO dw.fact_shipments (
    scenario,
    shipment_id,
    order_key,
    order_id,
    carrier,
    shipping_method,
    shipping_date,
    estimated_delivery_date,
    actual_delivery_date,
    shipment_status,
    delivery_delay_days,
    is_late
)
SELECT
    s.scenario,
    s.shipment_id,
    o.order_key,
    s.order_id,
    s.carrier,
    s.shipping_method,
    CASE
        WHEN s.shipping_date ~ '^\d{4}-\d{2}-\d{2}$'
        THEN s.shipping_date::DATE
    END,
    CASE
        WHEN s.estimated_delivery_date ~ '^\d{4}-\d{2}-\d{2}$'
        THEN s.estimated_delivery_date::DATE
    END,
    CASE
        WHEN s.actual_delivery_date ~ '^\d{4}-\d{2}-\d{2}$'
        THEN s.actual_delivery_date::DATE
    END,
    s.shipment_status,
    CASE
        WHEN s.delivery_delay_days ~ '^-?\d+(\.\d+)?$'
        THEN s.delivery_delay_days::NUMERIC
    END,
    CASE
        WHEN LOWER(TRIM(s.is_late)) IN ('true','1','yes')
        THEN TRUE
        WHEN LOWER(TRIM(s.is_late)) IN ('false','0','no')
        THEN FALSE
        ELSE NULL
    END
FROM raw.shipments s
LEFT JOIN unique_orders o
    ON s.scenario = o.scenario
   AND s.order_id = o.order_id
WHERE s.shipment_id IS NOT NULL
ON CONFLICT (scenario, shipment_id) DO NOTHING;

-- Contrôles après chargement
SELECT
    scenario,
    COUNT(*) AS nb_expeditions,
    COUNT(*) FILTER (
        WHERE order_key IS NULL
    ) AS commandes_non_reliees,
    COUNT(*) FILTER (
        WHERE actual_delivery_date IS NOT NULL
    ) AS livraisons_datees,
    COUNT(*) FILTER (
        WHERE is_late = TRUE
    ) AS livraisons_en_retard
FROM dw.fact_shipments
GROUP BY scenario
ORDER BY scenario;


-- PHASE 6 - Correction des retards logistiques
-- Ne modifie pas les données RAW.

BEGIN;

UPDATE dw.fact_shipments
SET
    is_late = CASE
        WHEN actual_delivery_date IS NOT NULL
         AND estimated_delivery_date IS NOT NULL
        THEN actual_delivery_date > estimated_delivery_date
        ELSE NULL
    END,
    delivery_delay_days = CASE
        WHEN actual_delivery_date IS NOT NULL
         AND estimated_delivery_date IS NOT NULL
        THEN GREATEST(
            actual_delivery_date - estimated_delivery_date,
            0
        )
        ELSE NULL
    END;

COMMIT;

-- Validation
SELECT
    scenario,
    COUNT(*) AS expeditions,
    COUNT(*) FILTER (
        WHERE is_late = TRUE
    ) AS retards,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE is_late = TRUE)
        / NULLIF(COUNT(*) FILTER (
            WHERE actual_delivery_date IS NOT NULL
              AND estimated_delivery_date IS NOT NULL
        ), 0),
        2
    ) AS taux_retard_pct,
    COUNT(*) FILTER (
        WHERE order_key IS NULL
    ) AS commandes_non_reliees
FROM dw.fact_shipments
GROUP BY scenario
ORDER BY scenario;
