from pathlib import Path

import pandas as pd

PROJECT_SHEETS = ["Project Details - Large Gen", "Project Details"]
COLUMN_ALIASES = {"GINR Study Phase": "GIM Study Phase"}

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
    matches = raw.index[(raw == "INR").any(axis=1)]
    if len(matches) == 0:
        raise ValueError(f"No 'INR' header row found in sheet '{sheet}' of {path}")
    return matches[0]

def pick_sheet(path):
    available = pd.ExcelFile(path).sheet_names
    for sheet in PROJECT_SHEETS:
        if sheet in available:
            return sheet
    raise ValueError(f"No project sheet found; sheets are {available}")


def parse(path, sheet=None):
    if sheet is None:
        sheet = pick_sheet(path)
    header_row = find_header_row(path, sheet)
    df = pd.read_excel(path, sheet_name=sheet, header=header_row)
    df = df.rename(columns=COLUMN_ALIASES)

    missing = [col for col in COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df[list(COLUMNS)]
    df = df.rename(columns=COLUMNS)

    df = df.dropna(subset=["project_id"])
    df["project_id"] = df["project_id"].astype(str).str.strip()
    for col in ["project_name", "study_phase", "county", "zone", "fuel", "technology"]:
        df[col] = df[col].str.strip()

    return df

MIN_ROWS = 100
DATE_COLUMNS = [
    "projected_cod",
    "ia_signed",
    "approved_energization",
    "approved_synchronization",
]


def validate(df):
    problems = []

    if len(df) < MIN_ROWS:
        problems.append(f"only {len(df)} projects (expected at least {MIN_ROWS})")

    duplicates = df["project_id"].duplicated().sum()
    if duplicates:
        problems.append(f"{duplicates} duplicate project IDs")

    if not pd.api.types.is_numeric_dtype(df["capacity_mw"]):
        problems.append("capacity_mw is not numeric")

    for col in DATE_COLUMNS:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            problems.append(f"{col} is not a date column")

    return problems

def sheet_says_none(path, sheet):
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    return raw[0].astype(str).str.startswith("No ").any()

EVENT_SHEETS = {
    "Cancellation Update": "cancelled",
    "Inactive Projects": "inactive",
    "Commissioning Update": "commissioned",
}


def parse_events(path):
    frames = []
    for sheet, event in EVENT_SHEETS.items():
        try:
            header_row = find_header_row(path, sheet)
        except ValueError:
            if sheet_says_none(path, sheet):
                continue
            raise
        df = pd.read_excel(path, sheet_name=sheet, header=header_row)
        df = df.dropna(subset=["INR"])
        frames.append(
            pd.DataFrame(
                {"project_id": df["INR"].astype(str).str.strip(), "event": event}
            )
        )

    if not frames:
        return pd.DataFrame(columns=["project_id", "event"])
    return pd.concat(frames, ignore_index=True).drop_duplicates(ignore_index=True)


if __name__ == "__main__":
    path = sorted(Path("data/raw").glob("*.xlsx"))[-1]
    projects = parse(path)
    events = parse_events(path)
    print(events["event"].value_counts())

    print("Projects:", len(projects))
    print("Duplicate IDs:", projects["project_id"].duplicated().sum())
    print()
    print(projects.dtypes)
    print()
    print(projects.head())
    print(projects[projects["project_name"].str.endswith(" ", na=False)])