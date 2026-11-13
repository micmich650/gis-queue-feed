from pathlib import Path

import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 8)

files = sorted(Path("data/raw").glob("*.xlsx"))
path = files[-1]
print("File:", path)

excel = pd.ExcelFile(path)
print("Sheets:", excel.sheet_names)

for sheet in excel.sheet_names:
    df = pd.read_excel(path, sheet_name=sheet, header=None, nrows=15)
    print(f"\n===== {sheet} =====")
    print(df)