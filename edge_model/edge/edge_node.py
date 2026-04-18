"""
Northern Blades — Production Edge Node
=========================================
The SINGLE production edge pipeline:
    Camera/Video → YOLOv11m-seg → Geometry Engine → REST API → Backend

Replaces: v6_demo.py, simulator.py, four_lane_demo.py, inference_pipeline.py

Architecture:
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ CAM-001  │  │ CAM-002  │  │ CAM-003  │  │ CAM-004  │
    │ (North)  │  │ (South)  │  │ (East)   │  │ (West)   │
    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
         └─────────┬───┴─────────┬───┘              │
                   ▼             ▼                   ▼
            YOLO Batch Inference (YOLOv11m-seg)
                   │
                   ▼
    ┌──────────────────────────────────────────────────────┐
    │  Geometry Engine (per-lane)                          │
    │  • Occlusion Filter                                 │
    │  • Single-Point Anchor → Undistort → BEV Warp       │
    │  • Synthetic Footprint Injection (anti-overlap)      │
    │  • Fluid Mass % = filled_px / canvas_area × 100     │
    └──────────────────────────────────────────────────────┘
                   │
                   ▼
    REST API → Backend (/api/telemetry, /api/box, /api/latency)
                   │
                   ▼
    Dashboard WebSocket → Live camera feeds + engine state

Usage:
    python edge/edge_node.py --no-display
    python edge/edge_node.py --fps 2 --save output.mp4
"""

import argparse
import json
import time
import os
import sys
import base64
import numpy as np
import cv2
import requests

# ── Path Resolution ───────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ── Geometry Engine ───────────────────────────────────────────────
from geometry_engine import NorthernBladesGeometryEngine

# ── Paths ─────────────────────────────────────────────────────────
TEST_DIR = os.path.join(ROOT_DIR, "testimages")
MODEL_PATH = os.path.join(ROOT_DIR, "dataset", "best.pt")
ROI_CONFIG = os.path.join(SCRIPT_DIR, "roi_config.json")
CALIBRATION_CONFIG = os.path.join(SCRIPT_DIR, "calibration_config.json")
BACKEND_URL = "http://localhost:8000"

# ── Lane Configuration ───────────────────────────────────────────
# Maps lane IDs to cloud IDs and video paths. No direction names.
LANES = {
    "001": {"cloud_id": "284501-01", "video": os.path.join(TEST_DIR, "north.mp4")},
    "002": {"cloud_id": "284501-02", "video": os.path.join(TEST_DIR, "south.mp4")},
    "003": {"cloud_id": "284501-03", "video": os.path.join(TEST_DIR, "east.mp4")},
    "004": {"cloud_id": "284501-04", "video": os.path.join(TEST_DIR, "west.mp4")},
}
BOX_IMAGE = os.path.join(TEST_DIR, "empty_intersection.jpg")

# Legacy direction → lane ID mapping (for roi_config.json backward compat)
DIR_TO_LANE = {"North": "001", "South": "002", "East": "003", "West": "004"}

# YOLO class index → Geometry Engine class name
YOLO_CLASS_MAP = {
    0: "Heavy_Motor",
    1: "Light_Motor",
    2: "Organic_Object",
    3: "Three_Wheeler",
    4: "Two_Wheeler",
}

# ── Colors ────────────────────────────────────────────────────────
LANE_COLORS = {
    "001": (0, 200, 255),
    "002": (255, 200, 0),
    "003": (0, 255, 100),
    "004": (255, 100, 200),
}
ZONE_COLORS = {
    "incoming": (0, 255, 0),
    "outgoing": (0, 165, 255),
    "exit":     (0, 0, 255),
}


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def load_model():
    """Load YOLOv11m-seg from best.pt."""
    from ultralytics import YOLO
    print(f"[MODEL] Loading {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)
    print(f"[MODEL] Task: {model.task} | Classes: {list(model.names.values())}")
    return model


def load_rois():
    """Load ROI zone polygons from roi_config.json.
    Translates legacy direction keys (North/South/etc.) to lane IDs (001/002/etc.)."""
    if os.path.exists(ROI_CONFIG):
        with open(ROI_CONFIG, "r") as f:
            raw = json.load(f)
        # Normalize keys: North→001, South→002, etc.
        config = {}
        for k, v in raw.items():
            new_key = DIR_TO_LANE.get(k, k)  # Pass through if already numeric
            config[new_key] = v
        print(f"[ROI] Loaded {len(config)} lane configs (keys: {list(config.keys())})")
        return config
    print("[ROI] No roi_config.json — running without ROI filtering")
    return {}


def create_geometry_engines():
    """
    Create one NorthernBladesGeometryEngine per lane,
    loading piecewise homography from calibration_config.json.
    """
    engines = {}
    calib_path = CALIBRATION_CONFIG if os.path.exists(CALIBRATION_CONFIG) else None

    for lane_name in LANES:
        engine = NorthernBladesGeometryEngine(
            calibration_config_path=calib_path,
        )
        # Fallback: if no real calibration, set identity homography
        if engine._global_H is None and len(engine.zones) == 0:
            engine.set_global_homography(np.eye(3))

        engines[lane_name] = engine

    src = "calibration_config.json" if calib_path else "identity (fallback)"
    print(f"[GEO] {len(engines)} geometry engines initialized | H source: {src}")
    return engines


def point_in_poly(pt, polygon):
    """Test if a 2D point is inside a polygon."""
    poly = np.array(polygon, dtype=np.int32)
    return cv2.pointPolygonTest(poly, (int(pt[0]), int(pt[1])), False) >= 0


def yolo_to_engine_dets(yolo_result, model, roi_zones, midpoint_y=None):
    """
    Convert YOLO detection boxes and masks to the format expected by
    GeometryEngine.process_detections(), splitting into
    incoming/outgoing by ROI zone or midpoint fallback.

    Returns
    -------
    tuple (incoming_dets, outgoing_dets, exit_dets, all_dets_with_zone)
        Each det is {"bbox": [x1,y1,x2,y2], "class_id": str, "polygon": [...]}
    """
    incoming, outgoing, exit_dets = [], [], []
    all_annotated = []  # (det_dict, zone, color) for visualization

    in_zone = roi_zones.get("incoming", [])
    out_zone = roi_zones.get("outgoing", [])
    exit_zone = roi_zones.get("exit", [])

    yolo_boxes = yolo_result.boxes if yolo_result is not None else []
    yolo_masks = yolo_result.masks.xy if (yolo_result is not None and getattr(yolo_result, 'masks', None) is not None) else []

    for i, box in enumerate(yolo_boxes):
        cls_idx = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
        class_name = YOLO_CLASS_MAP.get(cls_idx, "Organic_Object")

        det = {
            "bbox": [float(x1), float(y1), float(x2), float(y2)],
            "class_id": class_name,
        }
        if i < len(yolo_masks) and len(yolo_masks[i]) > 0:
            det["polygon"] = yolo_masks[i]


        # Anchor = bottom-center (tire contact)
        cx, cy = (x1 + x2) / 2, float(y2)

        # Zone classification
        zone, color = "outside", (100, 100, 100)
        if in_zone and point_in_poly((cx, cy), in_zone):
            zone, color = "incoming", (0, 255, 0)
            incoming.append(det)
        elif out_zone and point_in_poly((cx, cy), out_zone):
            zone, color = "outgoing", (0, 165, 255)
            outgoing.append(det)
        elif exit_zone and point_in_poly((cx, cy), exit_zone):
            zone, color = "exit", (0, 0, 255)
            exit_dets.append(det)
        elif midpoint_y is not None:
            # Fallback: use frame midpoint for direction
            if cy > midpoint_y:
                zone, color = "incoming", (0, 255, 0)
                incoming.append(det)
            else:
                zone, color = "outgoing", (0, 165, 255)
                outgoing.append(det)

        all_annotated.append({
            "det": det, "zone": zone, "color": color,
            "conf": conf, "label": class_name,
            "bbox_raw": (int(x1), int(y1), int(x2), int(y2)),
        })

    return incoming, outgoing, exit_dets, all_annotated


# ══════════════════════════════════════════════════════════════════
#  FRAME PROCESSING — uses GeometryEngine.process_detections()
# ══════════════════════════════════════════════════════════════════

def process_lane(model, frame, lane_name, roi_config, geo_engine, yolo_result):
    """
    Process a single lane frame using the FULL geometry engine pipeline:
    YOLO results → zone split → occlusion filter → anchor → undistort
    → BEV warp → footprint injection → fluid mass.

    Parameters
    ----------
    model       : YOLO model (for class name lookup)
    frame       : np.ndarray  BGR frame
    lane_name   : str  "North", "South", etc.
    roi_config  : dict  ROI zones for this lane
    geo_engine  : NorthernBladesGeometryEngine
    yolo_result : YOLO Results object (from batch inference)

    Returns
    -------
    dict with: annotated, density, exit_density, total, incoming,
               outgoing, bev_ms
    """
    h, w = frame.shape[:2]
    zones = roi_config.get(lane_name, {}).get("zones", {})
    detections = yolo_result.boxes if yolo_result is not None else []

    annotated = frame.copy()

    # Draw ROI zone BORDERS only (no fill — avoids the green wash)
    for zname, pts in zones.items():
        if pts:
            c = ZONE_COLORS.get(zname, (128, 128, 128))
            poly = np.array(pts, dtype=np.int32)
            cv2.polylines(annotated, [poly], True, c, 2)

    # ── Convert YOLO detections to engine format + zone split ────
    t_bev_start = time.perf_counter()
    midpoint_y = h // 2

    incoming_dets, outgoing_dets, exit_dets, all_vis = yolo_to_engine_dets(
        yolo_result, model, zones, midpoint_y
    )

    # ── Run Geometry Engine Pipeline ─────────────────────────────
    geo_engine.reset_canvases()
    n_incoming = geo_engine.process_detections(incoming_dets, direction="incoming")
    n_outgoing = geo_engine.process_detections(outgoing_dets, direction="outgoing")
    fluid_mass = geo_engine.process_fluid_mass()

    # Use ROI polygon area as denominator (not canvas area)
    in_zone_pts = zones.get("incoming", [])
    out_zone_pts = zones.get("outgoing", [])

    if in_zone_pts and len(in_zone_pts) >= 3:
        roi_area = cv2.contourArea(np.array(in_zone_pts, dtype=np.int32)) or 1
        incoming_pct = min((fluid_mass["incoming"]["occupied_pixels"] / roi_area) * 100, 100)
    else:
        incoming_pct = fluid_mass["incoming"]["percentage"]

    if out_zone_pts and len(out_zone_pts) >= 3:
        roi_area_out = cv2.contourArea(np.array(out_zone_pts, dtype=np.int32)) or 1
        outgoing_pct = min((fluid_mass["outgoing"]["occupied_pixels"] / roi_area_out) * 100, 100)
    else:
        outgoing_pct = fluid_mass["outgoing"]["percentage"]

    # ── Exit density (bbox fallback — no BEV needed for exit) ────
    exit_density = 0.0
    exit_zone_pts = zones.get("exit", [])
    if exit_zone_pts and len(exit_zone_pts) >= 3:
        exit_poly = np.array(exit_zone_pts, dtype=np.int32)
        ea = cv2.contourArea(exit_poly) or 1
        exit_box_areas = sum(
            int((d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]))
            for d in exit_dets
        )
        exit_density = min((exit_box_areas / ea) * 100, 100)

    bev_ms = (time.perf_counter() - t_bev_start) * 1000

    # ── Annotate detections on frame ─────────────────────────────
    # Batch all polygon fills into ONE overlay to avoid compounding alpha
    overlay = annotated.copy()
    has_polys = False

    for vis in all_vis:
        x1, y1, x2, y2 = vis["bbox_raw"]
        color = vis["color"]
        poly = vis["det"].get("polygon")

        if poly is not None and len(poly) >= 3:
            pts = np.array(poly, np.int32)
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(annotated, [pts], True, color, 2)
            has_polys = True
        else:
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        cv2.putText(annotated, f"{vis['label']} {vis['conf']:.1f}",
                    (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, color, 1)

    # Single blend pass for all polygon fills
    if has_polys:
        cv2.addWeighted(overlay, 0.3, annotated, 0.7, 0, annotated)

    # ── Status header ────────────────────────────────────────────
    total = len(all_vis)
    cv2.rectangle(annotated, (0, 0), (w, 28), (0, 0, 0), -1)
    cv2.putText(annotated,
                f"{lane_name} | {total}v | N={incoming_pct:.0f}% | Geo:{n_incoming}proj",
                (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                LANE_COLORS.get(lane_name, (255, 255, 255)), 1)

    return {
        "annotated": annotated,
        "density": incoming_pct,
        "exit_density": exit_density,
        "total": total,
        "incoming": n_incoming,
        "outgoing": n_outgoing,
        "bev_ms": bev_ms,
    }


def process_box(model, image_path, roi_config):
    """
    Process the 5th camera (God's Eye) intersection image using
    segmentation masks and the Box ROI — same pipeline as lane cameras.
    """
    img = cv2.imread(image_path)
    if img is None:
        return {"box_density": 0, "count": 0}

    results = model(img, verbose=False, conf=0.35)
    result = results[0] if results else None
    boxes = result.boxes if result is not None else []
    masks = result.masks.xy if (result is not None and getattr(result, 'masks', None) is not None) else []
    count = len(boxes)

    # Get Box ROI polygon from config
    box_roi_pts = None
    box_cfg = roi_config.get("Box", {})
    zones = box_cfg.get("zones", {})
    if "incoming" in zones and len(zones["incoming"]) >= 3:
        box_roi_pts = np.array(zones["incoming"], dtype=np.int32)

    if box_roi_pts is not None:
        roi_area = cv2.contourArea(box_roi_pts) or 1

        # Sum seg mask areas that fall inside the ROI
        total_mask_area = 0
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cx, cy = (x1 + x2) / 2, float(y2)

            # Only count vehicles whose anchor is inside the ROI
            if cv2.pointPolygonTest(box_roi_pts, (int(cx), int(cy)), False) >= 0:
                if i < len(masks) and len(masks[i]) >= 3:
                    # Use true seg mask area
                    mask_poly = np.array(masks[i], dtype=np.int32)
                    total_mask_area += cv2.contourArea(mask_poly)
                else:
                    # Fallback: use bbox area
                    total_mask_area += int((x2 - x1) * (y2 - y1))

        density = min((total_mask_area / roi_area) * 100, 100)
    else:
        # No ROI defined: use seg mask area / frame area
        h, w = img.shape[:2]
        total_mask_area = 0
        for i in range(len(boxes)):
            if i < len(masks) and len(masks[i]) >= 3:
                mask_poly = np.array(masks[i], dtype=np.int32)
                total_mask_area += cv2.contourArea(mask_poly)
            else:
                x1, y1, x2, y2 = boxes[i].xyxy[0].cpu().numpy()
                total_mask_area += int((x2 - x1) * (y2 - y1))
        density = min((total_mask_area / (h * w)) * 100, 100)

    return {"box_density": round(density, 1), "count": count}


# ══════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Northern Blades — Production Edge Node"
    )
    parser.add_argument("--fps", type=int, default=1,
                        help="Target processing rate per lane (default: 1)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save dashboard video to path")
    parser.add_argument("--no-display", action="store_true",
                        help="Run headless (no OpenCV windows)")
    parser.add_argument("--backend", type=str, default=BACKEND_URL,
                        help=f"Backend URL (default: {BACKEND_URL})")
    args = parser.parse_args()

    backend_url = args.backend

    # ── Load model ────────────────────────────────────────────────
    model = load_model()
    roi_config = load_rois()

    # ── Create geometry engines (one per lane, with calibration) ──
    geo_engines = create_geometry_engines()

    # ── Open video feeds ──────────────────────────────────────────
    caps = {}
    fps_map = {}
    for lane_name, cfg in LANES.items():
        path = cfg["video"]
        if os.path.exists(path):
            cap = cv2.VideoCapture(path)
            if cap.isOpened():
                n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS) or 30
                print(f"[VIDEO] {lane_name}: {n} frames @ {fps:.0f}fps")
                caps[lane_name] = cap
                fps_map[lane_name] = fps
            else:
                print(f"[WARN] Cannot open {path}")
        else:
            print(f"[WARN] Video not found: {path}")

    if not caps:
        print("[ERROR] No video sources available!")
        sys.exit(1)

    # ── Process box (5th camera) once ─────────────────────────────
    if os.path.exists(BOX_IMAGE):
        br = process_box(model, BOX_IMAGE, roi_config)
        print(f"[BOX] {br['count']} vehicles, density={br['box_density']:.1f}%")
        try:
            requests.post(f"{backend_url}/api/box",
                          json={"box_density": br["box_density"],
                                "confidence": 0.95}, timeout=3)
        except Exception as e:
            print(f"[WARN] Cannot reach backend: {e}")

    # ── Main loop config ──────────────────────────────────────────
    interval = 1.0 / args.fps
    frame_num = 0
    lane_stats = {}
    last_inference_time = {}
    engine_state = {"state": "IDLE", "active_green": None}
    lane_order = list(caps.keys())

    print(f"\n{'='*60}")
    print(f"  NORTHERN BLADES EDGE NODE — {len(caps)} lanes | Press 'q' to quit")
    print(f"  Geometry Engine: {'CALIBRATED' if os.path.exists(CALIBRATION_CONFIG) else 'IDENTITY (uncalibrated)'}")
    print(f"  Backend: {backend_url}")
    print(f"{'='*60}\n")

    try:
        while True:
            t0 = time.time()
            frame_num += 1
            tick_yolo_ms, tick_bev_ms = 0.0, 0.0

            # ── Step 1: Fetch engine state from backend ───────────
            t_eng_start = time.perf_counter()
            try:
                r = requests.get(f"{backend_url}/api/state", timeout=0.2)
                engine_state = r.json()
            except Exception:
                engine_state["state"] = "OFFLINE"
            engine_ms = (time.perf_counter() - t_eng_start) * 1000

            # ── Step 2: Grab frames (skip to match FPS) ───────────
            raw_frames = {}
            for lane, cap in caps.items():
                video_fps = fps_map.get(lane, 30.0)
                frames_to_skip = max(1, int(video_fps / args.fps))
                for _ in range(frames_to_skip - 1):
                    ret = cap.grab()
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        break

                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                if ret:
                    raw_frames[lane] = frame

            # ── Step 3: Sentry Mode — decide which lanes need YOLO ─
            active_lanes = []
            batch_frames = []

            for lane in lane_order:
                if lane not in raw_frames:
                    continue
                is_green = (lane == engine_state.get("active_green"))
                is_yellow = (engine_state.get("state") == "YELLOW")
                # Green/Yellow lanes: 1 FPS | Red lanes: 0.2 FPS (5s)
                target_interval = 1.0 if (is_green or is_yellow) else 5.0

                if t0 - last_inference_time.get(lane, 0) >= target_interval:
                    active_lanes.append(lane)
                    batch_frames.append(raw_frames[lane])
                    last_inference_time[lane] = t0

            # ── Step 4: YOLO batch inference ──────────────────────
            t_yolo_start = time.perf_counter()
            batch_results = model(
                batch_frames, verbose=False, conf=0.35
            ) if batch_frames else []
            tick_yolo_ms = (time.perf_counter() - t_yolo_start) * 1000

            # ── Step 5: Per-lane geometry engine processing ───────
            for i, lane in enumerate(active_lanes):
                result = batch_results[i] if i < len(batch_results) else None

                stats = process_lane(
                    model=model,
                    frame=raw_frames[lane],
                    lane_name=lane,
                    roi_config=roi_config,
                    geo_engine=geo_engines[lane],
                    yolo_result=result,
                )
                lane_stats[lane] = stats
                tick_bev_ms += stats.get("bev_ms", 0)

                # ── Step 6: Send telemetry to backend ─────────────
                try:
                    _, buffer = cv2.imencode(
                        '.jpg', stats["annotated"],
                        [cv2.IMWRITE_JPEG_QUALITY, 50]
                    )
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')
                    cloud_id = LANES[lane]["cloud_id"]

                    requests.post(f"{backend_url}/api/telemetry", json={
                        "lane": cloud_id,
                        "primary": stats["density"],
                        "spill": 0,
                        "exit": stats["exit_density"],
                        "velocity": 30,
                        "frame_b64": frame_b64,
                    }, timeout=2)
                except Exception:
                    pass

            # ── Step 7: Push latency telemetry ────────────────────
            try:
                requests.post(f"{backend_url}/api/latency", json={
                    "yolo_ms":   round(tick_yolo_ms, 1),
                    "bev_ms":    round(tick_bev_ms, 1),
                    "engine_ms": round(engine_ms, 1),
                }, timeout=1)
            except Exception:
                pass

            # ── Step 8: Display (if not headless) ─────────────────
            if not args.no_display and lane_stats:
                cell_w, cell_h = 480, 270
                dash = np.zeros((cell_h * 2, cell_w * 2, 3), dtype=np.uint8)
                positions = {
                    "001": (0, 0), "002": (cell_w, 0),
                    "003": (0, cell_h), "004": (cell_w, cell_h),
                }
                for lane, (x, y) in positions.items():
                    if lane in lane_stats:
                        resized = cv2.resize(
                            lane_stats[lane]["annotated"], (cell_w, cell_h)
                        )
                        dash[y:y+cell_h, x:x+cell_w] = resized

                cv2.imshow("Northern Blades Edge Node", dash)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # ── Console output (every 3 frames) ──────────────────
            if frame_num % 3 == 0:
                act = engine_state.get("active_green", "None")
                st = engine_state.get("state", "?")
                tm = engine_state.get("green_timer", 0)
                stats_str = " | ".join(
                    f"{l}:{s['density']:.0f}%"
                    for l, s in lane_stats.items()
                )
                print(
                    f"[F{frame_num:3d}] {st:12s} "
                    f"Green={act or 'RED':12s} T={tm:3d}s | "
                    f"{stats_str} | "
                    f"YOLO:{tick_yolo_ms:.0f}ms "
                    f"BEV:{tick_bev_ms:.0f}ms "
                    f"Eng:{engine_ms:.0f}ms"
                )

            # ── Frame pacing ─────────────────────────────────────
            elapsed = time.time() - t0
            if elapsed < interval:
                time.sleep(interval - elapsed)

    except KeyboardInterrupt:
        print("\n[EDGE] Stopped")
    finally:
        for c in caps.values():
            c.release()
        cv2.destroyAllWindows()

    print("[EDGE] Done!")


if __name__ == "__main__":
    main()
