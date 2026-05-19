import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from sqlalchemy import create_engine
import urllib
import os

"""
================================================================
Project : NHS A&E Performance Analysis (2023-25)
File    : load_data.py
Author  : Vinay Reddy Thudi
Date    : May 2026

Purpose : Loads 8 quarterly NHS England A&E XLS files into
          SQL Server. Auto-detects header rows, standardises
          column names, and handles file format variations.

Output  : dbo.ae_raw (SQL Server - nhs_ae_analysis)
================================================================
"""

OUTPUT_FOLDER = r"C:\Users\zainv\OneDrive\Desktop\NHS Datasets\nhs-ae-performance-analysis\python\charts"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=nhs_ae_analysis;"
    "Trusted_Connection=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# -------------------------------------------------------
# Pull unified data from SQL
# -------------------------------------------------------
df = pd.read_sql("SELECT * FROM dbo.ae_unified", engine)

print(f"Rows loaded: {len(df)}")
print(f"Columns: {list(df.columns)}")

# Convert numeric columns - must happen before any calculations
numeric_cols = [
    "type1_attendances", "type1_over_4hr", "type1_within_4hr",
    "type2_attendances", "type3_attendances", "total_attendances",
    "dta_12hr_plus", "dta_4to12hr", "total_emergency_admissions",
    "pct_within_4hr_type1", "pct_within_4hr_all"
]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

print("Numeric conversion complete.")

# -------------------------------------------------------
# Calculate 4hr performance where not already present
# -------------------------------------------------------
t1 = pd.to_numeric(df["type1_attendances"], errors="coerce")
t1_over = pd.to_numeric(df["type1_over_4hr"], errors="coerce")

print(f"t1 dtype: {t1.dtype}")
print(f"t1_over dtype: {t1_over.dtype}")
print(f"t1 sample: {t1.head()}")
print(f"t1_over sample: {t1_over.head()}")

diff = t1 - t1_over
print(f"diff dtype: {diff.dtype}")
print(f"diff sample: {diff.head()}")

result = diff / t1.replace(0, float('nan')) * 100
result = pd.to_numeric(result, errors="coerce")
print(f"result dtype: {result.dtype}")

df["pct_within_4hr_calc"] = result.round(1)
df["performance"] = df["pct_within_4hr_calc"]

# -------------------------------------------------------
# Sort order for quarters
# -------------------------------------------------------
quarter_order = {
    ("2023-24", "Q1"): 1,
    ("2023-24", "Q2"): 2,
    ("2023-24", "Q3"): 3,
    ("2023-24", "Q4"): 4,
    ("2024-25", "Q1"): 5,
    ("2024-25", "Q2"): 6,
    ("2024-25", "Q3 2024-25"): 7,
    ("2024-25", "Q4 2024-25"): 8,
}

df["sort_order"] = df.apply(
    lambda r: quarter_order.get((r["financial_year"], r["quarter_label"]), 99),
    axis=1
)

df["quarter_display"] = df["financial_year"] + " " + df["quarter_label"]

# Clean display labels
label_map = {
    "2023-24 Q1": "Q1\n2023-24",
    "2023-24 Q2": "Q2\n2023-24",
    "2023-24 Q3": "Q3\n2023-24",
    "2023-24 Q4": "Q4\n2023-24",
    "2024-25 Q1": "Q1\n2024-25",
    "2024-25 Q2": "Q2\n2024-25",
    "2024-25 Q3 2024-25": "Q3\n2024-25",
    "2024-25 Q4 2024-25": "Q4\n2024-25",
}
df["quarter_display"] = df["quarter_display"].map(label_map)

# -------------------------------------------------------
# Chart 1: National 4hr performance trend over 8 quarters
# -------------------------------------------------------
print("\nBuilding Chart 1 - National trend...")

quarterly = (
    df[df["type1_attendances"] > 0]
    .groupby(["sort_order", "quarter_display"])
    .apply(lambda g: pd.Series({
        "national_pct": (
            (g["type1_attendances"] - g["type1_over_4hr"]).sum()
            / g["type1_attendances"].sum() * 100
        ).round(1)
    }))
    .reset_index()
    .sort_values("sort_order")
    .dropna()
)

fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    quarterly["quarter_display"],
    quarterly["national_pct"],
    marker="o",
    linewidth=2.5,
    color="#005EB8",
    markersize=8,
    label="National 4hr performance"
)

# 95% target line
ax.axhline(y=95, color="#DA291C", linewidth=1.5,
           linestyle="--", label="95% NHS Standard")

# Shade the gap
ax.fill_between(
    quarterly["quarter_display"],
    quarterly["national_pct"],
    95,
    alpha=0.08,
    color="#DA291C",
    label="Performance gap"
)

for _, row in quarterly.iterrows():
    ax.annotate(
        f"{row['national_pct']:.1f}%",
        (row["quarter_display"], row["national_pct"]),
        textcoords="offset points",
        xytext=(0, 10),
        ha="center",
        fontsize=9,
        color="#005EB8"
    )

ax.set_ylim(50, 100)
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_title(
    "NHS England A&E 4-Hour Performance: 2023-24 to 2024-25\n"
    "No Trust met the 95% standard in any quarter",
    fontsize=13, fontweight="bold", pad=15
)
ax.set_xlabel("Quarter", fontsize=11)
ax.set_ylabel("% Patients seen within 4 hours (Type 1)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.4)
sns.despine()

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FOLDER, "01_national_trend.png"), dpi=150)
plt.close()
print("  Saved: 01_national_trend.png")

# -------------------------------------------------------
# Chart 2: Regional average performance comparison
# -------------------------------------------------------
print("Building Chart 2 - Regional comparison...")

# Standardise region names - quarterly and monthly CSVs store them differently
df["region_clean"] = (
    df["region"]
    .str.strip()
    .str.upper()
    .str.replace("NHS ENGLAND ", "", regex=False)
    .str.replace("NHS ", "", regex=False)
    .str.title()
    .str.strip()
)

regional = (
    df[
        (df["type1_attendances"] > 0) &
        (df["type1_over_4hr"].notna()) &
        (df["region_clean"].notna()) &
        (~df["region_clean"].isin(["Total", "Nan", ""]))
    ]
    .groupby("region_clean")
    .apply(lambda g: pd.Series({
        "avg_pct": (
            (g["type1_attendances"] - g["type1_over_4hr"]).sum()
            / g["type1_attendances"].sum() * 100
        ).round(1)
    }))
    .reset_index()
    .sort_values("avg_pct", ascending=True)
    .dropna()
)

# Shorten region labels
regional["region_short"] = regional["region_clean"]

fig, ax = plt.subplots(figsize=(11, 6))

colors = ["#DA291C" if v < 60 else "#FFB81C" if v < 65 else "#009639"
          for v in regional["avg_pct"]]

bars = ax.barh(
    regional["region_short"],
    regional["avg_pct"],
    color=colors,
    edgecolor="white",
    height=0.6
)

ax.axvline(x=95, color="#DA291C", linewidth=1.5,
           linestyle="--", label="95% NHS Standard", zorder=5)

for bar, val in zip(bars, regional["avg_pct"]):
    ax.text(
        val + 0.3, bar.get_y() + bar.get_height() / 2,
        f"{val:.1f}%",
        va="center", ha="left", fontsize=10
    )

ax.set_xlim(0, 100)
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_title(
    "Average A&E 4-Hour Performance by NHS Region (2023-25)\n"
    "All regions significantly below the 95% standard",
    fontsize=13, fontweight="bold", pad=15
)
ax.set_xlabel("% Patients seen within 4 hours (Type 1 A&E)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(axis="x", linestyle="--", alpha=0.4)
sns.despine()

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FOLDER, "02_regional_comparison.png"), dpi=150)
plt.close()
print("  Saved: 02_regional_comparison.png")

# -------------------------------------------------------
# Chart 3: 12-hour DTA waits trend - national total
# -------------------------------------------------------
print("Building Chart 3 - 12hr DTA trend...")

dta_trend = (
    df[df["dta_12hr_plus"].notna()]
    .groupby(["sort_order", "quarter_display"])
    .agg(total_12hr=("dta_12hr_plus", "sum"))
    .reset_index()
    .sort_values("sort_order")
)

# Only use first 6 quarters (quarterly XLS - comparable data)
dta_trend = dta_trend[dta_trend["sort_order"] <= 6]

fig, ax = plt.subplots(figsize=(12, 6))

ax.bar(
    dta_trend["quarter_display"],
    dta_trend["total_12hr"],
    color="#005EB8",
    edgecolor="white",
    width=0.6
)

for _, row in dta_trend.iterrows():
    ax.text(
        row["quarter_display"],
        row["total_12hr"] + 1000,
        f"{int(row['total_12hr']):,}",
        ha="center", va="bottom", fontsize=10, color="#005EB8"
    )

ax.set_title(
    "National 12-Hour DTA Waits by Quarter (2023-24 to Q2 2024-25)\n"
    "Patients waiting 12+ hours after decision to admit",
    fontsize=13, fontweight="bold", pad=15
)
ax.set_xlabel("Quarter", fontsize=11)
ax.set_ylabel("Number of patients", fontsize=11)
ax.yaxis.set_major_formatter(
    mtick.FuncFormatter(lambda x, _: f"{int(x):,}")
)
ax.grid(axis="y", linestyle="--", alpha=0.4)
sns.despine()

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_FOLDER, "03_dta_12hr_trend.png"), dpi=150)
plt.close()
print("  Saved: 03_dta_12hr_trend.png")

print("\nAll charts saved to:", OUTPUT_FOLDER)
print("\nDone.")