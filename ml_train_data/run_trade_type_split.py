import pandas as pd

# Load the enriched data file
df = pd.read_csv('ml_data_enriched.csv')

# Filter the DataFrame for 'Call' and 'Put' types
call_df = df[df['type'] == 'Call']
put_df = df[df['type'] == 'Put']

# Save the filtered DataFrames to new CSV files
call_df.to_csv('ml_call_data.csv', index=False)
put_df.to_csv('ml_put_data.csv', index=False)

print("Files 'ml_call_data.csv' and 'ml_put_data.csv' have been created successfully.")