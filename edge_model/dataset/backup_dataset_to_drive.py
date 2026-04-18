"""
Northern Blades — Standalone Drive Backup Script
Runs on Google Colab to securely zip and backup the dataset to Google Drive.

Usage in Colab:
  from google.colab import drive
  drive.mount('/content/drive')
  
  python backup_dataset_to_drive.py
"""

import os
import shutil
import time

# ─── CONFIG ───────────────────────────────────────────────────────────────────
SOURCE_DIR = "dataset"
ZIP_NAME = "northern_blades_sam_results" # will produce .zip
DRIVE_BACKUP_PATH = "/content/drive/MyDrive/northern_blades_backup"
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("Northern Blades — Google Drive Backup Utility")
    print("=" * 60)

    # 1. Check if source exists
    if not os.path.exists(SOURCE_DIR):
        print(f"\n❌ ERROR: Source directory '{SOURCE_DIR}' not found!")
        print("   Are you running this in the correct folder?")
        return

    # 2. Check if Drive is mounted
    print(f"\n[1/3] Checking for Google Drive...")
    if not os.path.exists("/content/drive/MyDrive"):
        print("❌ ERROR: Google Drive is NOT mounted.")
        print("   Run this cell in Colab first:")
        print("   from google.colab import drive")
        print("   drive.mount('/content/drive')")
        return
    print("   ✅ Google Drive is mounted and accessible.")

    # 3. Create backup directory in Drive
    os.makedirs(DRIVE_BACKUP_PATH, exist_ok=True)
    
    # 4. Compress the dataset (FAST VERSION)
    print(f"\n[2/3] Bundling dataset (using fast zero-compression zip)...")
    start_time = time.time()
    
    local_zip_path = f"/content/{ZIP_NAME}.zip"
    
    # Use native OS zip with -0 (store only, no compression). 
    # Images are already highly compressed (jpg/png), so compressing them again 
    # just wastes CPU time. This should take seconds instead of minutes.
    import subprocess
    
    try:
        # -r = recursive, -0 = store only (fastest), -q = quiet
        cmd = f"zip -r -0 -q {local_zip_path} {SOURCE_DIR}"
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"   ⚠️ Native zip failed ({e}). Falling back to python zip...")
        import zipfile
        with zipfile.ZipFile(local_zip_path, 'w', zipfile.ZIP_STORED) as zipf:
            for root, dirs, files in os.walk(SOURCE_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, file_path)
    
    zip_size_mb = os.path.getsize(local_zip_path) / (1024 * 1024)
    elapsed = time.time() - start_time
    print(f"   ✅ Bundling complete: {zip_size_mb:.1f} MB (took {elapsed:.1f}s)")

    # 5. Copy to Google Drive
    print(f"\n[3/3] Copying to Google Drive...")
    dest_path = os.path.join(DRIVE_BACKUP_PATH, f"{ZIP_NAME}.zip")
    
    print(f"   Transferring to: {dest_path}")
    shutil.copy2(local_zip_path, dest_path)
    
    print(f"\n{'='*60}")
    print(f"🚀 BACKUP SUCCESSFUL!")
    print(f"   Your dataset is safely stored in Google Drive at:")
    print(f"   {dest_path}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
