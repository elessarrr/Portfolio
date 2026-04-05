import os
import glob
import subprocess
import sys
from pathlib import Path

def main():
    target_dir = Path('/Users/Bhavesh/Documents/GitHub/Portfoilo/Aircraft Safety Tracker/ntsb_data_1985-01-01_2026-04-05')
    json_files = list(target_dir.rglob('*.json'))
    json_files.sort()
    
    print(f"Found {len(json_files)} NTSB JSON files to import.")
    
    success_count = 0
    fail_count = 0
    
    env = os.environ.copy()
    env["FLASK_APP"] = "run.py"
    
    for file_path in json_files:
        # Skip the one that we know was already done or if any other skipping logic is needed.
        # But user requested end-to-end import.
        # We can just import all of them, our dedupe logic will handle duplicates.
        print(f"Processing {file_path.name}...")
        try:
            # Running via subprocess to isolate memory and avoid syntax issues
            result = subprocess.run(
                ["flask", "import-data", "ntsb", "--file", str(file_path)],
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            success_count += 1
            print(f"  Success: {file_path.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ERROR processing {file_path.name}:")
            print(e.stderr)
            fail_count += 1
            print("  Halting batch import to allow rollback/fix.")
            break
            
    print(f"\nBatch Import Summary:")
    print(f"  Successfully processed: {success_count}")
    print(f"  Failed: {fail_count}")

if __name__ == '__main__':
    main()
