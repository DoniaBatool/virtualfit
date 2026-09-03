"""
Week 2 — SAM2 Body Segmentation
Meta's Segment Anything Model 2 to isolate person from background.

Auto-downloads checkpoint from HuggingFace hub on first run (~900 MB).
Uses MPS (Metal) on Apple Silicon, CUDA on NVIDIA, CPU fallback.
"""

import io
import logging
import os
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ─── Checkpoint paths ─────────────────────────────────────────────────────────
_ML_DIR     = Path(__file__).parent.parent          # services/ml-pipeline/
_CKPT_DIR   = _ML_DIR / "checkpoints"
_SAM2_CKPT  = _CKPT_DIR / "sam2.1_hiera_large.pt"
_SAM2_CFG   = "configs/sam2.1/sam2.1_hiera_l.yaml"  # bundled inside sam2 package

# ─── Lazy-loaded state ────────────────────────────────────────────────────────
_predictor  = None
_load_error = None


# ─── Device helper ────────────────────────────────────────────────────────────
def _get_device() -> str:
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# ─── Auto-download SAM2 checkpoint ────────────────────────────────────────────
def _ensure_checkpoint():
    """Download SAM2-Large checkpoint from HuggingFace if not present."""
    if _SAM2_CKPT.exists():
        return
    _CKPT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("⬇️  Downloading SAM2.1-Hiera-Large from HuggingFace (~900 MB)…")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id="facebook/sam2.1-hiera-large",
            filename="sam2.1_hiera_large.pt",
            local_dir=str(_CKPT_DIR),
        )
        logger.info(f"✅ SAM2 checkpoint saved → {path}")
    except Exception as e:
        logger.error(f"❌ SAM2 checkpoint download failed: {e}")
        raise


# ─── Model loader ─────────────────────────────────────────────────────────────
def _load_predictor():
    global _predictor, _load_error
    if _predictor is not None:
        return _predictor
    if _load_error:
        raise _load_error

    try:
        _ensure_checkpoint()
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        device = _get_device()
        logger.info(f"🔄 Loading SAM2 on {device}…")

        model = build_sam2(_SAM2_CFG, str(_SAM2_CKPT), device=device)
        _predictor = SAM2ImagePredictor(model)
        logger.info("✅ SAM2 ready")
        return _predictor

    except ImportError:
        err = ImportError(
            "sam2 package not installed. Run: uv add 'sam2>=1.0.0'"
        )
        _load_error = err
        raise err
    except Exception as e:
        _load_error = e
        raise


# ─── Public API ───────────────────────────────────────────────────────────────
def segment_person(image_bytes: bytes, auto_load: bool = True) -> dict:
    """
    Segment the main person in the image and remove the background.

    Args:
        image_bytes: JPEG/PNG bytes of a person photo
        auto_load: load model on first call (default True)

    Returns:
        {
            "masked_image": bytes,       # RGBA PNG — background transparent
            "mask": list[list[bool]],    # 2-D boolean mask (H×W)
            "bbox": [x1, y1, x2, y2],   # tight bounding box around person
            "score": float,              # SAM2 mask confidence
            "fallback": bool,            # True if SAM2 wasn't available
        }
    """
    image  = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_np = np.array(image)
    h, w   = img_np.shape[:2]

    # ── Try SAM2 inference ────────────────────────────────────────────────────
    if auto_load:
        try:
            predictor = _load_predictor()
            return _run_sam2(predictor, image, img_np, w, h)
        except Exception as e:
            logger.warning(f"⚠️  SAM2 unavailable ({e}) — using full-image fallback")

    # ── Fallback: full image = person (no background removal) ─────────────────
    mask = np.ones((h, w), dtype=bool)
    rgba = image.convert("RGBA")
    buf  = io.BytesIO()
    rgba.save(buf, format="PNG")
    return {
        "masked_image": buf.getvalue(),
        "mask":         mask.tolist(),
        "bbox":         [0, 0, w, h],
        "score":        1.0,
        "fallback":     True,
    }


def _run_sam2(predictor, image: Image.Image, img_np: np.ndarray, w: int, h: int) -> dict:
    """Internal: run SAM2 with two complementary point prompts."""
    import torch

    predictor.set_image(img_np)

    # Two foreground points: upper-body centre + lower-body centre
    # Persons are usually centred; slight head-bias for the upper point.
    point_coords = np.array([
        [w // 2, int(h * 0.30)],   # upper body
        [w // 2, int(h * 0.60)],   # lower body
    ])
    point_labels = np.array([1, 1])   # both foreground

    with torch.inference_mode():
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True,
        )

    # Take highest-scoring mask
    best = int(np.argmax(scores))
    mask = masks[best].astype(bool)    # (H, W)

    # Build RGBA with background removed
    alpha = Image.fromarray((mask * 255).astype(np.uint8), mode="L")
    rgba  = image.convert("RGBA")
    rgba.putalpha(alpha)

    # Tight bounding box
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    rmin, rmax = int(np.where(rows)[0][[0, -1]].tolist()[0]), int(np.where(rows)[0][[0, -1]].tolist()[1])
    cmin, cmax = int(np.where(cols)[0][[0, -1]].tolist()[0]), int(np.where(cols)[0][[0, -1]].tolist()[1])

    buf = io.BytesIO()
    rgba.save(buf, format="PNG")

    return {
        "masked_image": buf.getvalue(),
        "mask":         mask.tolist(),
        "bbox":         [cmin, rmin, cmax, rmax],
        "score":        float(scores[best]),
        "fallback":     False,
    }
