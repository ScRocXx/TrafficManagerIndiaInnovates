"""
Northern Blades — Step 6: Validate Trained Model
Runs validation on the trained model and generates per-class metrics.

Usage:
  python 06_validate.py
"""

import os
import sys

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BEST_WEIGHTS = "northern_blades/v1_medium_640/weights/best.pt"
DATASET_YAML = "northern_blades_dataset/northern_blades.yaml"
IMGSZ = 640
CONF_THRESHOLD = 0.45
IOU_THRESHOLD = 0.5
# ─────────────────────────────────────────────────────────────────────────────


def main():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: pip install ultralytics")
        sys.exit(1)

    if not os.path.exists(BEST_WEIGHTS):
        print(f"ERROR: {BEST_WEIGHTS} not found. Train first with 05_train.py!")
        sys.exit(1)

    print("=" * 60)
    print("Northern Blades — Model Validation")
    print("=" * 60)

    model = YOLO(BEST_WEIGHTS)

    print("\n[1/2] Running validation on val set...")
    results = model.val(
        data=os.path.abspath(DATASET_YAML),
        imgsz=IMGSZ,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
        split="val",
        verbose=True,
    )

    # Extract key metrics
    print(f"\n{'='*60}")
    print(f"VALIDATION RESULTS")
    print(f"{'='*60}")

    class_names = ["Heavy_Motor", "Light_Motor", "Organic_Object",
                   "Three_Wheeler", "Two_Wheeler"]

    # Box metrics
    print(f"\n  Box Detection Metrics:")
    print(f"    mAP@50:     {results.box.map50:.4f}")
    print(f"    mAP@50-95:  {results.box.map:.4f}")

    # Mask metrics
    print(f"\n  Mask Segmentation Metrics:")
    print(f"    mAP@50:     {results.seg.map50:.4f}")
    print(f"    mAP@50-95:  {results.seg.map:.4f}")

    # Per-class breakdown
    if hasattr(results.seg, 'ap50') and results.seg.ap50 is not None:
        print(f"\n  Per-Class Mask AP@50:")
        print(f"    {'Class':<20} {'AP@50':<10} {'Status'}")
        print(f"    {'-'*45}")
        for i, name in enumerate(class_names):
            if i < len(results.seg.ap50):
                ap = results.seg.ap50[i]
                status = "✅" if ap > 0.5 else "⚠️ NEEDS MORE DATA" if ap > 0.2 else "❌ FAILING"
                print(f"    {name:<20} {ap:.4f}     {status}")

    # Recommendations
    print(f"\n  Recommendations:")
    mask_map = results.seg.map50
    if mask_map >= 0.70:
        print(f"    ✅ Model is GOOD (mask mAP@50 = {mask_map:.3f}). Ready for deployment.")
    elif mask_map >= 0.50:
        print(f"    ⚠️  Model is OKAY (mask mAP@50 = {mask_map:.3f}).")
        print(f"    Consider: more data, longer training, or larger augmentation.")
    else:
        print(f"    ❌ Model is POOR (mask mAP@50 = {mask_map:.3f}).")
        print(f"    Actions needed:")
        print(f"      1. Add more training images (target 2000+)")
        print(f"      2. Check SAM mask quality in qc_samples/")
        print(f"      3. Increase epochs or reduce learning rate")

    # Speed test
    print(f"\n[2/2] Speed test...")
    speed_results = model.val(
        data=os.path.abspath(DATASET_YAML),
        imgsz=IMGSZ,
        batch=1,
        verbose=False,
    )

    if hasattr(speed_results, 'speed'):
        preprocess = speed_results.speed.get('preprocess', 0)
        inference = speed_results.speed.get('inference', 0)
        postprocess = speed_results.speed.get('postprocess', 0)
        total = preprocess + inference + postprocess
        fps = 1000 / total if total > 0 else 0
        print(f"    Preprocess:  {preprocess:.1f} ms")
        print(f"    Inference:   {inference:.1f} ms")
        print(f"    Postprocess: {postprocess:.1f} ms")
        print(f"    Total:       {total:.1f} ms ({fps:.1f} FPS)")
        print(f"\n    Note: This is on current hardware (likely Colab GPU).")
        print(f"    Jetson Orin Nano with TRT FP16 will be ~2-3x slower.")
        estimated_edge_fps = fps / 2.5
        print(f"    Estimated Orin Nano FPS: ~{estimated_edge_fps:.0f} FPS")
        if estimated_edge_fps < 15:
            print(f"    ⚠️  Below 15 FPS target! Consider dropping to imgsz=480 or yolo11s-seg.")


if __name__ == "__main__":
    main()
