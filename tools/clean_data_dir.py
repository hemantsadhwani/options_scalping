# nifty_option_trading/tools/clean_data_dir.py

import os
import sys

def clean_generated_files():
    """
    Scans all subdirectories within the 'data' folder and deletes
    a specific list of generated files.
    """
    # Navigate to the project root from the script's location
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_data_dir = os.path.join(project_root, 'data')

    # List of files to be deleted from each DDMM directory
    files_to_delete = [
        'tradeview_utc_output.csv',
        'tradeview_utc.csv',
        'backtest_results.csv',
        os.path.join('call', 'call_out.csv'),
        os.path.join('put', 'put_out.csv')
    ]

    if not os.path.isdir(base_data_dir):
        print(f"Directory '{base_data_dir}' not found. Nothing to clean.")
        return

    print(f"--- Starting cleanup of generated files in '{base_data_dir}' ---")

    # Get all subdirectories (e.g., '3006')
    try:
        subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    except FileNotFoundError:
        print(f"Error: Cannot access '{base_data_dir}'.")
        return

    if not subdirectories:
        print("No date directories found to clean.")
        return

    deleted_count = 0
    # Loop through each DDMM directory
    for dir_name in subdirectories:
        ddmm_path = os.path.join(base_data_dir, dir_name)
        print(f"\nProcessing directory: {ddmm_path}")

        # Loop through the list of files to delete
        for file_rel_path in files_to_delete:
            file_abs_path = os.path.join(ddmm_path, file_rel_path)
            
            if os.path.exists(file_abs_path):
                try:
                    os.remove(file_abs_path)
                    print(f"  ✅ Deleted: {file_rel_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ Error deleting {file_rel_path}: {e}")
            else:
                # This is normal, not an error, so we don't print anything.
                pass

    print(f"\n--- Cleanup complete. Total files deleted: {deleted_count} ---")

if __name__ == "__main__":
    # This confirmation step is a safety feature to prevent accidental deletion.
    # It checks for a '--force' command-line argument to bypass the prompt.
    if '--force' in sys.argv:
        clean_generated_files()
    else:
        confirm = input("This will delete all generated data files from the './data' subdirectories. Are you sure? (y/n): ")
        if confirm.lower() == 'y':
            clean_generated_files()
        else:
            print("Cleanup cancelled by user.")