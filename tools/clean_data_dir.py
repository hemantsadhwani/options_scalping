import os
import sys
import shutil
import glob

def clean_generated_files():
    """
    Scans all subdirectories within the 'data' folder and deletes
    a specific list of generated files and folders.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_data_dir = os.path.join(project_root, 'data')

    files_to_delete = [
        'tradeview_rev_output.csv',
        'tradeview_cont_output.csv',
        'tradeview_utc.csv',
        os.path.join('call', 'call_out.csv'),
        os.path.join('put', 'put_out.csv')
    ]
    
    folders_to_delete = ['backtest', 'backtest_crp', 'trades', 'trades_crp']

    if not os.path.isdir(base_data_dir):
        print(f"Directory '{base_data_dir}' not found. Nothing to clean.")
        return

    print(f"--- Starting cleanup of generated files in '{base_data_dir}' ---")

    try:
        subdirectories = [d for d in os.listdir(base_data_dir) if os.path.isdir(os.path.join(base_data_dir, d))]
    except FileNotFoundError:
        print(f"Error: Cannot access '{base_data_dir}'.")
        return

    if not subdirectories:
        print("No date directories found to clean.")
        return

    deleted_count = 0
    for dir_name in subdirectories:
        ddmm_path = os.path.join(base_data_dir, dir_name)
        print(f"\nProcessing directory: {ddmm_path}")

        for file_rel_path in files_to_delete:
            file_abs_path = os.path.join(ddmm_path, file_rel_path)
            if os.path.exists(file_abs_path):
                try:
                    os.remove(file_abs_path)
                    print(f"  ✅ Deleted: {file_rel_path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ Error deleting {file_rel_path}: {e}")
        
        # Delete analytics files
        for analytics_file in glob.glob(os.path.join(ddmm_path, 'analytics_*.txt')):
            try:
                os.remove(analytics_file)
                print(f"  ✅ Deleted: {os.path.basename(analytics_file)}")
                deleted_count += 1
            except Exception as e:
                print(f"  ❌ Error deleting {os.path.basename(analytics_file)}: {e}")

        for folder_name in folders_to_delete:
            folder_path = os.path.join(ddmm_path, folder_name)
            if os.path.isdir(folder_path):
                try:
                    shutil.rmtree(folder_path)
                    print(f"  ✅ Deleted folder: {folder_name}/")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ Error deleting folder {folder_name}/: {e}")

    print(f"\n--- Cleanup complete. Total files/folders deleted: {deleted_count} ---")

if __name__ == "__main__":
    if '--force' in sys.argv:
        clean_generated_files()
    else:
        confirm = input("This will delete all generated data files from the './data' subdirectories. Are you sure? (y/n): ")
        if confirm.lower() == 'y':
            clean_generated_files()
        else:
            print("Cleanup cancelled by user.")
