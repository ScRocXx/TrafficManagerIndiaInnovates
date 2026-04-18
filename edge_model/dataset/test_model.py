"""
Quick test: Load best.pt and run inference on image.png
Diagnose why polygons are not being drawn.
"""
import sys
import os

try:
    from ultralytics import YOLO
    import ultralytics
    print(f"[OK] ultralytics version: {ultralytics.__version__}")
    print(f"    Expected classes: 5 (Heavy_Motor, Light_Motor, Organic_Object, Three_Wheeler, Two_Wheeler)")
except ImportError:
    print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
    sys.exit(1)

MODEL_PATH = r"c:\traffic_optimizers\dataset\best.pt"
IMAGE_PATH = r"c:\traffic_optimizers\dataset\image.png"

print(f"\n{'='*60}")
print(f"NORTHERN BLADES — MODEL DIAGNOSTIC")
print(f"{'='*60}")

# 1. Check files exist
print(f"\n[1] File Check:")
print(f"    Model: {MODEL_PATH} — {'EXISTS' if os.path.exists(MODEL_PATH) else 'MISSING!'}")
print(f"    Image: {IMAGE_PATH} — {'EXISTS' if os.path.exists(IMAGE_PATH) else 'MISSING!'}")

if not os.path.exists(MODEL_PATH) or not os.path.exists(IMAGE_PATH):
    print("    FATAL: Files missing!")
    sys.exit(1)

size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
print(f"    Model size: {size_mb:.1f} MB")

# 2. Load model and inspect
print(f"\n[2] Loading model...")
model = YOLO(MODEL_PATH)

print(f"    Model task: {model.task}")
print(f"    Classes: {model.names}")
print(f"    Number of classes: {len(model.names)}")

# CRITICAL CHECK
if model.task != 'segment':
    print(f"\n    *** PROBLEM FOUND! ***")
    print(f"    Model task is '{model.task}', NOT 'segment'!")
    print(f"    This model does DETECTION only (bounding boxes), NOT SEGMENTATION (polygons).")
    print(f"    To get polygons, train with a '-seg' model (e.g., yolo11m-seg.pt)")
else:
    print(f"    OK: Model IS a segmentation model.")

# 3. Run inference
print(f"\n[3] Running inference...")
results = model(IMAGE_PATH, conf=0.18, iou=0.6, verbose=True)
result = results[0]

# 4. Analyze
print(f"\n[4] Results:")
print(f"    Detections: {len(result.boxes)}")

if len(result.boxes) == 0:
    print(f"\n    *** Zero detections at conf=0.25! ***")
    print(f"    Retrying with conf=0.05...")
    results_low = model(IMAGE_PATH, conf=0.05, verbose=False)
    low_count = len(results_low[0].boxes)
    print(f"    Detections at conf=0.05: {low_count}")
    if low_count > 0:
        for i, box in enumerate(results_low[0].boxes[:5]):
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls_id]
            print(f"      [{i}] {name}: {conf:.3f}")
        result = results_low[0]  # Use low-conf results for output
else:
    for i, box in enumerate(result.boxes[:10]):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        name = model.names[cls_id]
        print(f"      [{i}] {name}: conf={conf:.3f}")

# 5. Mask check
print(f"\n[5] Segmentation Masks:")
if result.masks is not None:
    print(f"    Masks present: {len(result.masks)}")
    print(f"    Mask data shape: {result.masks.data.shape}")
    if hasattr(result.masks, 'xy') and result.masks.xy is not None:
        for i, poly in enumerate(result.masks.xy[:3]):
            print(f"      Mask {i}: {len(poly)} vertices")
else:
    print(f"    NO MASKS!")
    if model.task == 'segment':
        print(f"    Segmentation model but no masks — likely zero detections.")
    else:
        print(f"    Model is '{model.task}' — can't produce polygons.")

# 6. Save output
print(f"\n[6] Saving annotated output...")
import cv2
output_path = r"c:\traffic_optimizers\dataset\test_output.jpg"
annotated = result.plot(boxes=False)
cv2.imwrite(output_path, annotated)
print(f"    Saved: {output_path}")

# 7. Summary
print(f"\n{'='*60}")
print(f"DIAGNOSIS")
print(f"{'='*60}")
if model.task != 'segment':
    print(f"  ROOT CAUSE: Model is '{model.task}', not 'segment'.")
    print(f"  FIX: Train with YOLO('yolo11m-seg.pt') instead of YOLO('yolo11m.pt')")
elif len(result.boxes) == 0:
    print(f"  ROOT CAUSE: No detections — model doesn't recognize this scene.")
    print(f"  FIX: Retrain with more diverse Indian traffic data.")
elif result.masks is None:
    print(f"  ROOT CAUSE: Detections exist but no masks. Possible export issue.")
else:
    print(f"  MODEL WORKS! Check test_output.jpg")
