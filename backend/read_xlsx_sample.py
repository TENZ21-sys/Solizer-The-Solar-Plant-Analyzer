import pandas as pd

file_path = "../Example xlsx file.xlsx"
df = pd.read_excel(file_path, sheet_name=0)
print("Columns:")
print(df.columns.tolist())
print("\nFirst 10 rows:")
print(df.head(10))
print("\nData description:")
print(df.describe())
