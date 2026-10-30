SELECT
    scenario,
    COUNT(*) AS total_lignes,
    COUNT(DISTINCT source_file) AS fichiers_sources
FROM (
    SELECT scenario, source_file FROM raw.customers
    UNION ALL
    SELECT scenario, source_file FROM raw.products
    UNION ALL
    SELECT scenario, source_file FROM raw.stores
    UNION ALL
    SELECT scenario, source_file FROM raw.employees
    UNION ALL
    SELECT scenario, source_file FROM raw.orders
    UNION ALL
    SELECT scenario, source_file FROM raw.order_items
    UNION ALL
    SELECT scenario, source_file FROM raw.payments
    UNION ALL
    SELECT scenario, source_file FROM raw.shipments
    UNION ALL
    SELECT scenario, source_file FROM raw.inventory
    UNION ALL
    SELECT scenario, source_file FROM raw.complaints
) AS donnees
GROUP BY scenario
ORDER BY scenario;
