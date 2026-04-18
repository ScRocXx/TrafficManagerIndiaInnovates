"""
Northern Blades — Step 3: SAM Mask Generator
Converts UVH-26 bounding boxes into YOLO-seg polygon masks using SAM 2.

*** RUN THIS ON GOOGLE COLAB WITH GPU (T4 or better) ***

Setup on Colab:
  !pip install segment-anything opencv-python-headless
  !wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth
"""

import os
import cv2
import json
import numpy as np
from tqdm import tqdm

# ─── CONFIG ───────────────────────────────────────────────────────────────────
# Use vit_b (Base) — 3x faster than vit_h, nearly same quality for vehicles
SAM_CHECKPOINT = "sam_vit_b_01ec64.pth"
SAM_MODEL_TYPE = "vit_b"

IMAGE_DIR = "northern_blades_dataset/images/all_raw"
ANNOTATIONS_JSON = "northern_blades_dataset/uvh26_top_annotations.json"
OUTPUT_LABEL_DIR = "northern_blades_dataset/labels/all_raw"
QC_DIR = "northern_blades_dataset/qc_samples"  # Visual QC output

MAX_POLYGON_VERTICES = 40  # Douglas-Peucker simplification target
MIN_MASK_AREA_PX = 100     # Ignore tiny masks (noise)
CONFIDENCE_THRESHOLD = 0.7 # SAM confidence cutoff
QC_SAMPLE_COUNT = 50       # Save this many visual QC images

# Northern Blades class mapping: UVH-26 category name → class ID
# ═══════════════════════════════════════════════════════════════════
# VERIFIED against official UVH-26 paper (IISc Bangalore, 14 classes)
# Primary keys = EXACT official names. Additional keys = safety aliases.
#
# ⚠️  IDs MUST match Roboflow's alphabetical export order:
#     0: Heavy_Motor, 1: Light_Motor, 2: Organic_Object,
#     3: Three_Wheeler, 4: Two_Wheeler
# ═══════════════════════════════════════════════════════════════════
CLASS_MAP = {
    # Class 0: Heavy_Motor  (Roboflow color: #C7FC00)
    "Bus": 0, "bus": 0,
    "Truck": 0, "truck": 0,
    "Mini-bus": 0, "mini-bus": 0, "Minibus": 0, "minibus": 0,
    "LCV": 0, "lcv": 0,
    "Van": 0, "van": 0,
    "Tempo-traveller": 0, "tempo-traveller": 0, "Tempo": 0, "tempo": 0,
    "Tempo Traveller": 0, "tempo traveller": 0,  # space variant

    # Class 1: Light_Motor  (Roboflow color: #8622FF)
    "Hatchback": 1, "hatchback": 1,
    "Sedan": 1, "sedan": 1,
    "SUV": 1, "suv": 1,
    "MUV": 1, "muv": 1,
    "Car": 1, "car": 1,                    # alias safety net

    # Class 2: Organic_Object  (Roboflow color: #FF8000)
    # (from custom YouTube data, not in UVH-26)
    "Pedestrian": 2, "pedestrian": 2,
    "Person": 2, "person": 2,

    # Class 3: Three_Wheeler  (Roboflow color: #FE0056)
    # OFFICIAL UVH-26 NAME: "3-Wheeler (Auto-rickshaw)"
    "3-Wheeler (Auto-rickshaw)": 3,         # ← EXACT official UVH-26 name
    "3-Wheeler": 3, "3-wheeler": 3,         # short form
    "Three-wheeler": 3, "three-wheeler": 3, # word form
    "Auto-rickshaw": 3, "auto-rickshaw": 3, # common alias
    "Auto": 3, "auto": 3,
    "E-rickshaw": 3, "e-rickshaw": 3,
    "Rickshaw": 3, "rickshaw": 3,

    # Class 4: Two_Wheeler  (Roboflow color: #00FFCE)
    # OFFICIAL UVH-26 NAME: "2-Wheeler (Motorcycle)"
    "2-Wheeler (Motorcycle)": 4,            # ← EXACT official UVH-26 name
    "2-Wheeler": 4, "2-wheeler": 4,         # short form
    "Two-wheeler": 4, "two-wheeler": 4,     # word form
    "Two Wheeler": 4, "two wheeler": 4,     # space variant
    "Motorcycle": 4, "motorcycle": 4,
    "Motorbike": 4, "motorbike": 4,
    "Bike": 4, "bike": 4,
    "Scooter": 4, "scooter": 4,
    "Cycle": 4, "cycle": 4,                 # ← EXACT official UVH-26 name
    "Bicycle": 4, "bicycle": 4,

    # "Other" category is SKIPPED (not mapped)
}
# ─────────────────────────────────────────────────────────────────────────────


def mask_to_yolo_polygon(binary_mask, img_h, img_w, epsilon_factor=0.005):
    """Convert a binary mask to a YOLO-seg polygon (normalized coordinates)."""
    contours, _ = cv2.findContours(
        binary_mask.astype(np.uint8),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return None

    # Take the largest contour
    contour = max(contours, key=cv2.contourArea)

    # Check minimum area
    if cv2.contourArea(contour) < MIN_MASK_AREA_PX:
        return None

    # Simplify polygon (Douglas-Peucker)
    perimeter = cv2.arcLength(contour, True)
    epsilon = epsilon_factor * perimeter
    simplified = cv2.approxPolyDP(contour, epsilon, True)

    # If still too many points, increase epsilon
    while len(simplified) > MAX_POLYGON_VERTICES and epsilon_factor < 0.05:
        epsilon_factor *= 1.5
        epsilon = epsilon_factor * perimeter
        simplified = cv2.approxPolyDP(contour, epsilon, True)

    # Need at least 3 points for a polygon
    if len(simplified) < 3:
        return None

    # Normalize to [0, 1]
    points = simplified.reshape(-1, 2)
    normalized = []
    for x, y in points:
        normalized.append(x / img_w)
        normalized.append(y / img_h)

    return normalized


def draw_qc_image(image, polygons_with_classes, class_names):
    """Draw masks on image for quality control inspection."""
    overlay = image.copy()
    # BGR colors matching Roboflow annotation colors for visual consistency
    colors = {
        0: (0, 252, 199),   # Heavy_Motor:     #C7FC00 → BGR
        1: (255, 34, 134),  # Light_Motor:     #8622FF → BGR
        2: (0, 128, 255),   # Organic_Object:  #FF8000 → BGR
        3: (86, 0, 254),    # Three_Wheeler:   #FE0056 → BGR
        4: (206, 255, 0),   # Two_Wheeler:     #00FFCE → BGR
    }

    for cls_id, polygon_norm in polygons_with_classes:
        h, w = image.shape[:2]
        pts = []
        for i in range(0, len(polygon_norm), 2):
            px = int(polygon_norm[i] * w)
            py = int(polygon_norm[i + 1] * h)
            pts.append([px, py])
        pts = np.array(pts, dtype=np.int32)

        color = colors.get(cls_id, (255, 255, 255))
        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(overlay, [pts], True, color, 2)

    # Blend overlay
    result = cv2.addWeighted(image, 0.6, overlay, 0.4, 0)

    # Add legend
    y_offset = 30
    for cls_id, name in class_names.items():
        color = colors.get(cls_id, (255, 255, 255))
        cv2.putText(result, f"{cls_id}: {name}", (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        y_offset += 25

    return result


def main():
    os.makedirs(OUTPUT_LABEL_DIR, exist_ok=True)
    os.makedirs(QC_DIR, exist_ok=True)

    # 1. Load SAM
    print("[Step 1/5] Loading SAM model...")
    try:
        from segment_anything import sam_model_registry, SamPredictor
    except ImportError:
        print("ERROR: Install segment-anything first:")
        print("  pip install segment-anything")
        print("  wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth")
        return

    sam = sam_model_registry[SAM_MODEL_TYPE](checkpoint=SAM_CHECKPOINT)
    device = "cuda"
    try:
        import torch
        if not torch.cuda.is_available():
            print("WARNING: No GPU detected. SAM will be VERY slow on CPU.")
            device = "cpu"
    except ImportError:
        device = "cpu"
    sam.to(device=device)
    predictor = SamPredictor(sam)

    # 2. Load annotations
    print("[Step 2/5] Loading UVH-26 annotations...")
    if not os.path.exists(ANNOTATIONS_JSON):
        print(f"ERROR: {ANNOTATIONS_JSON} not found.")
        print("  Run 01_download_uvh26.py first!")
        return

    with open(ANNOTATIONS_JSON, 'r') as f:
        coco = json.load(f)

    # Build category ID → name map
    cat_id_to_name = {cat['id']: cat['name'] for cat in coco['categories']}

    # ═══ DIAGNOSTIC: Verify all UVH-26 categories are mapped ═══
    print(f"\n    UVH-26 Categories Found in JSON:")
    unmapped = []
    for cat in coco['categories']:
        original_name = cat['name']
        name = original_name.strip()
        
        # 1. Try exact match
        mapped = CLASS_MAP.get(name)
        
        # 2. Try case-insensitive fallback if exact fails
        if mapped is None:
            for k, v in CLASS_MAP.items():
                if k.lower() == name.lower():
                    mapped = v
                    break

        if mapped is not None:
            nb_class = {0: "Heavy_Motor", 1: "Light_Motor", 2: "Organic_Object",
                       3: "Three_Wheeler", 4: "Two_Wheeler"}[mapped]
            print(f"      ✓ '{original_name}' → {mapped} ({nb_class})")
        elif name.lower() in ['other', 'others']:
            print(f"      ⊘ '{original_name}' → SKIPPED (intentional)")
        else:
            unmapped.append(name)
            print(f"      ✗ '{name}' → *** UNMAPPED! ***")

    if unmapped:
        print(f"\n    ⚠️  WARNING: {len(unmapped)} category(ies) NOT MAPPED!")
        print(f"    These vehicles will be SKIPPED in training!")
        print(f"    Unmapped: {unmapped}")
        print(f"    Add them to CLASS_MAP in 03_sam_mask_generator.py\n")
        # Count how many annotations would be lost
        lost = sum(1 for ann in coco['annotations']
                   if cat_id_to_name.get(ann['category_id'], '') in unmapped)
        print(f"    Annotations that would be lost: {lost}")
        resp = input("    Continue anyway? (y/n): ").strip().lower()
        if resp != 'y':
            print("    Aborted. Fix CLASS_MAP first.")
            return
    else:
        print(f"\n    ✓ All {len(coco['categories'])} UVH-26 categories are mapped!")
    # ═══ END DIAGNOSTIC ═══

    # Build image ID → annotations map
    img_to_anns = {}
    for ann in coco['annotations']:
        img_to_anns.setdefault(ann['image_id'], []).append(ann)

    # Build image ID → info map
    img_id_to_info = {img['id']: img for img in coco['images']}

    class_names = {
        0: "Heavy_Motor", 1: "Light_Motor", 2: "Organic_Object",
        3: "Three_Wheeler", 4: "Two_Wheeler"
    }

    # 3. Process each image
    print("[Step 3/5] Generating SAM masks...")

    # Get list of images that exist on disk
    available_images = []
    for img_info in coco['images']:
        img_path = os.path.join(IMAGE_DIR, img_info['file_name'])
        if os.path.exists(img_path):
            available_images.append(img_info)

    print(f"    Found {len(available_images)} images on disk (out of {len(coco['images'])} in JSON).")

    stats = {"processed": 0, "masks_generated": 0, "masks_failed": 0, "images_skipped": 0}
    qc_count = 0

    for img_info in tqdm(available_images, desc="SAM Processing"):
        img_path = os.path.join(IMAGE_DIR, img_info['file_name'])
        image = cv2.imread(img_path)

        if image is None:
            stats["images_skipped"] += 1
            continue

        h, w = image.shape[:2]
        predictor.set_image(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        anns = img_to_anns.get(img_info['id'], [])
        yolo_lines = []
        qc_polygons = []

        for ann in anns:
            # Get category and map to Northern Blades class
            cat_name = cat_id_to_name.get(ann['category_id'], 'Other')
            cls_id = CLASS_MAP.get(cat_name)
            if cls_id is None:
                # Try case-insensitive match
                for key, val in CLASS_MAP.items():
                    if key.lower() == cat_name.lower():
                        cls_id = val
                        break
            if cls_id is None:
                continue  # Skip unknown categories

            # Get bounding box [x, y, w, h] → [x1, y1, x2, y2]
            bx, by, bw, bh = ann['bbox']
            input_box = np.array([bx, by, bx + bw, by + bh])

            # Run SAM
            try:
                masks, scores, _ = predictor.predict(
                    box=input_box,
                    multimask_output=True
                )

                # Take highest confidence mask
                best_idx = np.argmax(scores)
                best_score = scores[best_idx]

                if best_score < CONFIDENCE_THRESHOLD:
                    stats["masks_failed"] += 1
                    continue

                best_mask = masks[best_idx]

                # Convert to YOLO polygon
                polygon = mask_to_yolo_polygon(best_mask, h, w)
                if polygon is None:
                    stats["masks_failed"] += 1
                    continue

                # Format: class_id x1 y1 x2 y2 ... xn yn
                coords_str = " ".join(f"{v:.6f}" for v in polygon)
                yolo_lines.append(f"{cls_id} {coords_str}")
                qc_polygons.append((cls_id, polygon))
                stats["masks_generated"] += 1

            except Exception:
                stats["masks_failed"] += 1
                continue

        # Save YOLO label file
        if yolo_lines:
            label_name = os.path.splitext(img_info['file_name'])[0] + ".txt"
            label_path = os.path.join(OUTPUT_LABEL_DIR, label_name)
            with open(label_path, 'w') as f:
                f.write("\n".join(yolo_lines))

            # Save QC sample
            if qc_count < QC_SAMPLE_COUNT:
                qc_img = draw_qc_image(image, qc_polygons, class_names)
                qc_path = os.path.join(QC_DIR, f"qc_{img_info['file_name']}")
                cv2.imwrite(qc_path, qc_img)
                qc_count += 1

        stats["processed"] += 1

    # 4. Print summary
    print(f"\n{'='*50}")
    print(f"SAM MASK GENERATION COMPLETE")
    print(f"{'='*50}")
    print(f"  Images processed:  {stats['processed']}")
    print(f"  Images skipped:    {stats['images_skipped']}")
    print(f"  Masks generated:   {stats['masks_generated']}")
    print(f"  Masks failed:      {stats['masks_failed']}")
    print(f"  Success rate:      {stats['masks_generated']/(stats['masks_generated']+stats['masks_failed'])*100:.1f}%")
    print(f"\n  Labels saved to:   {OUTPUT_LABEL_DIR}")
    print(f"  QC samples saved:  {QC_DIR} ({qc_count} images)")
    print(f"\n  >>> IMPORTANT: Review the QC images in {QC_DIR}")
    print(f"  >>> Fix bad masks in CVAT or Roboflow before training!")


if __name__ == "__main__":
    main()
