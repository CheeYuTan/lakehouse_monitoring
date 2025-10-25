"""
Test script to fetch DQ functions from monitoring_admin schema
"""
import db_utils
import pandas as pd

# Fetch all DQ functions
print("Fetching DQ functions...")
df_functions = db_utils.get_dq_functions()

if not df_functions.empty:
    print(f"\n✅ Found {len(df_functions)} function parameter entries")
    
    # Display all results
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)
    
    print("\n" + "="*80)
    print("DQ FUNCTIONS")
    print("="*80)
    print(df_functions.to_string())
    
    # Group by function to show structure
    print("\n" + "="*80)
    print("FUNCTIONS BY NAME")
    print("="*80)
    for func_name in df_functions['function_name'].unique():
        func_params = df_functions[df_functions['function_name'] == func_name]
        print(f"\n📦 {func_name}")
        print(f"   Return Type: {func_params.iloc[0]['return_type']}")
        print(f"   Description: {func_params.iloc[0]['description']}")
        print(f"   Parameters:")
        for _, param in func_params.iterrows():
            if pd.notna(param['parameter_name']):
                print(f"      - {param['parameter_name']}: {param['parameter_type']} ({param['parameter_mode']})")
        
else:
    print("❌ No functions found")

