with validation as (

    select
        scenario,
        anomaly_type,
        count(*) as nb_rows,
        min(total_records) as total_records,
        min(anomaly_count) as anomaly_count,
        min(anomaly_rate_pct) as anomaly_rate_pct

    from {{ ref('mart_data_quality_summary') }}

    group by scenario, anomaly_type

),

errors as (

    select *
    from validation

    where nb_rows <> 1
       or total_records <= 0
       or anomaly_count < 0
       or anomaly_count > total_records
       or anomaly_rate_pct is distinct from round(
           100.0 * anomaly_count / nullif(total_records, 0),
           2
       )

)

select *
from errors
