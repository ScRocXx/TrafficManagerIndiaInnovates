"""
Northern Blades — Step 1: Download Top High-Density Images from UVH-26
Run this on Google Colab or locally (needs huggingface_hub).

Usage:
  pip install huggingface_hub tqdm
  python 01_download_uvh26.py
"""

import os
import json
import shutil
from huggingface_hub import hf_hub_download, HfApi, login
from tqdm import tqdm

# ─── CONFIG ───────────────────────────────────────────────────────────────────
REPO_ID = "iisc-aim/UVH-26"
JSON_FILENAME = "UVH-26-Train/UVH-26-MV-Train.json"  # Majority Voting (higher quality)
OUTPUT_DIR = "northern_blades_dataset/images/all_raw"
TOP_K = 2000  # Get top 2000 densest images (not just 500!)

# HuggingFace token — required for gated datasets like UVH-26
# Get yours at: https://huggingface.co/settings/tokens
HF_TOKEN = "YOUR_HUGGINGFACE_TOKEN_HERE" # DO NOT COMMIT SECRETS
# ─────────────────────────────────────────────────────────────────────────────


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Scout all file paths in the repo (handles subfolder structure)
    print("[Step 1/4] Scouting UVH-26 repository structure...")
    # Login with token so gated datasets are accessible
    login(token=HF_TOKEN, add_to_git_credential=False)
    api = HfApi(token=HF_TOKEN)
    try:
        all_files = api.list_repo_files(repo_id=REPO_ID, repo_type="dataset", token=HF_TOKEN)
    except Exception as e:
        print(f"ERROR: Cannot access repo. Go to https://huggingface.co/datasets/{REPO_ID}")
        print(f"       and click 'Agree and access dataset' first.")
        print(f"       Error: {e}")
        return

    # Build path map: { 'filename.png': 'full/path/to/filename.png' }
    path_map = {}
    for f in all_files:
        if "/data/" in f and (f.endswith('.png') or f.endswith('.jpg')):
            path_map[os.path.basename(f)] = f
    print(f"    Found {len(path_map)} total images in repo.")

    if len(path_map) == 0:
        print("CRITICAL: No images found. You may need a HuggingFace access token.")
        print("  1. Go to https://huggingface.co/settings/tokens")
        print("  2. Create a token")
        print("  3. Run: huggingface-cli login")
        return

    # 2. Download metadata JSON
    print("[Step 2/4] Downloading annotation metadata...")
    meta_path = hf_hub_download(
        repo_id=REPO_ID, filename=JSON_FILENAME, repo_type="dataset", token=HF_TOKEN
    )
    with open(meta_path, 'r') as f:
        coco = json.load(f)
    print(f"    Loaded {len(coco['annotations'])} annotations across {len(coco['images'])} images.")

    # 3. Rank images by annotation density (most crowded first)
    print("[Step 3/4] Ranking images by vehicle density...")
    counts = {}
    for ann in coco['annotations']:
        counts[ann['image_id']] = counts.get(ann['image_id'], 0) + 1

    top_ids = sorted(counts, key=counts.get, reverse=True)[:TOP_K]
    id_to_file = {img['id']: img['file_name'] for img in coco['images']}

    print(f"    Top image has {counts[top_ids[0]]} vehicles.")
    print(f"    Bottom of top-{TOP_K} has {counts[top_ids[-1]]} vehicles.")

    # 4. Download the images
    print(f"[Step 4/4] Downloading top {TOP_K} high-density images...")
    success = 0
    skipped = 0

    for img_id in tqdm(top_ids, desc="Downloading"):
        fname = id_to_file.get(img_id)
        if not fname:
            skipped += 1
            continue

        # Check if already downloaded
        local_path = os.path.join(OUTPUT_DIR, fname)
        if os.path.exists(local_path):
            success += 1
            continue

        remote_path = path_map.get(fname)
        if remote_path:
            try:
                downloaded = hf_hub_download(
                    repo_id=REPO_ID,
                    filename=remote_path,
                    repo_type="dataset",
                    token=HF_TOKEN,
                    local_dir="northern_blades_dataset/_hf_cache",
                    local_dir_use_symlinks=False
                )
                # Copy to flat output directory
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                shutil.copy2(downloaded, local_path)
                success += 1
            except Exception as e:
                skipped += 1
        else:
            skipped += 1

    # Also save the filtered metadata for SAM processing
    filtered_img_ids = set(top_ids[:success + skipped])
    filtered_meta = {
        "images": [img for img in coco['images'] if img['id'] in filtered_img_ids],
        "annotations": [ann for ann in coco['annotations'] if ann['image_id'] in filtered_img_ids],
        "categories": coco['categories']
    }
    meta_out = "northern_blades_dataset/uvh26_top_annotations.json"
    with open(meta_out, 'w') as f:
        json.dump(filtered_meta, f)

    print(f"\n{'='*50}")
    print(f"DONE! Downloaded {success} images, skipped {skipped}.")
    print(f"Images saved to: {OUTPUT_DIR}")
    print(f"Filtered annotations saved to: {meta_out}")
    print(f"{'='*50}")

    # 5. Backup to Google Drive (if on Colab)
    print(f"\n[Step 5] Checking for Google Drive backup...")
    drive_path = "/content/drive/MyDrive/northern_blades_backup"
    
    if os.path.exists("/content/drive/MyDrive"):
        print(f"    Google Drive detected! Backing up dataset...")
        os.makedirs(drive_path, exist_ok=True)
        
        # Zip the raw dataset to save space/inodes on Drive
        zip_path = "/content/northern_blades_dataset"
        print(f"    Compressing dataset to {zip_path}.zip...")
        shutil.make_archive(zip_path, 'zip', "northern_blades_dataset")
        
        # Copy to Drive
        dest = os.path.join(drive_path, "northern_blades_dataset.zip")
        print(f"    Copying to {dest}...")
        shutil.copy2(f"{zip_path}.zip", dest)
        print(f"    ✅ Backup complete! Your data is safe in Google Drive.")
        print(f"    Next time, you can just extract this zip instead of re-downloading.")
    else:
        print(f"    ⚠️ Google Drive not mounted. Skipping backup.")
        print(f"    (Run: from google.colab import drive; drive.mount('/content/drive'))")


if __name__ == "__main__":
    main()
