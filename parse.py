from pathlib import Path

import pandas as pd

SHEET = "Project Details - Large Gen"

COLUMNS = {
    "INR": "project_id",
    "Project Name": "project_name",
    "GIM Study Phase": "study_phase",
    "County": "county",
    "CDR Reporting Zone": "zone",
    "Fuel": "fuel",
    "Technology": "technology",
    "Capacity (MW)": "capacity_mw",
    "Projected COD": "projected_cod",
    "IA Signed": "ia_signed",
    "Approved for Energization": "approved_energization",
    "Approved for Synchronization": "approved_synchronization",
}


def find_header_row(path, sheet):
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    matches = raw.index[raw[0] == "INR"]
    if len(matches) == 0:
        raise ValueError(f"No 'INR' header row found in sheet '{sheet}' of {path}")
    return matches[0]


def parse(path, sheet=SHEET):
    header_row = find_header_row(path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, header=header_row)

    df = df[list(COLUMNS)]
    df = df.rename(columns=COLUMNS)

    df = df.dropna(subset=["project_id"])
    df["project_id"] = df["project_id"].astype(str).str.strip()
    for col in ["project_name", "study_phase", "county", "zone", "fuel", "technology"]:
        df[col] = df[col].str.strip()

    return df


if __name__ == "__main__":
    path = sorted(Path("data/raw").glob("*.xlsx"))[-1]
    projects = parse(path)

    print("Projects:", len(projects))
    print("Duplicate IDs:", projects["project_id"].duplicated().sum())
    print()
    print(projects.dtypes)
    print()
    print(projects.head())
    print(projects[projects["project_name"].str.endswith(" ", na=False)])