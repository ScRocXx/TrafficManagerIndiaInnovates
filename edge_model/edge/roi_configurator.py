"""
Northern Blades V5.5 — Manual ROI Configurator
================================================
Interactive tool to define 3 ROI zones per camera image:
  1. INCOMING zone — where vehicles approach the intersection
  2. OUTGOING zone — where vehicles leave the intersection
  3. EXIT zone    — the exit box (jam detection for Rank 0 Veto)

Usage:
    python edge/roi_configurator.py --image "testimages/t1.jpg" --lane North
    python edge/roi_configurator.py --image "testimages/t2.webp" --lane South

Instructions:
    1. A window opens showing your camera image.
    2. Click points to draw each ROI polygon.
    3. Press 'n' to finish the current zone and move to the next.
    4. Press 'u' to undo the last point.
    5. Press 'r' to reset the current zone.
    6. Press 's' to save all zones and exit.
    7. Press 'q' to quit without saving.

Output:
    Saves to edge/roi_config.json with polygons per lane.
"""

import argparse
import json
import os
import sys
import cv2
import numpy as np
import copy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "roi_config.json")

ZONE_NAMES = ["incoming", "outgoing", "exit"]
ZONE_COLORS = {
    "incoming": (0, 255, 0),    # Green
    "outgoing": (0, 165, 255),  # Orange
    "exit":     (0, 0, 255),    # Red
}
ZONE_LABELS = {
    "incoming": "INCOMING ZONE (vehicles approaching intersection)",
    "outgoing": "OUTGOING ZONE (vehicles leaving intersection)",
    "exit":     "EXIT ZONE (jam detection — Rank 0 Gridlock Veto)",
}


class ROIConfigurator:
    def __init__(self, image_path, lane_name):
        self.image_path = image_path
        self.lane_name = lane_name
        self.original = cv2.imread(image_path)
        if self.original is None:
            print(f"[ERROR] Cannot read image: {image_path}")
            sys.exit(1)

        self.h, self.w = self.original.shape[:2]
        # Scale down for display if image is too large
        self.scale = 1.0
        max_display = 1200
        if self.w > max_display or self.h > max_display:
            self.scale = max_display / max(self.w, self.h)

        self.display_w = int(self.w * self.scale)
        self.display_h = int(self.h * self.scale)
        self.display_img = cv2.resize(self.original, (self.display_w, self.display_h))

        self.current_zone_idx = 0
        self.zones = {name: [] for name in ZONE_NAMES}  # Points in ORIGINAL coords
        self.current_points = []  # Points in DISPLAY coords (for the zone being drawn)

        self.window_name = f"ROI Configurator — {lane_name} Lane"

    def _display_to_original(self, pt):
        """Convert display coordinates to original image coordinates."""
        return (int(pt[0] / self.scale), int(pt[1] / self.scale))

    def _original_to_display(self, pt):
        """Convert original image coordinates to display coordinates."""
        return (int(pt[0] * self.scale), int(pt[1] * self.scale))

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append((x, y))
            self.redraw()

    def redraw(self):
        canvas = self.display_img.copy()

        # Draw already-completed zones
        for zone_name, pts_orig in self.zones.items():
            if pts_orig:
                pts_disp = [self._original_to_display(p) for p in pts_orig]
                color = ZONE_COLORS[zone_name]
                overlay = canvas.copy()
                cv2.fillPoly(overlay, [np.array(pts_disp, dtype=np.int32)], color)
                cv2.addWeighted(overlay, 0.25, canvas, 0.75, 0, canvas)
                cv2.polylines(canvas, [np.array(pts_disp, dtype=np.int32)], True, color, 2)
                # Label
                cx = int(np.mean([p[0] for p in pts_disp]))
                cy = int(np.mean([p[1] for p in pts_disp]))
                cv2.putText(canvas, zone_name.upper(), (cx - 40, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Draw current zone being drawn
        if self.current_zone_idx < len(ZONE_NAMES):
            zone_name = ZONE_NAMES[self.current_zone_idx]
            color = ZONE_COLORS[zone_name]

            if len(self.current_points) > 0:
                for pt in self.current_points:
                    cv2.circle(canvas, pt, 5, color, -1)
                if len(self.current_points) > 1:
                    cv2.polylines(canvas, [np.array(self.current_points, dtype=np.int32)],
                                  False, color, 2)

        # Instructions bar at top
        bar_h = 55
        cv2.rectangle(canvas, (0, 0), (self.display_w, bar_h), (0, 0, 0), -1)

        if self.current_zone_idx < len(ZONE_NAMES):
            zone_name = ZONE_NAMES[self.current_zone_idx]
            color = ZONE_COLORS[zone_name]
            label = ZONE_LABELS[zone_name]
            cv2.putText(canvas, f"Draw: {label}", (10, 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            cv2.putText(canvas, "Click=add point | N=next zone | U=undo | R=reset | S=save | Q=quit",
                        (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
        else:
            cv2.putText(canvas, "All zones drawn! Press S to save, Q to quit.",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Lane info bar at bottom
        cv2.rectangle(canvas, (0, self.display_h - 25), (self.display_w, self.display_h), (0, 0, 0), -1)
        cv2.putText(canvas, f"Lane: {self.lane_name} | Zone {self.current_zone_idx + 1}/3 | "
                    f"Points: {len(self.current_points)}",
                    (10, self.display_h - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        cv2.imshow(self.window_name, canvas)

    def finalize_current_zone(self):
        """Save current points to the zone and move to the next."""
        if self.current_zone_idx >= len(ZONE_NAMES):
            return

        zone_name = ZONE_NAMES[self.current_zone_idx]

        if len(self.current_points) < 3:
            print(f"[WARN] Need at least 3 points for {zone_name} zone. Currently {len(self.current_points)}.")
            return

        # Convert display coords to original image coords
        orig_pts = [self._display_to_original(p) for p in self.current_points]
        self.zones[zone_name] = orig_pts
        print(f"[OK] {zone_name.upper()} zone saved: {len(orig_pts)} points")

        self.current_points = []
        self.current_zone_idx += 1
        self.redraw()

    def save_config(self):
        """Save all zones to roi_config.json."""
        # Load existing config or create new
        config = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)

        config[self.lane_name] = {
            "image": os.path.abspath(self.image_path),
            "image_size": [self.w, self.h],
            "zones": {}
        }

        for zone_name, pts in self.zones.items():
            if pts:
                config[self.lane_name]["zones"][zone_name] = pts

        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

        print(f"\n[SAVED] ROI config → {CONFIG_PATH}")
        print(f"  Lane: {self.lane_name}")
        for zone_name, pts in self.zones.items():
            status = f"{len(pts)} points" if pts else "NOT SET"
            print(f"  {zone_name}: {status}")

    def run(self):
        """Main interactive loop."""
        print(f"\n{'='*60}")
        print(f"  ROI CONFIGURATOR — {self.lane_name} Lane")
        print(f"  Image: {self.image_path} ({self.w}×{self.h})")
        print(f"{'='*60}")
        print(f"\nDraw 3 zones in order:")
        for i, name in enumerate(ZONE_NAMES):
            print(f"  {i+1}. {ZONE_LABELS[name]}")
        print(f"\nControls:")
        print(f"  Click  = Add a point")
        print(f"  N      = Finish this zone, move to next")
        print(f"  U      = Undo last point")
        print(f"  R      = Reset current zone")
        print(f"  S      = Save all zones and exit")
        print(f"  Q      = Quit without saving\n")

        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        self.redraw()

        while True:
            key = cv2.waitKey(30) & 0xFF

            if key == ord('q'):
                print("[QUIT] Exiting without saving.")
                break

            elif key == ord('n'):
                self.finalize_current_zone()

            elif key == ord('u'):
                if self.current_points:
                    self.current_points.pop()
                    self.redraw()
                    print("[UNDO] Removed last point.")

            elif key == ord('r'):
                self.current_points = []
                self.redraw()
                print("[RESET] Current zone cleared.")

            elif key == ord('s'):
                # Finalize current zone if it has enough points
                if len(self.current_points) >= 3:
                    self.finalize_current_zone()
                self.save_config()
                break

        cv2.destroyAllWindows()


# ──────────────────────────────────────────────────────────────────
#  NON-INTERACTIVE MODE (for headless/automated use)
# ──────────────────────────────────────────────────────────────────

def auto_roi_from_image(image_path, lane_name):
    img = cv2.imread(image_path)
    if img is None:
        print(f"[ERROR] Cannot read {image_path}")
        return None

    h, w = img.shape[:2]
    margin_x = int(w * 0.05)  # 5% margin on sides

    zones = {
        "incoming": [
            [margin_x, int(h * 0.60)],
            [w - margin_x, int(h * 0.60)],
            [w - margin_x, int(h * 0.95)],
            [margin_x, int(h * 0.95)],
        ],
        "outgoing": [
            [margin_x, int(h * 0.05)],
            [w - margin_x, int(h * 0.05)],
            [w - margin_x, int(h * 0.40)],
            [margin_x, int(h * 0.40)],
        ],
        "exit": [
            [margin_x, int(h * 0.40)],
            [w - margin_x, int(h * 0.40)],
            [w - margin_x, int(h * 0.60)],
            [margin_x, int(h * 0.60)],
        ],
    }

    config = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

    config[lane_name] = {
        "image": os.path.abspath(image_path),
        "image_size": [w, h],
        "zones": zones,
    }

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    print(f"[AUTO-ROI] {lane_name}: incoming={h*0.60:.0f}-{h*0.95:.0f}px, "
          f"exit={h*0.40:.0f}-{h*0.60:.0f}px, outgoing={h*0.05:.0f}-{h*0.40:.0f}px")

    return config[lane_name]


# ──────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def run_all_lanes():
    """
    Auto-discover test images and run the ROI configurator
    for all 4 lanes sequentially. Works without any arguments.
    """
    ROOT = os.path.dirname(SCRIPT_DIR)
    test_dir = os.path.join(ROOT, "testimages")

    # Lane ID → expected frame image mapping
    lane_images = {
        "001": os.path.join(test_dir, "north_frame1.jpg"),
        "002": os.path.join(test_dir, "south_frame1.jpg"),
        "003": os.path.join(test_dir, "east_frame1.jpg"),
        "004": os.path.join(test_dir, "west_frame1.jpg"),
    }

    print(f"\n{'='*60}")
    print(f"  NORTHERN BLADES — ROI CONFIGURATOR")
    print(f"{'='*60}")
    print(f"\n  Lane to image mapping:")
    for lane, img in lane_images.items():
        status = os.path.basename(img) if os.path.exists(img) else "NOT FOUND"
        print(f"    {lane}: {status}")

    print(f"\n  You will draw 3 zones per lane:")
    print(f"    1. INCOMING (Green)  — vehicles approaching")
    print(f"    2. OUTGOING (Orange) — vehicles leaving")
    print(f"    3. EXIT (Red)        — jam detection zone")
    print(f"\n  Controls: Click=point | N=next zone | U=undo | R=reset | S=save | Q=skip\n")

    for lane, img_path in lane_images.items():
        if os.path.exists(img_path):
            print(f"\n{'─'*60}")
            print(f"  Starting Lane {lane} ({os.path.basename(img_path)})...")
            print(f"{'─'*60}")
            configurator = ROIConfigurator(img_path, lane)
            configurator.run()
        else:
            print(f"\n[SKIP] {lane} — image not found: {img_path}")

    print(f"\n{'='*60}")
    print(f"  ROI CONFIG COMPLETE")
    print(f"  Saved to: {CONFIG_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Northern Blades — ROI Configurator",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--image", default=None,
                        help="Camera image to draw ROIs on (optional)")
    parser.add_argument("--lane", default=None,
                        help="Lane name: North/South/East/West (optional)")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-generate ROIs without interactive drawing")
    args = parser.parse_args()

    if args.image and args.lane:
        # Single-lane mode
        if args.auto:
            auto_roi_from_image(args.image, args.lane)
        else:
            configurator = ROIConfigurator(args.image, args.lane)
            configurator.run()
    else:
        # No arguments — run all 4 lanes from testimages/
        run_all_lanes()
