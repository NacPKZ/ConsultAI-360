-- =====================================================
-- CONSULTAI 360 — PHASE 4.4
-- JOURNAL D'AUDIT DES RESTAURATIONS
-- =====================================================
CREATE TABLE IF NOT EXISTS recovered.recovery_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id BIGINT NOT NULL,
    column_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    recovery_method TEXT NOT NULL,
    recovered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_recovery_audit UNIQUE (scenario, table_name, record_id, column_name)
);
-- Verification de la structure
SELECT column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'recovered'
    AND table_name = 'recovery_audit'
ORDER BY ordinal_position;
