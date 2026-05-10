import pandas as pd
import os

# Get the absolute path to the Excel file
file_path = os.path.join(os.path.dirname(__file__), 'data', 'emissions_data.xlsx')

# Open the Excel file
xl = pd.ExcelFile(file_path)

# Print available sheets
print('Available sheets in the Excel file:')
print(xl.sheet_names)

# For each sheet, print year information
for sheet_name in xl.sheet_names:
    print(f'\nAnalyzing sheet: {sheet_name}')
    df = pd.read_excel(xl, sheet_name)
    if 'YEAR' in df.columns:
        years = df['YEAR'].unique()
        print(f'Years in this sheet: {sorted(years)}')
    else:
        print('No YEAR column found in this sheet')
    print(f'Number of rows: {len(df)}')
    print('Columns:', df.columns.tolist())
    print('\nSample data:')
    print(df.head(2))