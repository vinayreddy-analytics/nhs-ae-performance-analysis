import pandas as pd
from sqlalchemy import create_engine
import os
import urllib


DATA_FOLDER = r"C:\Users\zainv\OneDrive\Desktop\NHS Datasets"

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=nhs_ae_analysis;"
    "Trusted_Connection=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

files = [
    "Q1 2023-24 XLS Apr–Jun 2023.xls",
    "Q2 2023-24 XLS Jul–Sep 2023.xls",
    "Q3 2023-24 XLS Oct–Dec 2023.xls",
    "Q4 2023-24 XLS Jan–Mar 2024.xls",
    "Q1 2024-25 XLS Apr–Jun 2024.xls",
    "Q2 2024-25 XLS Jul–Sep 2024.xls",
    "Q3-2024-25.xls",
    "Q4-2024-25.xls",
]


def read_sheet(filepath):
    """Try both engines, return raw dataframe with no header"""
    engines = ["openpyxl", "xlrd"] if filepath.endswith(".xlsx") else ["xlrd", "openpyxl"]
    for eng in engines:
        try:
            return pd.read_excel(
                filepath,
                sheet_name="Provider Level Data",
                header=None,
                engine=eng
            ), eng
        except Exception:
            continue
    return None, None


def find_header_row(raw):
    """Find the row where Code, Region, Name all appear together"""
    for i, row in raw.head(25).iterrows():
        values = [str(v).strip().lower() for v in row if pd.notna(v)]
        if "code" in values and "region" in values and "name" in values:
            return i
    # Fallback - row 15 is consistent across all NHS quarterly files
    return 15


def clean_columns(df):
    """Make column names SQL-safe and unique"""
    cols = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    # Handle duplicate column names by appending _1, _2 etc
    seen = {}
    new_cols = []
    for col in cols:
        if col in seen:
            seen[col] += 1
            new_cols.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 0
            new_cols.append(col)
    df.columns = new_cols
    return df


all_quarters = []

for filename in files:
    filepath = os.path.join(DATA_FOLDER, filename)
    print(f"\nReading: {filename}")

    # Step 1 - read raw sheet
    raw, eng = read_sheet(filepath)
    if raw is None:
        print(f"  ERROR: Could not open file with any engine - skipping")
        continue

    # Step 2 - find header row
    header_row = find_header_row(raw)
    print(f"  Header at row {header_row}, using engine: {eng}")

    # Step 3 - re read from header row
    engines = ["openpyxl", "xlrd"] if filepath.endswith(".xlsx") else ["xlrd", "openpyxl"]
    df = None
    for e in engines:
        try:
            df = pd.read_excel(
                filepath,
                sheet_name="Provider Level Data",
                header=header_row,
                engine=e
            )
            break
        except Exception:
            continue

    if df is None:
        print(f"  ERROR: Could not read data - skipping")
        continue

    # Step 4 - clean up
    df.dropna(how="all", inplace=True)
    df.dropna(axis=1, how="all", inplace=True)
    df = clean_columns(df)

    # Drop England total row and blank rows
    if "code" in df.columns:
        df = df[df["code"].notna()]
        df = df[df["code"].astype(str).str.strip() != "-"]

    # Tag source
    df["source_file"] = filename

    print(f"  Rows loaded: {len(df)}")
    print(f"  Columns ({len(df.columns)}): {list(df.columns)[:6]}...")

    all_quarters.append(df)


if not all_quarters:
    print("\nNo data loaded.")
else:
    # Align columns across all quarters before concat
    # Some quarters might have slightly different columns - fill missing values with NaN
    all_cols = set()
    for df in all_quarters:
        all_cols.update(df.columns)

    aligned = []
    for df in all_quarters:
        for col in all_cols:
            if col not in df.columns:
                df[col] = None
        aligned.append(df)

    combined = pd.concat(aligned, ignore_index=True)

    print(f"\n{'='*50}")
    print(f"Total rows: {len(combined)}")
    print(f"Total columns: {len(combined.columns)}")
    print(f"\nAll column names:")
    for c in combined.columns:
        print(f"  {c}")

    # Rename duplicate columns to meaningful names
    combined.rename(columns={
        "type_1_departments_major_a_e":                    "type1_attendances",
        "type_2_departments_single_specialty":             "type2_attendances",
        "type_3_departments_other_a_e_minor_injury_unit":  "type3_attendances",
        "total_attendances":                               "total_attendances",
        "type_1_departments_major_a_e_1":                  "type1_within_4hr",
        "type_2_departments_single_specialty_1":           "type2_within_4hr",
        "type_3_departments_other_a_e_minor_injury_unit_1":"type3_within_4hr",
        "total_attendances_4_hours":                       "total_within_4hr",
        "type_1_departments_major_a_e_2":                  "type1_over_4hr",
        "type_2_departments_single_specialty_2":           "type2_over_4hr",
        "type_3_departments_other_a_e_minor_injury_unit_2":"type3_over_4hr",
        "total_attendances_4_hours_1":                     "total_over_4hr",
        "number_of_patients_spending_4_hours_from_decision_to_admit_to_admission":  "dta_4to12hr",
        "number_of_patients_spending_12_hours_from_decision_to_admit_to_admission": "dta_12hr_plus",
        "unnamed_28":                                      "icb_name",
    }, inplace=True)

    combined.to_sql(
        name="ae_raw",
        con=engine,
        if_exists="replace",
        index=False,
        schema="dbo"
    )

    print(f"\nDone - loaded into dbo.ae_raw")