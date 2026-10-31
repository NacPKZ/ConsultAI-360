-- =====================================================
-- CONSULTAI 360 — PHASE 4.4
-- COPIE CLEAN VERS RECOVERED
-- =====================================================
-- Objectif :
-- 1. Conserver les donnees CLEAN intactes
-- 2. Creer une copie independante dans RECOVERED
-- 3. Verifier que les volumes sont identiques
--
-- IMPORTANT :
-- La copie a deja ete executee dans DBeaver.
-- Ne pas relancer la partie creation/copie.
-- Executer uniquement la partie VALIDATION.
-- =====================================================
-- =====================================================
-- PARTIE 1 : CREATION DU SCHEMA
-- DEJA EXECUTEE
-- =====================================================
CREATE SCHEMA IF NOT EXISTS recovered;
-- =====================================================
-- PARTIE 2 : CREATION ET COPIE DES 10 TABLES
-- DEJA EXECUTEE — NE PAS RELANCER
-- =====================================================
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
nb_lignes BIGINT;
BEGIN FOREACH t IN ARRAY tables LOOP -- Eviter d'ecraser une table existante
IF to_regclass(format('recovered.%I', t)) IS NOT NULL THEN RAISE EXCEPTION 'Table recovered.% existe deja : operation annulee',
t;
END IF;
-- Reproduire la structure de CLEAN
EXECUTE format(
    'CREATE TABLE recovered.%I
             (LIKE clean.%I INCLUDING ALL)',
    t,
    t
);
-- Copier toutes les lignes
-- en conservant les identifiants techniques
EXECUTE format(
    'INSERT INTO recovered.%I
             OVERRIDING SYSTEM VALUE
             SELECT * FROM clean.%I',
    t,
    t
);
-- Compter les lignes copiees
EXECUTE format(
    'SELECT COUNT(*) FROM recovered.%I',
    t
) INTO nb_lignes;
RAISE NOTICE 'Table recovered.% copiee : % lignes',
t,
nb_lignes;
END LOOP;
END $$;
-- =====================================================
-- PARTIE 3 : VALIDATION CLEAN VS RECOVERED
-- A EXECUTER MAINTENANT DANS DBEAVER
-- =====================================================
WITH clean_counts AS (
    SELECT 'customers' AS table_name,
        COUNT(*) AS nb
    FROM clean.customers
    UNION ALL
    SELECT 'products',
        COUNT(*)
    FROM clean.products
    UNION ALL
    SELECT 'stores',
        COUNT(*)
    FROM clean.stores
    UNION ALL
    SELECT 'employees',
        COUNT(*)
    FROM clean.employees
    UNION ALL
    SELECT 'orders',
        COUNT(*)
    FROM clean.orders
    UNION ALL
    SELECT 'order_items',
        COUNT(*)
    FROM clean.order_items
    UNION ALL
    SELECT 'payments',
        COUNT(*)
    FROM clean.payments
    UNION ALL
    SELECT 'shipments',
        COUNT(*)
    FROM clean.shipments
    UNION ALL
    SELECT 'inventory',
        COUNT(*)
    FROM clean.inventory
    UNION ALL
    SELECT 'complaints',
        COUNT(*)
    FROM clean.complaints
),
recovered_counts AS (
    SELECT 'customers' AS table_name,
        COUNT(*) AS nb
    FROM recovered.customers
    UNION ALL
    SELECT 'products',
        COUNT(*)
    FROM recovered.products
    UNION ALL
    SELECT 'stores',
        COUNT(*)
    FROM recovered.stores
    UNION ALL
    SELECT 'employees',
        COUNT(*)
    FROM recovered.employees
    UNION ALL
    SELECT 'orders',
        COUNT(*)
    FROM recovered.orders
    UNION ALL
    SELECT 'order_items',
        COUNT(*)
    FROM recovered.order_items
    UNION ALL
    SELECT 'payments',
        COUNT(*)
    FROM recovered.payments
    UNION ALL
    SELECT 'shipments',
        COUNT(*)
    FROM recovered.shipments
    UNION ALL
    SELECT 'inventory',
        COUNT(*)
    FROM recovered.inventory
    UNION ALL
    SELECT 'complaints',
        COUNT(*)
    FROM recovered.complaints
)
SELECT c.table_name,
    c.nb AS clean_rows,
    r.nb AS recovered_rows,
    r.nb - c.nb AS difference,
    CASE
        WHEN c.nb = r.nb THEN 'PASS'
        ELSE 'FAIL'
    END AS statut
FROM clean_counts c
    JOIN recovered_counts r USING (table_name)
UNION ALL
SELECT 'TOTAL',
    SUM(c.nb),
    SUM(r.nb),
    SUM(r.nb - c.nb),
    CASE
        WHEN SUM(c.nb) = SUM(r.nb) THEN 'PASS'
        ELSE 'FAIL'
    END
FROM clean_counts c
    JOIN recovered_counts r USING (table_name)
ORDER BY table_name;
