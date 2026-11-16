import sys

import pandas as pd

path = sys.argv[1]

if len(sys.argv) > 2:
    sheet = sys.argv[2]
    print(pd.read_excel(path, sheet_name=sheet, header=None, nrows=15))
else:
    print(pd.ExcelFile(path).sheet_names)