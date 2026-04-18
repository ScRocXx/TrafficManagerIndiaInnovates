"""
Northern Blades — Step 5: Train YOLOv11m-seg
Instance Segmentation training for Fluid Mass traffic analytics.

*** RUN THIS ON GOOGLE COLAB WITH GPU (T4/A100) ***

Setup on Colab:
  !pip install ultralytics albumentations
"""

import os
import sys

# ─── CONFIG ───────────────────────────────────────────────────────────────────
MODEL = "yolo11m-seg.pt"           # Medium segmentation model
DATASET_YAML = "dataset/data.yaml"
PROJECT_NAME = "northern_blades"
RUN_NAME = "v1_medium_640"

# Training hyperparameters
EPOCHS = 200
IMGSZ = 640                        # 640 for reliable FPS on Orin Nano
                                   # Change to 1024 ONLY if FPS is confirmed ≥15
BATCH = 16                         # Reduce to 8 if OOM on T4
OPTIMIZER = "AdamW"
LR0 = 0.01
LRF = 0.01
WARMUP_EPOCHS = 5
PATIENCE = 30                      # Early stopping

# Augmentation (critical for Indian traffic)
MOSAIC = 1.0                       # Mandatory: simulates dense occlusion
MIXUP = 0.2                        # Blends images for overlapping vehicles
COPY_PASTE = 0.3                   # Instance copy-paste
DEGREES = 5.0                      # Slight rotation
SCALE = 0.5                        # Scale variation
FLIPUD = 0.0                       # No vertical flip (cameras are fixed)
FLIPLR = 0.5                       # Horizontal flip ok

# Segmentation-specific
OVERLAP_MASK = True                # Handle overlapping masks
MASK_RATIO = 4                     # Mask downsample ratio
# ─────────────────────────────────────────────────────────────────────────────


def check_prerequisites():
    """Verify everything is ready before training."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: Install ultralytics first: pip install ultralytics")
        sys.exit(1)

    if not os.path.exists(DATASET_YAML):
        print(f"ERROR: {DATASET_YAML} not found!")
        print("  Run 04_finalize_dataset.py first!")
        sys.exit(1)

    # Check dataset has images
    yaml_dir = os.path.dirname(DATASET_YAML)
    train_dir = os.path.join(yaml_dir, "images", "train")
    if os.path.exists(train_dir):
        count = len([f for f in os.listdir(train_dir)
                     if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
        print(f"  Train images found: {count}")
        if count < 100:
            print(f"  WARNING: Only {count} training images. Results may be poor.")
            print(f"  Recommendation: At least 1,500 images for segmentation.")
    else:
        print(f"  WARNING: {train_dir} not found!")

    return True


def main():
    print("=" * 60)
    print("Northern Blades — YOLOv11m-seg Training")
    print("Instance Segmentation for Fluid Mass Traffic Analytics")
    print("=" * 60)

    check_prerequisites()

    from ultralytics import YOLO

    # Load pretrained model
    print(f"\n[1/3] Loading {MODEL}...")
    model = YOLO(MODEL)

    # Start training
    print(f"[2/3] Starting training...")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Image size: {IMGSZ}")
    print(f"  Batch: {BATCH}")
    print(f"  Optimizer: {OPTIMIZER}")
    print(f"  Mosaic: {MOSAIC}, Mixup: {MIXUP}")
    print(f"  Early stopping patience: {PATIENCE}")
    print()

    results = model.train(
        data=os.path.abspath(DATASET_YAML),
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        optimizer=OPTIMIZER,

        # Learning rate
        lr0=LR0,
        lrf=LRF,
        warmup_epochs=WARMUP_EPOCHS,

        # Augmentation
        mosaic=MOSAIC,
        mixup=MIXUP,
        copy_paste=COPY_PASTE,
        degrees=DEGREES,
        scale=SCALE,
        flipud=FLIPUD,
        fliplr=FLIPLR,

        # Segmentation
        overlap_mask=OVERLAP_MASK,
        mask_ratio=MASK_RATIO,

        # Performance
        amp=True,
        patience=PATIENCE,
        workers=4,

        # Output
        project=PROJECT_NAME,
        name=RUN_NAME,
        exist_ok=True,
        verbose=True,
    )

    # Post-training summary
    print(f"\n{'='*60}")
    print(f"TRAINING COMPLETE!")
    print(f"{'='*60}")

    weights_dir = os.path.join(PROJECT_NAME, RUN_NAME, "weights")
    best_pt = os.path.join(weights_dir, "best.pt")

    if os.path.exists(best_pt):
        size_mb = os.path.getsize(best_pt) / (1024 * 1024)
        print(f"  Best weights: {best_pt} ({size_mb:.1f} MB)")
    else:
        print(f"  Weights directory: {weights_dir}")

    print(f"\n  Next steps:")
    print(f"  1. Check training curves in {PROJECT_NAME}/{RUN_NAME}/")
    print(f"  2. Run validation: python 06_validate.py")
    print(f"  3. Export for edge: python 07_export_tensorrt.py")

    # Export to ONNX immediately (for later TensorRT conversion on Orin)
    print(f"\n[3/3] Exporting to ONNX for TensorRT conversion...")
    try:
        model_best = YOLO(best_pt)
        model_best.export(
            format="onnx",
            imgsz=IMGSZ,
            simplify=True,
            opset=12,
        )
        onnx_path = best_pt.replace(".pt", ".onnx")
        print(f"  ONNX exported: {onnx_path}")
        print(f"\n  To convert on Jetson Orin Nano:")
        print(f"  trtexec --onnx={os.path.basename(onnx_path)} --saveEngine=best.engine --fp16")
    except Exception as e:
        print(f"  ONNX export failed: {e}")
        print(f"  You can export manually later.")


if __name__ == "__main__":
    main()

