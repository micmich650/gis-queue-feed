import pandas as pd

path = "data/raw/2026-11-02_1293955078_GIS_Report_October2026.xlsx"
print(pd.ExcelFile(path).sheet_names)