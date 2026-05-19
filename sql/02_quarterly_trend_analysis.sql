/*
================================================================
NHS A&E Performance Analysis
02_quarterly_trend_analysis.sql
Vinay Reddy Thudi | May 2026

Is performance getting better or worse over time?
LAG() gives us the previous quarter to calculate change.
The seasonal dip in Q3 every year shows up clearly here.

Data: dbo.ae_unified | nhs_ae_analysis
================================================================
*/

WITH quarterly_national AS (
    SELECT
        financial_year,
        quarter_label,

        -- Create a sort key so quarters display in correct order
        CASE
            WHEN financial_year = '2023-24' AND quarter_label = 'Q1' THEN 1
            WHEN financial_year = '2023-24' AND quarter_label = 'Q2' THEN 2
            WHEN financial_year = '2023-24' AND quarter_label = 'Q3' THEN 3
            WHEN financial_year = '2023-24' AND quarter_label = 'Q4' THEN 4
            WHEN financial_year = '2024-25' AND quarter_label = 'Q1' THEN 5
            WHEN financial_year = '2024-25' AND quarter_label = 'Q2' THEN 6
            WHEN financial_year = '2024-25' AND quarter_label = 'Q3 2024-25' THEN 7
            WHEN financial_year = '2024-25' AND quarter_label = 'Q4 2024-25' THEN 8
        END AS sort_order,

        COUNT(DISTINCT org_code)            AS active_trusts,
        SUM(type1_attendances)              AS national_type1_attendances,
        SUM(type1_over_4hr)                 AS national_type1_breaches,
        SUM(dta_12hr_plus)                  AS national_12hr_waits,
        SUM(total_emergency_admissions)     AS national_emergency_admissions,

        -- National 4hr performance
        CAST(
            ROUND(100.0 * SUM(type1_attendances - type1_over_4hr)
            / NULLIF(SUM(type1_attendances), 0), 1)
        AS DECIMAL(5,1))                    AS national_pct_within_4hr,

        -- How many Trusts hitting 95% target this quarter
        SUM(CASE
            WHEN type1_attendances > 0
             AND 100.0 * (type1_attendances - type1_over_4hr)
                 / type1_attendances >= 95
            THEN 1 ELSE 0
        END)                                AS trusts_meeting_target

    FROM dbo.ae_unified
    WHERE type1_attendances > 0
      AND type1_over_4hr IS NOT NULL
    GROUP BY financial_year, quarter_label
),

-- Add quarter-on-quarter change
trend AS (
    SELECT
        *,
        LAG(national_pct_within_4hr) OVER (ORDER BY sort_order)
            AS prev_quarter_pct,
        LAG(national_12hr_waits) OVER (ORDER BY sort_order)
            AS prev_quarter_12hr_waits
    FROM quarterly_national
)

SELECT
    financial_year,
    quarter_label,
    active_trusts,
    national_type1_attendances,
    national_pct_within_4hr,
    national_pct_within_4hr - prev_quarter_pct
        AS pct_change_vs_prev_quarter,
    national_12hr_waits,
    national_12hr_waits - prev_quarter_12hr_waits
        AS change_in_12hr_waits,
    trusts_meeting_target,
    active_trusts - trusts_meeting_target
        AS trusts_failing_target
FROM trend
WHERE sort_order IS NOT NULL
ORDER BY sort_order;