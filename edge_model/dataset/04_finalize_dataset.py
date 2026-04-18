"""
Northern Blades — Step 4: Finalize Dataset
Splits data into train/val, verifies integrity, and creates YOLO config.

Usage:
  python 04_finalize_dataset.py
"""

import os
import random
import shutil
from collections import Counter
from pathlib import Path

# ─── CONFIG ───────────────────────────────────────────────────────────────────
RAW_IMAGES_DIR = "dataset/images/all_raw"
RAW_LABELS_DIR = "dataset/labels/all_raw"

TRAIN_IMAGES_DIR = "dataset/images/train"
TRAIN_LABELS_DIR = "dataset/labels/train"
VAL_IMAGES_DIR = "dataset/images/val"
VAL_LABELS_DIR = "dataset/labels/val"

YAML_OUTPUT = "dataset/data.yaml"

TRAIN_RATIO = 0.9  # 90% train, 10% val
SEED = 42

CLASS_NAMES = {
    0: "Heavy_Motor",
    1: "Light_Motor",
    2: "Organic_Object",
    3: "Three_Wheeler",
    4: "Two_Wheeler",
}
# ─────────────────────────────────────────────────────────────────────────────


def get_matching_pairs(images_dir, labels_dir):
    """Find images that have matching label files."""
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}

    # Get all images
    image_files = {}
    for f in os.listdir(images_dir):
        stem = Path(f).stem
        ext = Path(f).suffix.lower()
        if ext in image_exts:
            image_files[stem] = f

    # Get all labels
    label_files = {}
    for f in os.listdir(labels_dir):
        if f.endswith('.txt'):
            stem = Path(f).stem
            label_files[stem] = f

    # Find matching pairs
    pairs = []
    for stem in image_files:
        if stem in label_files:
            pairs.append((image_files[stem], label_files[stem]))

    return pairs


def analyze_labels(labels_dir, label_files):
    """Count class distribution across all label files."""
    class_counts = Counter()
    total_objects = 0
    empty_labels = 0

    for label_file in label_files:
        filepath = os.path.join(labels_dir, label_file)
        with open(filepath, 'r') as f:
            lines = f.readlines()

        if not lines:
            empty_labels += 1
            continue

        for line in lines:
            parts = line.strip().split()
            if parts:
                cls_id = int(parts[0])
                class_counts[cls_id] += 1
                total_objects += 1

    return class_counts, total_objects, empty_labels


def main():
    print("=" * 50)
    print("Northern Blades — Dataset Finalizer")
    print("=" * 50)

    # 1. Check raw data exists
    if not os.path.exists(RAW_IMAGES_DIR):
        print(f"ERROR: {RAW_IMAGES_DIR} not found. Run steps 1-3 first!")
        return

    if not os.path.exists(RAW_LABELS_DIR):
        print(f"ERROR: {RAW_LABELS_DIR} not found. Run step 3 (SAM) first!")
        return

    # 2. Find matching image-label pairs
    print("\n[Step 1/4] Finding image-label pairs...")
    pairs = get_matching_pairs(RAW_IMAGES_DIR, RAW_LABELS_DIR)
    print(f"    Found {len(pairs)} matched image-label pairs.")

    total_images = len(os.listdir(RAW_IMAGES_DIR))
    total_labels = len([f for f in os.listdir(RAW_LABELS_DIR) if f.endswith('.txt')])
    unmatched = total_images - len(pairs)
    if unmatched > 0:
        print(f"    WARNING: {unmatched} images have no label file (unlabeled YouTube frames?)")
        print(f"    These will be SKIPPED. Label them in Roboflow first.")

    if len(pairs) < 100:
        print(f"    WARNING: Only {len(pairs)} pairs. You need at least 500+ for decent results.")

    # 3. Analyze class distribution
    print("\n[Step 2/4] Analyzing class distribution...")
    label_files = [p[1] for p in pairs]
    class_counts, total_objects, empty_labels = analyze_labels(RAW_LABELS_DIR, label_files)

    print(f"\n    Total objects: {total_objects}")
    print(f"    Empty labels:  {empty_labels}")
    print(f"\n    Class Distribution:")
    print(f"    {'Class':<20} {'Count':<10} {'Percentage':<10}")
    print(f"    {'-'*40}")
    for cls_id in sorted(CLASS_NAMES.keys()):
        count = class_counts.get(cls_id, 0)
        pct = (count / total_objects * 100) if total_objects > 0 else 0
        name = CLASS_NAMES[cls_id]
        bar = "█" * int(pct / 2)
        print(f"    {cls_id}: {name:<16} {count:<10} {pct:>5.1f}% {bar}")

    # Warn about missing classes
    missing = [CLASS_NAMES[c] for c in CLASS_NAMES if class_counts.get(c, 0) == 0]
    if missing:
        print(f"\n    ⚠️  MISSING CLASSES: {', '.join(missing)}")
        print(f"    You need to add training data for these from YouTube/custom sources!")

    # 4. Split into train/val
    print(f"\n[Step 3/4] Splitting dataset ({TRAIN_RATIO*100:.0f}/{(1-TRAIN_RATIO)*100:.0f})...")

    random.seed(SEED)
    random.shuffle(pairs)

    split_idx = int(len(pairs) * TRAIN_RATIO)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]

    # Create directories
    for d in [TRAIN_IMAGES_DIR, TRAIN_LABELS_DIR, VAL_IMAGES_DIR, VAL_LABELS_DIR]:
        os.makedirs(d, exist_ok=True)

    # Copy files
    for img_file, lbl_file in train_pairs:
        shutil.copy2(os.path.join(RAW_IMAGES_DIR, img_file),
                     os.path.join(TRAIN_IMAGES_DIR, img_file))
        shutil.copy2(os.path.join(RAW_LABELS_DIR, lbl_file),
                     os.path.join(TRAIN_LABELS_DIR, lbl_file))

    for img_file, lbl_file in val_pairs:
        shutil.copy2(os.path.join(RAW_IMAGES_DIR, img_file),
                     os.path.join(VAL_IMAGES_DIR, img_file))
        shutil.copy2(os.path.join(RAW_LABELS_DIR, lbl_file),
                     os.path.join(VAL_LABELS_DIR, lbl_file))

    print(f"    Train: {len(train_pairs)} images")
    print(f"    Val:   {len(val_pairs)} images")

    # 5. Generate YOLO config YAML
    print(f"\n[Step 4/4] Generating YOLO config...")

    dataset_root = os.path.abspath("dataset")
    yaml_content = f"""# Northern Blades — YOLO Instance Segmentation Config
# Generated automatically by 04_finalize_dataset.py

path: {dataset_root}
train: images/train
val: images/val

# 5-Class Northern Blades Taxonomy (alphabetical — matches Roboflow export)
names:
  0: Heavy_Motor
  1: Light_Motor
  2: Organic_Object
  3: Three_Wheeler
  4: Two_Wheeler

# Dataset stats (auto-generated):
# Total pairs: {len(pairs)}
# Train: {len(train_pairs)}
# Val: {len(val_pairs)}
# Total objects: {total_objects}
"""

    with open(YAML_OUTPUT, 'w') as f:
        f.write(yaml_content)

    print(f"    Config saved to: {YAML_OUTPUT}")

    # Final summary
    print(f"\n{'='*50}")
    print(f"DATASET READY!")
    print(f"{'='*50}")
    print(f"  Train: {len(train_pairs)} images → {TRAIN_IMAGES_DIR}")
    print(f"  Val:   {len(val_pairs)} images → {VAL_IMAGES_DIR}")
    print(f"  Config: {YAML_OUTPUT}")
    print(f"\n  Next step: Run 05_train.py to start training!")


if __name__ == "__main__":
    main()
