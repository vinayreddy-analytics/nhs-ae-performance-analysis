import pandas as pd
from sqlalchemy import create_engine
import urllib

# -------------------------------------------------------
# Load Q3 and Q4 2024-25 from monthly CSVs
# Since the quarterly XLS files are corrupted, I used
# individual monthly CSVs and aggregate them to quarter level
# -------------------------------------------------------

DATA_FOLDER = r"C:\Users\zainv\OneDrive\Desktop\NHS Datasets"

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=nhs_ae_analysis;"
    "Trusted_Connection=yes;"
)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# Q3 2024-25 = October, November, December 2024
# Q4 2024-25 = January, February, March 2025

quarter_files = {
    "Q3 2024-25": [
        "Monthly-AE-October-2024.csv",
        "Monthly-AE-November-2024.csv",
        "Monthly-AE-December-2024.csv",
    ],
    "Q4 2024-25": [
        "Monthly-AE-January-2025.csv",
        "Monthly-AE-February-2025.csv",
        "Monthly-AE-March-2025.csv",
    ],
}

import os

all_quarters = []

for quarter_label, files in quarter_files.items():
    print(f"\nProcessing: {quarter_label}")
    monthly_frames = []

    for filename in files:
        filepath = os.path.join(DATA_FOLDER, filename)
        print(f"  Reading: {filename}")

        # Monthly CSVs also have metadata rows at top
        # Read raw first to find the header
        raw = pd.read_csv(filepath, header=None, encoding="latin-1")

        header_row = None
        for i, row in raw.head(25).iterrows():
            values = [str(v).strip().lower() for v in row if pd.notna(v)]
            if "org code" in values or "code" in values:
                header_row = i
                break

        if header_row is None:
            print(f"    WARNING: Could not find header - trying row 0")
            header_row = 0

        print(f"    Header at row {header_row}")

        df = pd.read_csv(
            filepath,
            header=header_row,
            encoding="latin-1"
        )

        df.dropna(how="all", inplace=True)
        df.dropna(axis=1, how="all", inplace=True)

        # Clean column names
        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
            .str.replace(r"[^a-z0-9]+", "_", regex=True)
            .str.strip("_")
        )

        print(f"    Rows: {len(df)} | Cols: {len(df.columns)}")
        print(f"    First 5 cols: {list(df.columns)[:5]}")

        monthly_frames.append(df)

    if not monthly_frames:
        print(f"  No files loaded for {quarter_label}")
        continue

    # Stack the three months
    combined_quarter = pd.concat(monthly_frames, ignore_index=True)
    combined_quarter["source_file"] = quarter_label
    all_quarters.append(combined_quarter)
    print(f"  Total rows for {quarter_label}: {len(combined_quarter)}")


if all_quarters:
    final = pd.concat(all_quarters, ignore_index=True)
    print(f"\nTotal rows to append: {len(final)}")
    print(f"Columns: {list(final.columns)}")

    # Append to existing ae_raw table
    final.to_sql(
        name="ae_raw_monthly",
        con=engine,
        if_exists="replace",
        index=False,
        schema="dbo"
    )
    print("\nDone - loaded into dbo.ae_raw_monthly")
    print("Check column names then we will align and merge with ae_raw")