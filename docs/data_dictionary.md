# Data Dictionary — NHS A&E Performance Analysis

## Source Dataset
**Name:** Monthly A&E ( Accident and Emergency. The hospital department where people go for urgent medical treatment. Also called an Emergency Department (ED)) Admissions  
**Publisher:** NHS England  
**Licence:** Open Government Licence v3.0  
**Validated against:** NHS England published national totals (Q1 2024-25 = 4,250,407 Type 1 attendances confirmed)

---

## Table: ae_unified
Primary analytical table combining quarterly XLS and monthly CSV source data.
1,605 rows covering 8 quarters (Q1 2023-24 to Q4 2024-25).

| Column | Type | Description |
|---|---|---|
| period | VARCHAR | Original period label from source file |
| financial_year | VARCHAR | NHS financial year (e.g. 2023-24) |
| quarter_label | VARCHAR | Quarter identifier (Q1, Q2, Q3, Q4, Q3 2024-25, Q4 2024-25) |
| org_code | VARCHAR | Unique NHS organisation code (e.g. RRK = University Hospitals Birmingham) |
| org_name | VARCHAR | Full organisation name, standardised to most frequent variant across sources |
| region | VARCHAR | NHS England region (e.g. NHS England Midlands) |
| type1_attendances | BIGINT | Total Type 1 (major A&E) attendances in the period |
| type2_attendances | BIGINT | Total Type 2 (single specialty) attendances in the period |
| type3_attendances | BIGINT | Total Type 3 (minor injury / walk-in) attendances in the period |
| total_attendances | BIGINT | Sum of all A&E attendance types |
| type1_within_4hr | BIGINT | Type 1 patients discharged, admitted or transferred within 4 hours |
| type1_over_4hr | BIGINT | Type 1 patients who waited more than 4 hours |
| total_within_4hr | BIGINT | All types combined - patients seen within 4 hours |
| total_over_4hr | BIGINT | All types combined - patients waiting over 4 hours |
| pct_within_4hr_type1 | FLOAT | Pre-calculated % of Type 1 patients within 4 hours (from source) |
| pct_within_4hr_all | FLOAT | Pre-calculated % of all types within 4 hours (from source) |
| dta_4to12hr | BIGINT | Patients waiting 4-12 hours from Decision To Admit to receiving a bed |
| dta_12hr_plus | BIGINT | Patients waiting 12+ hours from Decision To Admit - key patient safety indicator |
| emergency_admissions_type1 | BIGINT | Emergency admissions via Type 1 A&E department |
| total_emergency_admissions | BIGINT | All emergency admissions including non-A&E routes |
| data_source | VARCHAR | Source file type: quarterly_xls or monthly_csv |
| is_primary_source | INT | 1 = use this row for Trust-level analysis (avoids double counting), 0 = exclude |

---

## Key Metrics Explained

**4-Hour Standard**  
The NHS operational standard requires 95% of patients attending A&E to be 
admitted, transferred or discharged within 4 hours of arrival. This standard 
has not been met nationally since 2015.

**Type 1 Performance %**  
Calculated as: (type1_attendances - type1_over_4hr) / type1_attendances × 100  
This is calculated from raw counts rather than the pre-supplied percentage 
to ensure consistency across quarterly and monthly data sources.

**Decision To Admit (DTA ) Waits** 

#### WHat is Decision To Admit (DTA)?
Decision To Admit. The moment a doctor decides a patient needs a hospital bed. The 12-hour DTA wait measures how long patients are stuck in A&E after that decision because no bed is available.

Once a clinician decides a patient needs admission, the clock starts. 
The 12-hour DTA wait (dta_12hr_plus) measures patients still in A&E 
12+ hours after that decision - indicating bed unavailability rather than 
A&E throughput problems. This is considered a serious harm indicator.

**12-Hour Wait Rate**  
Calculated as: dta_12hr_plus / type1_attendances × 100  
Expresses 12-hour waits as a proportion of Type 1 attendances, 
allowing fair comparison between large and small Trusts.

---

## Department Types

| Type | Description | NHS Standard |
|---|---|---|
| Type 1 | Consultant-led 24/7 Emergency Department with full resuscitation | 95% within 4 hours |
| Type 2 | Single specialty (e.g. ophthalmology, dental emergency) | No national standard |
| Type 3 | Minor Injury Units, Walk-in Centres, Urgent Treatment Centres | No national standard |

---

## Data Sources by Quarter

| Quarter | Financial Year | Source | Provider Count | Type 1 Attendances |
|---|---|---|---|---|
| Q1 | 2023-24 | quarterly_xls | 204 | 4,060,969 |
| Q2 | 2023-24 | quarterly_xls | 203 | 4,072,546 |
| Q3 | 2023-24 | quarterly_xls | 203 | 4,183,825 |
| Q4 | 2023-24 | quarterly_xls | 201 | 4,208,495 |
| Q1 | 2024-25 | quarterly_xls | 197 | 4,250,407 |
| Q2 | 2024-25 | quarterly_xls | 198 | 4,110,208 |
| Q3 | 2024-25 | monthly_csv | 200 | 4,226,705 |
| Q4 | 2024-25 | monthly_csv | 199 | 3,986,836 |

---

## Known Data Quality Issues

**1. Q3 and Q4 2024-25 source difference**  
Quarterly XLS files for these periods were corrupted and could not be read 
by Python. Monthly CSV files (3 months per quarter) were used instead and 
aggregated to quarter level. Performance percentages for these quarters are 
calculated from raw counts rather than pre-supplied figures.

**2. Organisation name variants**  
Some org codes appear with different name formats across quarterly XLS and 
monthly CSV sources (e.g. mixed case vs upper case). Names have been 
standardised to the most frequently occurring variant using a SQL window 
function (ROW_NUMBER with COUNT ordering).

**3. Independent sector providers**  
The dataset includes independent sector organisations commissioned to provide 
NHS A&E services. Many have zero Type 1 attendances and are excluded from 
Trust-level performance analysis using the is_primary_source flag and 
type1_attendances > 0 filter.

**4. Seasonal data note**  
Q3 (October-December) consistently shows the lowest performance figures 
due to winter demand pressures. Year-on-year comparisons should account 
for this seasonal pattern.

---

## Assumptions

1. Performance % is calculated from raw attendance and breach counts 
   rather than pre-supplied percentages, for consistency across data sources
2. Quarterly figures represent the full three-month period, not monthly averages
3. National totals validated against NHS England published statistics — 
   Q1 2024-25 Type 1 attendances confirmed as 4,250,407
4. Providers with zero Type 1 attendances are excluded from major A&E analysis 
   as they operate Type 2 or Type 3 departments only