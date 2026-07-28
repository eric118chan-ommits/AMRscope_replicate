#!/usr/bin/env python3
import pandas as pd
import sys

def fix_headers(csv_path):
    df = pd.read_csv(csv_path)
    
    # Map the legacy columns in the file to what preprocessing.py expects
    rename_map = {
        'wt_sequence': 'wt_seq',
        'mut_sequence': 'mt_seq',
        'position': 'aa_index'
    }
    
    # Only rename if the old columns exist to avoid errors on already-patched files
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    df.to_csv(csv_path, index=False)
    print(f"Success: Patched headers in {csv_path} to match pipeline requirements.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fix_headers(sys.argv[1])
    else:
        print("Error: Please provide a CSV file path.")
