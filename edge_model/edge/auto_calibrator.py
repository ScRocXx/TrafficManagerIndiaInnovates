"""
Northern Blades V5.5 — Dynamic Auto-Calibrator
================================================
Self-healing homography pipeline.

Designed to run as a CRON job every 4 hours, independent of the main
inference loop.  It detects physical camera drift (wind, bumps,
maintenance) and automatically corrects the Homography matrix without
human intervention.

Pipeline:
    1. capture_background()        — MOG2 erases traffic → empty road.
    2. apply_delhi_filter()        — Grayscale + CLAHE flattens shadows.
    3. extract_and_match_features()— ORB keypoints + BFMatcher.
    4. calculate_correction_matrix()— RANSAC homography from matched pts.
    5. heal_geometry_engine()      — H_new = H_golden × ΔH → save.
"""

import cv2
import numpy as np
import json
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="[AUTO-CAL %(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────

# Paths — override via environment variables or direct edit.
GOLDEN_IMAGE_PATH = os.environ.get(
    "NB_GOLDEN_IMAGE", "edge/golden_reference.png"
)
CALIBRATION_CONFIG_PATH = os.environ.get(
    "NB_CALIBRATION_CONFIG", "edge/calibration_config.json"
)
VIDEO_SOURCE = os.environ.get("NB_VIDEO_SOURCE", "0")  # camera index or RTSP url

# MOG2 background extraction duration (seconds).
BG_CAPTURE_DURATION = int(os.environ.get("NB_BG_DURATION", 300))  # 5 minutes

# CLAHE parameters (The "Delhi Fix")
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID = (8, 8)

# ORB parameters
ORB_MAX_FEATURES = 1000

# RANSAC reprojection threshold (pixels)
RANSAC_THRESH = 5.0

# Minimum number of good matches required to compute a correction.
# If fewer matches are found, the calibration is skipped (safety guard).
MIN_GOOD_MATCHES = 20

# Maximum allowed reprojection error.  If the average reprojection
# error exceeds this, the correction is rejected as too unstable.
MAX_REPROJ_ERROR = 10.0


# ──────────────────────────────────────────────────────────────────
#  STEP 1 — BACKGROUND EXTRACTION (Erase Traffic)
# ──────────────────────────────────────────────────────────────────

def capture_background(video_source=VIDEO_SOURCE, duration_seconds=BG_CAPTURE_DURATION):
    """
    Capture footage and apply MOG2 to extract a traffic-free
    background image of the intersection.

    Because cars are always moving, the median / MOG2 algorithm
    mathematically erases them, leaving only the static asphalt,
    lane markings, curbs, and road geometry.

    Parameters
    ----------
    video_source : str | int
        Camera index or RTSP URL.
    duration_seconds : int
        How many seconds of footage to process.

    Returns
    -------
    np.ndarray | None
        The extracted background image (BGR), or None on failure.
    """
    log.info("Starting background extraction (%ds) from source: %s", duration_seconds, video_source)

    try:
        src = int(video_source)
    except ValueError:
        src = video_source

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        log.error("Cannot open video source: %s", video_source)
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(fps * duration_seconds)

    # MOG2 background subtractor — high history for stable convergence
    bg_sub = cv2.createBackgroundSubtractorMOG2(
        history=min(total_frames, 5000),
        varThreshold=16,
        detectShadows=False,
    )

    background = None
    frames_read = 0

    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            break
        bg_sub.apply(frame)
        background = frame  # keep last frame as geometry reference
        frames_read += 1

    cap.release()

    if frames_read == 0:
        log.error("No frames read from source.")
        return None

    # Retrieve the learned background model
    bg_image = bg_sub.getBackgroundImage()
    if bg_image is None:
        log.warning("MOG2 did not converge; using last raw frame as fallback.")
        bg_image = background

    log.info("Background extracted successfully (%d frames processed).", frames_read)
    return bg_image


# ──────────────────────────────────────────────────────────────────
#  STEP 2 — DELHI SHADOW FILTER (CLAHE)
# ──────────────────────────────────────────────────────────────────

def apply_delhi_filter(image):
    """
    Neutralise harsh sun / shadow lines by converting to grayscale
    and applying CLAHE (Contrast Limited Adaptive Histogram
    Equalization).

    This makes ORB match on *physical geometry* (cracks, lane
    markings, curbs) rather than on transient shadow edges.

    Parameters
    ----------
    image : np.ndarray  (BGR)

    Returns
    -------
    np.ndarray  (single-channel, CLAHE-enhanced)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID)
    return clahe.apply(gray)


# ──────────────────────────────────────────────────────────────────
#  STEP 3 — FEATURE EXTRACTION & MATCHING
# ──────────────────────────────────────────────────────────────────

def extract_and_match_features(golden_img, current_img):
    """
    Find ORB keypoints in both images and match them using a
    Brute-Force Hamming matcher with cross-check.

    Parameters
    ----------
    golden_img  : np.ndarray  (grayscale, CLAHE-enhanced)
    current_img : np.ndarray  (grayscale, CLAHE-enhanced)

    Returns
    -------
    tuple (src_pts, dst_pts, num_matches)
        src_pts / dst_pts are np.ndarray of shape (N, 2) or None.
    """
    orb = cv2.ORB_create(nfeatures=ORB_MAX_FEATURES)

    kp1, des1 = orb.detectAndCompute(golden_img, None)
    kp2, des2 = orb.detectAndCompute(current_img, None)

    if des1 is None or des2 is None or len(des1) < MIN_GOOD_MATCHES or len(des2) < MIN_GOOD_MATCHES:
        log.warning("Insufficient features detected (golden: %s, current: %s).",
                     len(des1) if des1 is not None else 0,
                     len(des2) if des2 is not None else 0)
        return None, None, 0

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    # Sort by distance (best matches first)
    matches = sorted(matches, key=lambda m: m.distance)

    if len(matches) < MIN_GOOD_MATCHES:
        log.warning("Only %d matches found (need %d). Skipping calibration.", len(matches), MIN_GOOD_MATCHES)
        return None, None, len(matches)

    src_pts = np.float32([kp1[m.queryIdx].pt for m in matches])
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches])

    log.info("Matched %d keypoints between golden and current image.", len(matches))
    return src_pts, dst_pts, len(matches)


# ──────────────────────────────────────────────────────────────────
#  STEP 4 — CORRECTION MATRIX (RANSAC)
# ──────────────────────────────────────────────────────────────────

def calculate_correction_matrix(src_pts, dst_pts):
    """
    Compute the geometric shift ΔH between the golden and current
    camera orientations using RANSAC.

    Parameters
    ----------
    src_pts : np.ndarray  shape (N, 2) — keypoints from golden image
    dst_pts : np.ndarray  shape (N, 2) — keypoints from current image

    Returns
    -------
    np.ndarray (3×3) | None
    """
    if src_pts is None or dst_pts is None:
        return None

    delta_H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, RANSAC_THRESH)

    if delta_H is None:
        log.warning("RANSAC failed to find a homography.")
        return None

    # ── Safety check: reject wild corrections ──────────────────
    inliers = mask.ravel().sum() if mask is not None else 0
    inlier_ratio = inliers / len(src_pts)
    log.info("RANSAC inliers: %d / %d (%.1f%%)", inliers, len(src_pts), inlier_ratio * 100)

    if inlier_ratio < 0.40:
        log.warning("Inlier ratio too low (%.1f%%). Rejecting correction.", inlier_ratio * 100)
        return None

    # Check average reprojection error on inliers
    src_inliers = src_pts[mask.ravel() == 1]
    dst_inliers = dst_pts[mask.ravel() == 1]
    projected = cv2.perspectiveTransform(src_inliers.reshape(-1, 1, 2), delta_H).reshape(-1, 2)
    errors = np.linalg.norm(projected - dst_inliers, axis=1)
    avg_error = errors.mean()
    log.info("Average reprojection error: %.2f px", avg_error)

    if avg_error > MAX_REPROJ_ERROR:
        log.warning("Reprojection error too high (%.2f px). Rejecting correction.", avg_error)
        return None

    return delta_H


# ──────────────────────────────────────────────────────────────────
#  STEP 5 — HEAL THE GEOMETRY ENGINE
# ──────────────────────────────────────────────────────────────────

def heal_geometry_engine(delta_H, config_path=CALIBRATION_CONFIG_PATH):
    """
    Apply the correction matrix to all homography matrices stored
    in the calibration config.

    H_new = H_golden × ΔH

    The updated config is written back to disk so that the running
    geometry_engine.py picks it up on its next reload.

    Parameters
    ----------
    delta_H     : np.ndarray (3×3)
    config_path : str
    """
    if delta_H is None:
        log.info("No correction needed — matrices unchanged.")
        return

    if not os.path.exists(config_path):
        log.error("Calibration config not found at: %s", config_path)
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    # Correct the global H
    if "global_H" in config:
        H_old = np.array(config["global_H"], dtype=np.float64)
        H_new = H_old @ delta_H
        config["global_H"] = H_new.tolist()
        log.info("Healed global_H matrix.")

    # Correct each zone's H
    for zone in config.get("zones", []):
        H_old = np.array(zone["H"], dtype=np.float64)
        H_new = H_old @ delta_H
        zone["H"] = H_new.tolist()
        log.info("Healed zone '%s' matrix.", zone["name"])

    # Timestamp the heal
    config["last_calibration"] = datetime.now().isoformat()

    # Write back
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)

    log.info("Calibration config updated at: %s", config_path)


# ──────────────────────────────────────────────────────────────────
#  MAIN — THE 4-HOUR CRON ENTRY POINT
# ──────────────────────────────────────────────────────────────────

def run_auto_calibration():
    """
    Full self-healing pipeline.  Call this from a cron job or
    a scheduled task every 4 hours.
    """
    log.info("=" * 60)
    log.info("NORTHERN BLADES AUTO-CALIBRATOR — Starting cycle")
    log.info("=" * 60)

    # 1. Load golden reference
    if not os.path.exists(GOLDEN_IMAGE_PATH):
        log.error("Golden reference image not found: %s", GOLDEN_IMAGE_PATH)
        return

    golden_raw = cv2.imread(GOLDEN_IMAGE_PATH)
    if golden_raw is None:
        log.error("Failed to read golden image.")
        return

    # 2. Capture current background (erase traffic)
    current_raw = capture_background()
    if current_raw is None:
        return

    # 3. Apply Delhi Filter to both
    golden_filtered = apply_delhi_filter(golden_raw)
    current_filtered = apply_delhi_filter(current_raw)

    # 4. Match features
    src_pts, dst_pts, num_matches = extract_and_match_features(golden_filtered, current_filtered)

    # 5. Compute correction
    delta_H = calculate_correction_matrix(src_pts, dst_pts)

    # 6. Heal
    heal_geometry_engine(delta_H)

    log.info("Auto-calibration cycle complete.")
    log.info("=" * 60)


if __name__ == "__main__":
    run_auto_calibration()
