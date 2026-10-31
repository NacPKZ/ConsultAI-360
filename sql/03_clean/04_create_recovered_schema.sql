-- =====================================================
-- CONSULTAI 360 — RESTAURATION SUPERVISEE
-- =====================================================
CREATE SCHEMA IF NOT EXISTS recovered;
-- Vérification
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name = 'recovered';
-- =====================================================
-- CONSULTAI 360 — COPIE CLEAN VERS RECOVERED
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
BEGIN FOREACH t IN ARRAY tables LOOP -- Sécurité : ne jamais écraser une table existante
IF to_regclass(format('recovered.%I', t)) IS NOT NULL THEN RAISE EXCEPTION 'Table recovered.% existe déjà : opération annulée',
t;
END IF;
-- Créer une table indépendante avec les mêmes colonnes
EXECUTE format(
    'CREATE TABLE recovered.%I
             (LIKE clean.%I INCLUDING ALL)',
    t,
    t
);
-- Copier toutes les données, identifiants compris
EXECUTE format(
    'INSERT INTO recovered.%I
             OVERRIDING SYSTEM VALUE
             SELECT * FROM clean.%I',
    t,
    t
);
-- Vérifier le nombre de lignes copiées
EXECUTE format(
    'SELECT COUNT(*) FROM recovered.%I',
    t
) INTO nb_lignes;
RAISE NOTICE 'Table recovered.% copiée : % lignes',
t,
nb_lignes;
END LOOP;
END $$;
