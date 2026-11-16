import sys

import pandas as pd

from parse import find_header_row

path = sys.argv[1]
sheet = sys.argv[2]

header_row = find_header_row(path, sheet)
df = pd.read_excel(path, sheet_name=sheet, header=header_row)

print("Header row:", header_row)
print("Rows:", len(df))
print(list(df.columns))
