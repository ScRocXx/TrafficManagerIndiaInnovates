"""
Northern Blades V6.0 — 5th Camera "God's Eye" Box Monitor
==========================================================
A specialized, lightweight script designed to run YOLO on
the 5th PTZ/overhead camera feed monitoring only the
"Shared Conflict Zone" (The Box) at the center of the
intersection.

Publishes a single metric to the backend:
    {"box_density": float, "confidence": float}

This script can run on:
    - A dedicated Jetson Nano (production)
    - The same machine as the lane cameras (demo/testing)
    - Simulated mode for testing without a real 5th camera

Usage:
    # Live camera feed:
    python edge/box_monitor.py --source rtsp://192.168.1.50/stream

    # Static image for testing:
    python edge/box_monitor.py --source testimages/box_view.jpg --once

    # Simulation mode (no camera needed):
    python edge/box_monitor.py --simulate
"""

import argparse
import json
import os
import sys
import time
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

# ── Configuration ─────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000/api/box"
POLL_INTERVAL = 2        # Seconds between density updates
BOX_ROI_CONFIG = os.path.join(SCRIPT_DIR, "roi_config.json")


# ==================================================================
#  SIMULATION MODE (No camera needed — for testing)
# ==================================================================

def run_simulation():
    """
    Simulates a 5th camera by cycling through different
    box density scenarios for testing the engine's state machine.
    """
    print("[BOX MONITOR] Running in SIMULATION mode")
    print(f"[BOX MONITOR] Publishing to {BACKEND_URL}")
    print()

    scenarios = [
        {"name": "Empty Box",         "density": 0.0,  "duration": 10},
        {"name": "Light Traffic",     "density": 20.0, "duration": 8},
        {"name": "Moderate Traffic",  "density": 50.0, "duration": 8},
        {"name": "Heavy Traffic",     "density": 80.0, "duration": 6},
        {"name": "GRIDLOCK!",         "density": 97.0, "duration": 10},
        {"name": "Clearing...",       "density": 85.0, "duration": 6},
        {"name": "Recovery",          "density": 72.0, "duration": 6},
        {"name": "Clear",             "density": 10.0, "duration": 8},
    ]

    while True:
        for scenario in scenarios:
            print(f"[SIM] {scenario['name']}: Box Density = {scenario['density']:.0f}%")
            payload = {
                "box_density": scenario["density"],
                "confidence": 0.95,
            }

            try:
                resp = requests.post(BACKEND_URL, json=payload, timeout=3)
                result = resp.json()
                print(f"  → Server: {result.get('status', 'unknown')}")
            except requests.exceptions.RequestException as e:
                print(f"  → [ERROR] Backend unreachable: {e}")

            # Hold this density for the specified duration
            for _ in range(scenario["duration"]):
                time.sleep(1)
                try:
                    requests.post(BACKEND_URL, json=payload, timeout=3)
                except Exception:
                    pass


# ==================================================================
#  LIVE MODE (Real camera + YOLO)
# ==================================================================

def run_live(source, once=False):
    """
    Run YOLO on the 5th camera feed and calculate box density
    based on the ROI polygon defined in roi_config.json.
    """
    try:
        import cv2
        import numpy as np
        from ultralytics import YOLO
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("  Install with: pip install ultralytics opencv-python numpy")
        sys.exit(1)

    # ── Load model ────────────────────────────────────────────────
    model_path = os.path.join(ROOT_DIR, "dataset", "best.pt")
    if not os.path.exists(model_path):
        print(f"[ERROR] Model not found: {model_path}")
        sys.exit(1)

    print(f"[BOX MONITOR] Loading model: {model_path}")
    model = YOLO(model_path)

    # ── Load Box ROI (if defined) ─────────────────────────────────
    box_roi = None
    if os.path.exists(BOX_ROI_CONFIG):
        with open(BOX_ROI_CONFIG, "r") as f:
            config = json.load(f)
        if "Box" in config:
            zones = config["Box"].get("zones", {})
            if "incoming" in zones:
                box_roi = np.array(zones["incoming"], dtype=np.int32)
                print(f"[BOX MONITOR] Loaded Box ROI: {len(box_roi)} points")

    # ── Open video source ─────────────────────────────────────────
    cap = cv2.VideoCapture(source if not source.isdigit() else int(source))
    if not cap.isOpened():
        print(f"[ERROR] Cannot open source: {source}")
        sys.exit(1)

    print(f"[BOX MONITOR] Monitoring: {source}")
    print(f"[BOX MONITOR] Publishing to {BACKEND_URL} every {POLL_INTERVAL}s")

    frame_count = 0
    last_publish = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            if once:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_count += 1
        now = time.time()

        # Only process every POLL_INTERVAL seconds
        if now - last_publish < POLL_INTERVAL and not once:
            continue

        # ── Run YOLO ──────────────────────────────────────────────
        results = model(frame, verbose=False, conf=0.35)
        detections = results[0].boxes if results else []

        # Calculate average confidence
        confs = [float(d.conf[0]) for d in detections] if detections else []
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        # ── Count vehicles in Box ROI ─────────────────────────────
        total_vehicles = 0
        vehicles_in_box = 0

        for det in detections:
            total_vehicles += 1
            if box_roi is not None:
                # Use bottom-center of bounding box as anchor
                x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
                anchor_x = int((x1 + x2) / 2)
                anchor_y = int(y2)
                if cv2.pointPolygonTest(box_roi, (anchor_x, anchor_y), False) >= 0:
                    vehicles_in_box += 1
            else:
                vehicles_in_box += 1  # No ROI = count all

        # ── Calculate density ─────────────────────────────────────
        if box_roi is not None:
            roi_area = cv2.contourArea(box_roi)
            # Approximate: each vehicle occupies ~2000 sq pixels
            max_capacity = max(roi_area / 2000, 1)
            density = min((vehicles_in_box / max_capacity) * 100, 100)
        else:
            # Fallback: use frame area
            h, w = frame.shape[:2]
            max_capacity = max((h * w) / 5000, 1)
            density = min((total_vehicles / max_capacity) * 100, 100)

        # ── Publish ───────────────────────────────────────────────
        payload = {
            "box_density": round(density, 1),
            "confidence": round(avg_conf, 2),
        }

        try:
            resp = requests.post(BACKEND_URL, json=payload, timeout=3)
            status = resp.json().get("status", "unknown")
            print(f"[BOX] Density={density:.1f}% | Vehicles={vehicles_in_box} | "
                  f"Conf={avg_conf:.2f} → {status}")
        except requests.exceptions.RequestException as e:
            print(f"[BOX] Density={density:.1f}% | [ERROR] Backend: {e}")

        last_publish = now

        if once:
            break

    cap.release()


# ==================================================================
#  ENTRY POINT
# ==================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Northern Blades V6.0 — 5th Camera Box Monitor"
    )
    parser.add_argument("--source", default=None,
                        help="Video source (RTSP URL, file path, or camera index)")
    parser.add_argument("--once", action="store_true",
                        help="Process single frame and exit")
    parser.add_argument("--simulate", action="store_true",
                        help="Run in simulation mode (no camera needed)")
    args = parser.parse_args()

    if args.simulate:
        run_simulation()
    elif args.source:
        run_live(args.source, once=args.once)
    else:
        print("[BOX MONITOR] No source specified. Use --simulate for testing.")
        print("  python edge/box_monitor.py --simulate")
        print("  python edge/box_monitor.py --source rtsp://ip/stream")
        print("  python edge/box_monitor.py --source testimages/box.jpg --once")
