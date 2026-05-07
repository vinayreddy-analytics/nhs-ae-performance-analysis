-- ============================================================
-- Query 1: Trust Performance Ranking by 4-Hour Standard
-- Business question: Which Trusts are consistently failing
-- the 95% target, and by how much?
-- ============================================================

WITH trust_performance AS (
    SELECT
        org_code,
        org_name,
        financial_year,
        quarter_label,

        -- Calculate 4hr performance from raw numbers
        -- More reliable than the pre-calculated percentage
        -- since monthly CSV data doesn't include it
        type1_attendances,
        type1_over_4hr,

        CASE
            WHEN type1_attendances > 0
            THEN ROUND(
                100.0 * (type1_attendances - type1_over_4hr)
                / type1_attendances, 1)
            ELSE NULL
        END AS pct_within_4hr,

        dta_12hr_plus

    FROM dbo.ae_unified
    WHERE type1_attendances > 0
      AND type1_attendances IS NOT NULL
),

-- Average performance across all 8 quarters per Trust
trust_avg AS (
    SELECT
        org_code,
        org_name,
        COUNT(DISTINCT quarter_label + financial_year)  AS quarters_present,
        ROUND(AVG(pct_within_4hr), 1)                  AS avg_pct_within_4hr,
        ROUND(MIN(pct_within_4hr), 1)                  AS worst_quarter_pct,
        ROUND(MAX(pct_within_4hr), 1)                  AS best_quarter_pct,
        SUM(type1_attendances)                          AS total_type1_attendances,
        SUM(dta_12hr_plus)                              AS total_12hr_waits
    FROM trust_performance
    GROUP BY org_code, org_name
    HAVING COUNT(DISTINCT quarter_label + financial_year) >= 4
       AND AVG(pct_within_4hr) IS NOT NULL
)

SELECT
    org_code,
    org_name,
    quarters_present,
    avg_pct_within_4hr,
    worst_quarter_pct,
    best_quarter_pct,
    total_type1_attendances,
    total_12hr_waits,

    -- RAG status against 95% standard
    CASE
        WHEN avg_pct_within_4hr >= 95 THEN 'GREEN'
        WHEN avg_pct_within_4hr >= 85 THEN 'AMBER'
        ELSE 'RED'
    END AS rag_status,

    -- Rank worst to best
    RANK() OVER (ORDER BY avg_pct_within_4hr ASC) AS performance_rank

FROM trust_avg
ORDER BY avg_pct_within_4hr ASC;