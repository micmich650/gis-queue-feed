from pathlib import Path

import pandas as pd

SHEET = "Project Details - Large Gen"
path = sorted(Path("data/raw").glob("*.xlsx"))[-1]

raw = pd.read_excel(path, sheet_name=SHEET, header=None)
header_row = raw.index[raw[0] == "INR"][0]
print("Header is on row", header_row)

projects = pd.read_excel(path, sheet_name=SHEET, header=header_row)
print("Rows and columns:", projects.shape)
print(list(projects.columns))
print(projects.head())

unnamed = [c for c in projects.columns if str(c).startswith("Unnamed")]
print(projects[unnamed].dropna(how="all").head())