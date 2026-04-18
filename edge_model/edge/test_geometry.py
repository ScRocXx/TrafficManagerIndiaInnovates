"""
Northern Blades V5.5 — Geometry Engine Unit Tests
===================================================
Run with:  pytest edge/test_geometry.py -v
"""

import numpy as np
import cv2
import sys
import os

# Allow imports from the edge directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from geometry_engine import NorthernBladesGeometryEngine


# ──────────────────────────────────────────────────────────────────
#  1. SINGLE-POINT ANCHOR EXTRACTION
# ──────────────────────────────────────────────────────────────────

class TestAnchorExtraction:
    def test_anchor_returns_bottom_center(self):
        """Anchor must be (center_x, ymax) of the bounding box."""
        bbox = [100, 50, 200, 300]
        anchor = NorthernBladesGeometryEngine.extract_anchor(bbox)
        assert anchor[0] == 150.0, f"cx should be 150, got {anchor[0]}"
        assert anchor[1] == 300.0, f"ymax should be 300, got {anchor[1]}"

    def test_anchor_with_float_bbox(self):
        bbox = [10.5, 20.3, 50.7, 80.9]
        anchor = NorthernBladesGeometryEngine.extract_anchor(bbox)
        assert abs(anchor[0] - 30.6) < 0.1
        assert abs(anchor[1] - 80.9) < 0.1

    def test_anchor_with_zero_width_box(self):
        bbox = [100, 50, 100, 300]
        anchor = NorthernBladesGeometryEngine.extract_anchor(bbox)
        assert anchor[0] == 100.0
        assert anchor[1] == 300.0


# ──────────────────────────────────────────────────────────────────
#  2. BEV WARP (IDENTITY MATRIX = NO CHANGE)
# ──────────────────────────────────────────────────────────────────

class TestBEVWarp:
    def test_identity_warp_returns_same_point(self):
        engine = NorthernBladesGeometryEngine()
        H_identity = np.eye(3, dtype=np.float64)
        engine.set_global_homography(H_identity)

        anchor = np.array([500.0, 400.0], dtype=np.float32)
        bev_pt = engine.apply_bev_warp(anchor)

        assert bev_pt is not None
        assert abs(bev_pt[0] - 500.0) < 0.1
        assert abs(bev_pt[1] - 400.0) < 0.1

    def test_warp_without_matrix_returns_none(self):
        engine = NorthernBladesGeometryEngine()
        anchor = np.array([500.0, 400.0], dtype=np.float32)
        bev_pt = engine.apply_bev_warp(anchor)
        assert bev_pt is None


# ──────────────────────────────────────────────────────────────────
#  3. SYNTHETIC FOOTPRINT INJECTION
# ──────────────────────────────────────────────────────────────────

class TestFootprintInjection:
    def test_footprint_creates_nonzero_pixels(self):
        engine = NorthernBladesGeometryEngine()
        engine.reset_canvases()

        bev_pt = np.array([512, 512], dtype=np.float32)
        engine.inject_footprint(bev_pt, "Light_Motor", canvas="incoming")

        mass = cv2.countNonZero(engine.canvas_incoming)
        assert mass > 0, "Footprint should create non-zero pixels on the canvas"

    def test_unknown_class_does_not_crash(self):
        engine = NorthernBladesGeometryEngine()
        engine.reset_canvases()
        engine.inject_footprint(np.array([100, 100], dtype=np.float32), "Unknown_Class")
        mass = cv2.countNonZero(engine.canvas_incoming)
        assert mass == 0  # Unknown class should be silently ignored


# ──────────────────────────────────────────────────────────────────
#  4. DOUBLE-COUNT PREVENTION (BITWISE CANVAS)
# ──────────────────────────────────────────────────────────────────

class TestDoubleCountPrevention:
    def test_overlapping_vehicles_do_not_double_count(self):
        """Two overlapping footprints must NOT produce 2x the area."""
        engine = NorthernBladesGeometryEngine()
        engine.reset_canvases()

        same_point = np.array([512, 512], dtype=np.float32)
        engine.inject_footprint(same_point, "Light_Motor", canvas="incoming")
        single_mass = cv2.countNonZero(engine.canvas_incoming)

        # Inject again at exact same location
        engine.inject_footprint(same_point, "Light_Motor", canvas="incoming")
        double_mass = cv2.countNonZero(engine.canvas_incoming)

        assert double_mass == single_mass, \
            f"Overlapping injection should not double-count: {single_mass} vs {double_mass}"

    def test_canvas_never_exceeds_100_percent(self):
        engine = NorthernBladesGeometryEngine(canvas_size=(100, 100))
        engine.reset_canvases()

        # Fill with a massive number of overlapping footprints
        for x in range(0, 100, 5):
            for y in range(0, 100, 5):
                engine.inject_footprint(np.array([x, y], dtype=np.float32), "Heavy_Motor", canvas="incoming")

        result = engine.process_fluid_mass()
        assert result["incoming"]["percentage"] <= 100.0


# ──────────────────────────────────────────────────────────────────
#  5. OCCLUSION FILTER
# ──────────────────────────────────────────────────────────────────

class TestOcclusionFilter:
    def test_hidden_bike_behind_bus_is_dropped(self):
        """A Two_Wheeler mostly inside a Heavy_Motor with higher bottom-Y should be removed."""
        engine = NorthernBladesGeometryEngine()

        detections = [
            {"bbox": [100, 100, 400, 500], "class_id": "Heavy_Motor"},   # Big bus
            {"bbox": [150, 200, 250, 350], "class_id": "Two_Wheeler"},   # Bike hidden behind bus (bottom Y=350 < 500)
        ]

        filtered = engine.filter_occlusions(detections)
        class_ids = [d["class_id"] for d in filtered]

        assert "Heavy_Motor" in class_ids
        assert "Two_Wheeler" not in class_ids, "Occluded bike should be dropped"

    def test_non_overlapping_vehicles_are_kept(self):
        engine = NorthernBladesGeometryEngine()

        detections = [
            {"bbox": [100, 100, 200, 300], "class_id": "Light_Motor"},
            {"bbox": [500, 500, 600, 700], "class_id": "Two_Wheeler"},   # Far away, no overlap
        ]

        filtered = engine.filter_occlusions(detections)
        assert len(filtered) == 2


# ──────────────────────────────────────────────────────────────────
#  6. FULL PIPELINE (process_detections)
# ──────────────────────────────────────────────────────────────────

class TestFullPipeline:
    def test_process_detections_produces_mass(self):
        engine = NorthernBladesGeometryEngine()
        engine.set_global_homography(np.eye(3))
        engine.reset_canvases()

        detections = [
            {"bbox": [100, 100, 200, 300], "class_id": "Light_Motor"},
            {"bbox": [400, 400, 500, 600], "class_id": "Two_Wheeler"},
        ]

        count = engine.process_detections(detections, direction="incoming")
        assert count == 2

        result = engine.process_fluid_mass()
        assert result["incoming"]["percentage"] > 0
        assert result["outgoing"]["percentage"] == 0


# ──────────────────────────────────────────────────────────────────
#  RUN
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
