"""
Week 2 — MediaPipe Body Measurements
Uses the PoseLandmarker (Heavy) model to detect 33 body landmarks,
then converts pixel distances to real-world centimetres.

Auto-downloads model (~29 MB) from Google's MediaPipe CDN on first run.
"""

import io
import math
import logging
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ─── Checkpoint path ──────────────────────────────────────────────────────────
_ML_DIR        = Path(__file__).parent.parent
_CKPT_DIR      = _ML_DIR / "checkpoints"
_POSE_CKPT     = _CKPT_DIR / "pose_landmarker_heavy.task"
_POSE_DL_URL   = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_heavy/float16/latest/"
    "pose_landmarker_heavy.task"
)

# ─── Lazy-loaded state ────────────────────────────────────────────────────────
_landmarker = None
_load_error = None


# ─── MediaPipe landmark indices (COCO-style) ──────────────────────────────────
_LM = {
    "nose":           0,
    "left_shoulder":  11,
    "right_shoulder": 12,
    "left_elbow":     13,
    "right_elbow":    14,
    "left_wrist":     15,
    "right_wrist":    16,
    "left_hip":       23,
    "right_hip":      24,
    "left_knee":      25,
    "right_knee":     26,
    "left_ankle":     27,
    "right_ankle":    28,
    "left_heel":      29,
    "right_heel":     30,
}


# ─── Auto-download ────────────────────────────────────────────────────────────
def _ensure_checkpoint():
    if _POSE_CKPT.exists():
        return
    _CKPT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("⬇️  Downloading MediaPipe PoseLandmarker Heavy (~29 MB)…")
    urllib.request.urlretrieve(_POSE_DL_URL, str(_POSE_CKPT))
    logger.info(f"✅ PoseLandmarker saved → {_POSE_CKPT}")


# ─── Model loader ─────────────────────────────────────────────────────────────
def _load_landmarker():
    global _landmarker, _load_error
    if _landmarker is not None:
        return _landmarker
    if _load_error:
        raise _load_error

    try:
        _ensure_checkpoint()
        import mediapipe as mp
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision as mp_vision

        base_opts = mp_tasks.BaseOptions(model_asset_path=str(_POSE_CKPT))
        opts = mp_vision.PoseLandmarkerOptions(
            base_options=base_opts,
            output_segmentation_masks=False,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        _landmarker = mp_vision.PoseLandmarker.create_from_options(opts)
        logger.info("✅ MediaPipe PoseLandmarker ready")
        return _landmarker

    except ImportError:
        err = ImportError("mediapipe not installed. Run: uv add 'mediapipe>=0.10.14'")
        _load_error = err
        raise err
    except Exception as e:
        _load_error = e
        raise


# ─── Pixel helpers ────────────────────────────────────────────────────────────
def _px_dist(lm_a, lm_b, img_w: int, img_h: int) -> float:
    """Euclidean pixel distance between two normalised landmarks."""
    dx = (lm_a.x - lm_b.x) * img_w
    dy = (lm_a.y - lm_b.y) * img_h
    return math.sqrt(dx * dx + dy * dy)


def _visibility(lm) -> float:
    return getattr(lm, "visibility", 1.0) or 1.0


# ─── Public API ───────────────────────────────────────────────────────────────
def measure_body(
    image_bytes: bytes,
    reference_height_cm: float = 165.0,
) -> dict:
    """
    Estimate body measurements from a full-body photo.

    The caller supplies `reference_height_cm` (person's real height, or a
    population average like 165 cm).  Pixel distances are then scaled to cm
    using the detected head-to-ankle span.

    Args:
        image_bytes: JPEG/PNG of a person standing upright facing the camera
        reference_height_cm: actual or estimated height in cm (default 165)

    Returns:
        {
            "shoulder_cm":  float,   # biacromial distance
            "chest_cm":     float,   # estimated (shoulder × 2.06 ≈ chest girth)
            "waist_cm":     float,   # estimated from mid-torso landmark positions
            "hip_cm":       float,   # bi-trochanteric distance (× 2 → circumference)
            "height_px":    float,   # detected person height in pixels
            "px_per_cm":    float,   # calibration ratio
            "confidence":   float,   # avg landmark visibility (0–1)
            "fallback":     bool,    # True if MediaPipe wasn't available
        }
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h  = image.size

    try:
        landmarker = _load_landmarker()
        return _run_mediapipe(landmarker, image, w, h, reference_height_cm)
    except Exception as e:
        logger.warning(f"⚠️  PoseLandmarker unavailable ({e}) — returning demo measurements")
        return _demo_measurements(reference_height_cm)


def _run_mediapipe(landmarker, image: Image.Image, w: int, h: int, ref_h_cm: float) -> dict:
    import mediapipe as mp

    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.array(image))
    result   = landmarker.detect(mp_image)

    if not result.pose_landmarks:
        logger.warning("No pose detected — returning demo measurements")
        return _demo_measurements(ref_h_cm)

    lm = result.pose_landmarks[0]   # first person

    L = _LM  # alias

    # ── Shoulder width (biacromial) ───────────────────────────────────────────
    shoulder_px = _px_dist(lm[L["left_shoulder"]], lm[L["right_shoulder"]], w, h)

    # ── Hip width (bi-trochanteric) ────────────────────────────────────────────
    hip_px = _px_dist(lm[L["left_hip"]], lm[L["right_hip"]], w, h)

    # ── Waist: interpolated between shoulder and hip, with inward taper ───────
    ls, rs = lm[L["left_shoulder"]], lm[L["right_shoulder"]]
    lh, rh = lm[L["left_hip"]],      lm[L["right_hip"]]
    mid_y   = (ls.y + rs.y + lh.y + rh.y) / 4
    mid_lx  = ls.x + (lh.x - ls.x) * 0.5
    mid_rx  = rs.x + (rh.x - rs.x) * 0.5
    waist_px = abs(mid_rx - mid_lx) * w * 0.88   # slight inward taper

    # ── Height: nose to lower heel (with head allowance) ──────────────────────
    nose        = lm[L["nose"]]
    left_heel   = lm[L["left_heel"]]
    right_heel  = lm[L["right_heel"]]
    lower_heel  = left_heel if left_heel.y > right_heel.y else right_heel
    body_span_y = abs(lower_heel.y - nose.y) * h
    height_px   = body_span_y * 1.12   # +12% for head above nose + sole below heel

    # ── Pixel → cm calibration ────────────────────────────────────────────────
    px_per_cm = height_px / ref_h_cm if height_px > 10 else 1.0

    def width_to_cm(px: float) -> float:
        """Convert a HALF-width measurement (one side) to full cm span."""
        return round(px / px_per_cm, 1)

    shoulder_cm = width_to_cm(shoulder_px)
    hip_cm      = width_to_cm(hip_px)
    waist_cm    = width_to_cm(waist_px)

    # Chest circumference ≈ shoulder_span × 2.06  (empirical average ratio)
    chest_cm = round(shoulder_cm * 2.06, 1)

    # Average visibility score
    key_lms = [L["left_shoulder"], L["right_shoulder"], L["left_hip"], L["right_hip"], L["nose"]]
    confidence = float(np.mean([_visibility(lm[k]) for k in key_lms]))

    return {
        "shoulder_cm": shoulder_cm,
        "chest_cm":    chest_cm,
        "waist_cm":    waist_cm,
        "hip_cm":      hip_cm,
        "height_px":   round(height_px, 1),
        "px_per_cm":   round(px_per_cm, 3),
        "confidence":  round(confidence, 3),
        "fallback":    False,
    }


def _demo_measurements(ref_h_cm: float) -> dict:
    """Synthetic measurements for a 165 cm person (average female)."""
    scale = ref_h_cm / 165.0
    return {
        "shoulder_cm": round(38.5 * scale, 1),
        "chest_cm":    round(88.0 * scale, 1),
        "waist_cm":    round(70.0 * scale, 1),
        "hip_cm":      round(94.0 * scale, 1),
        "height_px":   0.0,
        "px_per_cm":   0.0,
        "confidence":  0.0,
        "fallback":    True,
    }


# ─── Size recommendation helper ───────────────────────────────────────────────
def recommend_size(measurements: dict, brand_chart: dict | None = None) -> str:
    """
    Map body measurements to a clothing size label.
    Uses a simple rule-based lookup (Week 3 will replace with TF model).

    Args:
        measurements: output dict from measure_body()
        brand_chart:  optional brand-specific size chart dict

    Returns:
        size string: "XS" | "S" | "M" | "L" | "XL" | "XXL"
    """
    chest = measurements.get("chest_cm", 88.0)

    chart = brand_chart or {
        "XS": (0,   82),
        "S":  (82,  88),
        "M":  (88,  96),
        "L":  (96, 104),
        "XL": (104, 116),
        "XXL": (116, 999),
    }

    for size, (lo, hi) in chart.items():
        if lo <= chest < hi:
            return size
    return "XL"
