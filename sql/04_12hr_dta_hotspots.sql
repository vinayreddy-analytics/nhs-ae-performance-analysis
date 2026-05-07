-- ============================================================
-- Query 4: 12-Hour DTA Wait Hotspots with Window Functions
-- Business question: Which Trusts have the most dangerous
-- post-admission wait times, and is it getting worse?
-- ============================================================

WITH quarterly_dta AS (
    SELECT
        org_code,
        org_name,
        region,
        financial_year,
        quarter_label,
        CASE
            WHEN financial_year = '2023-24' AND quarter_label = 'Q1' THEN 1
            WHEN financial_year = '2023-24' AND quarter_label = 'Q2' THEN 2
            WHEN financial_year = '2023-24' AND quarter_label = 'Q3' THEN 3
            WHEN financial_year = '2023-24' AND quarter_label = 'Q4' THEN 4
            WHEN financial_year = '2024-25' AND quarter_label = 'Q1' THEN 5
            WHEN financial_year = '2024-25' AND quarter_label = 'Q2' THEN 6
            WHEN financial_year = '2024-25' AND quarter_label = 'Q3 2024-25' THEN 7
            WHEN financial_year = '2024-25' AND quarter_label = 'Q4 2024-25' THEN 8
        END                                                 AS sort_order,
        type1_attendances,
        dta_12hr_plus,

        -- 12hr waits as % of Type 1 attendances
        CASE
            WHEN type1_attendances > 0
            THEN CAST(
                ROUND(100.0 * dta_12hr_plus / type1_attendances, 2)
                AS DECIMAL(6,2))
            ELSE NULL
        END                                                 AS dta_12hr_rate
    FROM dbo.ae_unified
    WHERE dta_12hr_plus IS NOT NULL
      AND type1_attendances > 0
),

trust_dta_summary AS (
    SELECT
        org_code,
        org_name,
        region,
        SUM(type1_attendances)                              AS total_type1,
        SUM(dta_12hr_plus)                                  AS total_12hr_waits,
        CAST(ROUND(AVG(dta_12hr_rate), 2) AS DECIMAL(6,2)) AS avg_12hr_rate,
        COUNT(DISTINCT sort_order)                          AS quarters_present,

        -- Trend: compare first 2 quarters vs last 2 quarters
        AVG(CASE WHEN sort_order <= 2 THEN dta_12hr_rate END) AS early_rate,
        AVG(CASE WHEN sort_order >= 5 THEN dta_12hr_rate END) AS recent_rate

    FROM quarterly_dta
    WHERE sort_order IS NOT NULL
    GROUP BY org_code, org_name, region
    HAVING COUNT(DISTINCT sort_order) >= 4
      AND SUM(dta_12hr_plus) > 0
)

SELECT TOP 30
    org_code,
    org_name,
    region,
    total_12hr_waits,
    avg_12hr_rate                                           AS avg_pct_of_attendances,
    CAST(ROUND(early_rate, 2) AS DECIMAL(6,2))              AS rate_early_quarters,
    CAST(ROUND(recent_rate, 2) AS DECIMAL(6,2))             AS rate_recent_quarters,

    -- Is the 12hr problem getting better or worse?
    CASE
        WHEN recent_rate > early_rate * 1.1 THEN 'WORSENING'
        WHEN recent_rate < early_rate * 0.9 THEN 'IMPROVING'
        ELSE 'STABLE'
    END                                                     AS trend_direction,

    -- Rank by total 12hr waits
    RANK() OVER (ORDER BY total_12hr_waits DESC)            AS rank_by_volume,

    -- Rank by rate (most concerning regardless of size)
    RANK() OVER (ORDER BY avg_12hr_rate DESC)               AS rank_by_rate

FROM trust_dta_summary
ORDER BY total_12hr_waits DESC;