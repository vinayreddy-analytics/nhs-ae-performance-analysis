/*
================================================================
NHS A&E Performance Analysis
03_regional_benchmarking.sql
Vinay Reddy Thudi | May 2026

How does each Trust compare to others in its own region?
PARTITION BY region means the rank resets for each region
so you can see the worst Trust in London vs worst in Midlands.

Data: dbo.ae_unified | nhs_ae_analysis
================================================================
*/

WITH trust_summary AS (
    SELECT
        org_code,
        org_name,
        region,
        COUNT(DISTINCT quarter_label + financial_year)      AS quarters_present,
        SUM(type1_attendances)                              AS total_type1_attendances,
        SUM(type1_over_4hr)                                 AS total_breaches,
        SUM(dta_12hr_plus)                                  AS total_12hr_waits,
        CAST(
            ROUND(
                100.0 * SUM(type1_attendances - type1_over_4hr)
                / NULLIF(SUM(type1_attendances), 0)
            , 1)
        AS DECIMAL(5,1))                                    AS overall_pct_within_4hr
    FROM dbo.ae_unified
    WHERE type1_attendances > 0
      AND type1_over_4hr IS NOT NULL
      AND region IS NOT NULL
    GROUP BY org_code, org_name, region
    HAVING COUNT(DISTINCT quarter_label + financial_year) >= 4
),

regional_stats AS (
    SELECT
        region,
        COUNT(org_code)                                     AS trust_count,
        CAST(ROUND(AVG(overall_pct_within_4hr), 1) AS DECIMAL(5,1))
                                                            AS regional_avg_pct,
        CAST(ROUND(MIN(overall_pct_within_4hr), 1) AS DECIMAL(5,1))
                                                            AS regional_worst,
        CAST(ROUND(MAX(overall_pct_within_4hr), 1) AS DECIMAL(5,1))
                                                            AS regional_best,
        SUM(total_12hr_waits)                               AS regional_12hr_waits
    FROM trust_summary
    GROUP BY region
)

SELECT
    t.org_code,
    t.org_name,
    t.region,
    t.overall_pct_within_4hr                                AS trust_pct,
    r.regional_avg_pct,

    -- How far above or below regional average
    CAST(
        ROUND(t.overall_pct_within_4hr - r.regional_avg_pct, 1)
    AS DECIMAL(5,1))                                        AS vs_regional_avg,

    t.total_12hr_waits,

    -- Rank within region (1 = worst performer)
    RANK() OVER (
        PARTITION BY t.region
        ORDER BY t.overall_pct_within_4hr ASC
    )                                                       AS rank_in_region,

    -- Rank nationally
    RANK() OVER (
        ORDER BY t.overall_pct_within_4hr ASC
    )                                                       AS national_rank,

    r.trust_count                                           AS trusts_in_region

FROM trust_summary t
JOIN regional_stats r ON t.region = r.region
ORDER BY t.region, t.overall_pct_within_4hr ASC;