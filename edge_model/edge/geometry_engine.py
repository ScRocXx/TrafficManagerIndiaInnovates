import numpy as np
import cv2
import json
import os

# ──────────────────────────────────────────────────────────────────
# Northern Blades V5.5 — Geometry Engine
# Converts YOLOv11m-seg outputs into Bird's-Eye View Fluid Mass
# using the Single-Point Anchor architecture.
# ──────────────────────────────────────────────────────────────────


class NorthernBladesGeometryEngine:
    """
    V5.5 Geometry Engine.

    Pipeline per vehicle:
        1. extract_anchor(bbox)          → (cx, ymax) tire-contact point
        2. undistort_point(anchor, K, D) → lens-corrected anchor
        3. apply_bev_warp(anchor, zone)  → 2D BEV coordinate
        4. inject_footprint(bev_pt, cls) → rigid rectangle on canvas
        5. process_fluid_mass()          → N% for each direction
    """

    # Default BEV canvas dimensions (pixels). A 1024×1024 map gives
    # 1 048 576 addressable "road cells" — plenty of resolution.
    DEFAULT_CANVAS = (1024, 1024)

    # Synthetic footprint dimensions (BEV-scaled pixel units).
    # These are rigid rectangles injected at the anchor point so that
    # the density calculation is immune to mask jitter.
    FOOTPRINTS = {
        "Heavy_Motor":    {"length": 120, "width": 30},
        "Light_Motor":    {"length": 45,  "width": 20},
        "Three_Wheeler":  {"length": 25,  "width": 15},
        "Two_Wheeler":    {"length": 20,  "width": 8},
        "Organic_Object": {"length": 10,  "width": 10},
    }

    # IOU threshold for the occlusion filter.  If a smaller vehicle's
    # bbox is ≥ this fraction *inside* a larger vehicle's bbox AND its
    # bottom-Y is higher (farther from camera), it is "depth-occluded".
    OCCLUSION_IOU_THRESH = 0.60

    def __init__(
        self,
        canvas_size=None,
        calibration_config_path=None,
        camera_matrix=None,
        dist_coeffs=None,
    ):
        """
        Parameters
        ----------
        canvas_size : tuple[int, int]
            (height, width) of the BEV bitwise canvas.
        calibration_config_path : str | None
            Path to ``calibration_config.json`` containing piecewise
            homography zones.  If *None* the engine falls back to a
            single global H matrix supplied at warp-time.
        camera_matrix : np.ndarray | None
            3×3 intrinsic camera matrix K (from checkerboard calibration).
        dist_coeffs : np.ndarray | None
            Distortion coefficients D (from checkerboard calibration).
        """
        self.canvas_size = canvas_size or self.DEFAULT_CANVAS

        # ── Bitwise Anti-Ghost Canvases (one per direction) ──────
        self.canvas_incoming = np.zeros(self.canvas_size, dtype=np.uint8)
        self.canvas_outgoing = np.zeros(self.canvas_size, dtype=np.uint8)

        # ── Lens Distortion Correction ───────────────────────────
        self.camera_matrix = camera_matrix  # K
        self.dist_coeffs = dist_coeffs      # D

        # ── Piecewise Homography Zones ───────────────────────────
        # Each zone is: { "name": str, "bbox": [x1,y1,x2,y2],
        #                  "H": [[3×3 floats]] }
        self.zones = []
        self._global_H = None  # fallback single matrix
        if calibration_config_path and os.path.exists(calibration_config_path):
            self._load_calibration(calibration_config_path)

    # ================================================================
    #  CONFIGURATION
    # ================================================================

    def _load_calibration(self, path):
        """Load piecewise homography zones from a JSON config file."""
        with open(path, "r") as f:
            config = json.load(f)

        self._global_H = None
        self.zones = []

        if "global_H" in config:
            self._global_H = np.array(config["global_H"], dtype=np.float64)

        for zone in config.get("zones", []):
            self.zones.append({
                "name": zone["name"],
                "bbox": zone["bbox"],          # [x1, y1, x2, y2] in image-pixel space
                "H": np.array(zone["H"], dtype=np.float64),
            })

    def set_global_homography(self, H):
        """Set a single global homography matrix (fallback when no zones)."""
        self._global_H = np.array(H, dtype=np.float64)

    def set_camera_intrinsics(self, K, D):
        """Set the camera intrinsic matrix and distortion coefficients."""
        self.camera_matrix = np.array(K, dtype=np.float64)
        self.dist_coeffs = np.array(D, dtype=np.float64)

    # ================================================================
    #  STEP 0 — CANVAS MANAGEMENT
    # ================================================================

    def reset_canvases(self):
        """Clear both canvases for the next frame."""
        self.canvas_incoming.fill(0)
        self.canvas_outgoing.fill(0)

    # ================================================================
    #  STEP 1 — SINGLE-POINT ANCHOR EXTRACTION
    # ================================================================

    @staticmethod
    def extract_anchor(bbox):
        """
        Return the ground-contact anchor point from a YOLO bounding box.

        Parameters
        ----------
        bbox : tuple/list  (x1, y1, x2, y2)

        Returns
        -------
        np.ndarray  shape (2,) → (cx, ymax)
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        ymax = float(y2)          # bottom edge = tire contact
        return np.array([cx, ymax], dtype=np.float32)

    # ================================================================
    #  STEP 2 — LENS UNDISTORTION
    # ================================================================

    def undistort_point(self, point):
        """
        Remove barrel / pincushion distortion from a single 2D point
        using the pre-calibrated camera intrinsics (K, D).

        If K or D is not set the point is returned unchanged.

        Parameters
        ----------
        point : np.ndarray  shape (2,)

        Returns
        -------
        np.ndarray  shape (2,)
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            return point

        pts = point.reshape(1, 1, 2).astype(np.float64)
        undistorted = cv2.undistortPoints(
            pts,
            self.camera_matrix,
            self.dist_coeffs,
            P=self.camera_matrix,  # re-project back to pixel space
        )
        return undistorted.reshape(2).astype(np.float32)

    def undistort_frame(self, frame):
        """
        Undistort an entire frame (useful for visualization / debug).
        Falls back to returning the original frame if K/D are not set.
        """
        if self.camera_matrix is None or self.dist_coeffs is None:
            return frame
        return cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)

    # ================================================================
    #  STEP 3 — PIECEWISE HOMOGRAPHY WARP
    # ================================================================

    def _find_zone(self, anchor):
        """Return the H matrix for the zone containing *anchor*, or the
        global fallback matrix."""
        ax, ay = anchor
        for zone in self.zones:
            x1, y1, x2, y2 = zone["bbox"]
            if x1 <= ax <= x2 and y1 <= ay <= y2:
                return zone["H"]
        # Fallback to global H
        return self._global_H

    def apply_bev_warp(self, anchor, homography_matrix=None):
        """
        Warp a single anchor point onto the BEV map.

        Parameters
        ----------
        anchor : np.ndarray  shape (2,)
        homography_matrix : np.ndarray | None
            If supplied, this overrides the zone / global lookup.

        Returns
        -------
        np.ndarray  shape (2,) — BEV (x, y) coordinate,  or *None*
            if no H matrix is available.
        """
        H = homography_matrix if homography_matrix is not None else self._find_zone(anchor)
        if H is None:
            return None

        pt = anchor.reshape(1, 1, 2).astype(np.float64)
        warped = cv2.perspectiveTransform(pt, H)
        return warped.reshape(2).astype(np.float32)

    # ================================================================
    #  STEP 4 — SYNTHETIC FOOTPRINT INJECTION
    # ================================================================

    def inject_footprint(self, bev_point, class_id, canvas="incoming"):
        """
        Draw a rigid, class-sized rectangle centred on *bev_point*
        onto the specified bitwise canvas.

        Parameters
        ----------
        bev_point : np.ndarray  shape (2,)
        class_id  : str   one of the keys in FOOTPRINTS
        canvas    : str   "incoming" | "outgoing"
        """
        fp = self.FOOTPRINTS.get(class_id)
        if fp is None or bev_point is None:
            return

        cx, cy = int(bev_point[0]), int(bev_point[1])
        half_w = fp["width"] // 2
        half_l = fp["length"] // 2

        # Define the four corners of the rigid rectangle
        pts = np.array([
            [cx - half_w, cy - half_l],
            [cx + half_w, cy - half_l],
            [cx + half_w, cy + half_l],
            [cx - half_w, cy + half_l],
        ], dtype=np.int32)

        target = self.canvas_incoming if canvas == "incoming" else self.canvas_outgoing
        cv2.fillPoly(target, [pts], color=255)

    # ================================================================
    #  STEP 5 — OCCLUSION FILTER (IOU Depth-Check)
    # ================================================================

    @staticmethod
    def _bbox_area(box):
        return max(0, box[2] - box[0]) * max(0, box[3] - box[1])

    @staticmethod
    def _intersection_area(a, b):
        ix1 = max(a[0], b[0])
        iy1 = max(a[1], b[1])
        ix2 = min(a[2], b[2])
        iy2 = min(a[3], b[3])
        return max(0, ix2 - ix1) * max(0, iy2 - iy1)

    def filter_occlusions(self, detections):
        """
        Remove depth-occluded small vehicles hidden behind large ones.

        A detection is dropped if:
          - Its bbox area is significantly inside a larger bbox
            (intersection / small_area ≥ threshold)
          - Its bottom-Y is *higher* (i.e., further from camera)
            than the larger vehicle's bottom-Y.

        Parameters
        ----------
        detections : list[dict]
            Each dict must have ``"bbox": [x1,y1,x2,y2]`` and
            ``"class_id": str``.

        Returns
        -------
        list[dict]  filtered detections (without occluded ghosts).
        """
        # Sort largest-area first so we compare small vs. large
        dets = sorted(detections, key=lambda d: self._bbox_area(d["bbox"]), reverse=True)
        keep = []

        for i, det in enumerate(dets):
            occluded = False
            box_i = det["bbox"]
            area_i = self._bbox_area(box_i)

            for j in range(i):
                box_j = dets[j]["bbox"]
                area_j = self._bbox_area(box_j)
                if area_j <= area_i:
                    continue  # only compare against strictly larger boxes

                inter = self._intersection_area(box_i, box_j)
                if area_i > 0 and (inter / area_i) >= self.OCCLUSION_IOU_THRESH:
                    # Small box is mostly inside the large box.
                    # Check depth: higher bottom-Y = closer to camera.
                    if box_i[3] < box_j[3]:
                        # small vehicle's bottom is higher → it's behind
                        occluded = True
                        break

            if not occluded:
                keep.append(det)

        return keep

    # ================================================================
    #  STEP 6 — FLUID MASS CALCULATION
    # ================================================================

    def process_fluid_mass(self):
        """
        Calculate the exact physical road occupancy percentage by
        counting non-zero pixels on the bitwise canvases.

        Returns
        -------
        dict  with "incoming" and "outgoing" sub-dicts containing
              "occupied_pixels" and "percentage".
        """
        incoming_mass = int(cv2.countNonZero(self.canvas_incoming))
        outgoing_mass = int(cv2.countNonZero(self.canvas_outgoing))
        total_area = self.canvas_size[0] * self.canvas_size[1]

        return {
            "incoming": {
                "occupied_pixels": incoming_mass,
                "percentage": round((incoming_mass / total_area) * 100, 2),
            },
            "outgoing": {
                "occupied_pixels": outgoing_mass,
                "percentage": round((outgoing_mass / total_area) * 100, 2),
            },
        }

    # ================================================================
    #  CONVENIENCE — FULL FRAME PIPELINE
    # ================================================================

    def process_detections(self, detections, direction="incoming"):
        """
        Run the full pipeline for a list of YOLO detections on a
        single frame and single direction.

        Parameters
        ----------
        detections : list[dict]
            Each dict: {"bbox": [x1,y1,x2,y2], "class_id": str}
        direction  : str  "incoming" | "outgoing"

        Returns
        -------
        int  number of vehicles successfully projected.
        """
        # Step 5 — remove ghosts
        clean = self.filter_occlusions(detections)
        projected = 0

        for det in clean:
            bbox = det["bbox"]
            cls = det["class_id"]
            polygon = det.get("polygon")

            # Step 1 — anchor (used to determine which homography zone to apply)
            anchor = self.extract_anchor(bbox)

            if polygon is not None and len(polygon) >= 3:
                # Use true segmentation mask polygon
                H = self._find_zone(anchor)
                if H is not None:
                    pts = np.array(polygon, dtype=np.float32)
                    
                    # Undistort all polygon points
                    if self.camera_matrix is not None and self.dist_coeffs is not None:
                        pts_reshaped = pts.reshape(-1, 1, 2).astype(np.float64)
                        pts_undist = cv2.undistortPoints(
                            pts_reshaped, self.camera_matrix, self.dist_coeffs, P=self.camera_matrix
                        )
                        pts = pts_undist.reshape(-1, 2).astype(np.float32)
                        
                    # BEV Warp all polygon points
                    pts_reshaped = pts.reshape(-1, 1, 2).astype(np.float64)
                    warped = cv2.perspectiveTransform(pts_reshaped, H)
                    warped_poly = warped.reshape(-1, 2).astype(np.int32)
                    
                    # Inject true shape
                    target = self.canvas_incoming if direction == "incoming" else self.canvas_outgoing
                    cv2.fillPoly(target, [warped_poly], color=255)
                    projected += 1
            else:
                # Fallback to fixed footprint
                anchor = self.undistort_point(anchor)
                bev_pt = self.apply_bev_warp(anchor)
                if bev_pt is not None:
                    self.inject_footprint(bev_pt, cls, canvas=direction)
                    projected += 1

        return projected
