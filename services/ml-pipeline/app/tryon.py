"""
VirtualFit — YouCam API (Perfect Corp) Multi-Feature Try-On
============================================================
All inference runs in Perfect Corp's cloud — no local ML models needed.

Features:
  👔 Clothes  — upper / lower / full body clothing try-on
  👜 Bag      — handbag / purse try-on
  💄 Makeup   — lip color, blush, eye shadow, eyeliner, foundation
  👁️ Eye Color — colored contact lens try-on
  🎩 Hat      — hat / cap try-on
  👟 Shoes    — footwear try-on

API Docs:  https://docs.perfectcorp.com/reference
Register:  https://yce.makeupar.com/ai-api
"""

import io
import logging
import os
import time
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

_BASE = "https://yce-api-01.makeupar.com"

# Load .env so key is available even when tryon.py is imported before main.py lifespan
try:
    from dotenv import load_dotenv as _load_dotenv
    import pathlib as _pathlib
    _env = _pathlib.Path(__file__).parent.parent.parent.parent / ".env"
    if _env.exists():
        _load_dotenv(_env, override=False)
except ImportError:
    pass


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _api_key() -> str:
    """Read key at call time — not at import time — so dotenv always works."""
    return os.environ.get("YOUCAM_API_KEY", "").strip()


def _headers() -> dict:
    return {"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"}


def _check_key():
    if not _api_key():
        raise RuntimeError(
            "YOUCAM_API_KEY not set.\n"
            "Register free at https://yce.makeupar.com/ai-api\n"
            "Then add to .env:  YOUCAM_API_KEY=your_key_here"
        )


def _upload(img_bytes: bytes, fname: str) -> str:
    """Upload image bytes via YouCam File API → return file_id."""
    import requests as req

    r = req.post(
        f"{_BASE}/s2s/v2.0/file",
        headers=_headers(),
        json={"files": [{"content_type": "image/jpg", "file_name": fname, "file_size": len(img_bytes)}]},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"YouCam File API {r.status_code}: {r.text[:200]}")

    f       = r.json()["data"]["files"][0]
    file_id = f["file_id"]
    put     = f["requests"][0]
    hdrs    = {k: str(v) for k, v in put.get("headers", {}).items()}
    hdrs["Content-Type"] = "image/jpg"

    s3r = req.put(put["url"], data=img_bytes, headers=hdrs, timeout=60)
    if not s3r.ok:
        raise RuntimeError(f"S3 upload {s3r.status_code}: {s3r.text[:200]}")

    logger.debug(f"✅ Uploaded {fname} → file_id acquired")
    return file_id


def _poll(endpoint: str, task_id: str, timeout_s: int = 120) -> bytes:
    """Poll YouCam task until success → return result JPEG bytes."""
    import requests as req

    for attempt in range(timeout_s // 2):
        time.sleep(2)
        r = req.get(f"{_BASE}{endpoint}/{task_id}", headers=_headers(), timeout=30)
        if not r.ok:
            logger.debug(f"Poll #{attempt+1} error {r.status_code}")
            continue

        data   = r.json().get("data", {})
        status = data.get("task_status")
        logger.debug(f"Poll #{attempt+1}: {status}")

        if status == "success":
            result_url = (data.get("results") or {}).get("url")
            if not result_url:
                raise RuntimeError(f"No result URL in response: {data}")
            return req.get(result_url, timeout=60).content

        if status in ("failed", "error"):
            err = data.get("error") or data.get("failure_reason") or "unknown"
            raise RuntimeError(f"YouCam task failed: {err}")

    raise TimeoutError(f"YouCam task timed out after {timeout_s}s")


def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


# ─── Feature 1: Clothes Try-On ────────────────────────────────────────────────

def run_clothes_tryon(
    person_bytes: bytes,
    garment_bytes: bytes,
    category: str = "upper_body",  # "upper_body" | "lower_body" | "full_body"
) -> dict:
    """Virtual clothing try-on (shirt, dress, pants, jacket, full outfit)."""
    _check_key()
    t0 = time.time()
    logger.info(f"👔 Clothes try-on ({category}) — uploading…")

    src_id = _upload(person_bytes,  "person.jpg")
    ref_id = _upload(garment_bytes, "garment.jpg")

    import requests as req
    r = req.post(
        f"{_BASE}/s2s/v2.0/task/cloth-v4",
        headers=_headers(),
        json={"src_file_id": src_id, "ref_file_id": ref_id, "garment_category": category},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Cloth task error {r.status_code}: {r.text}")
    task_id = r.json()["data"]["task_id"]
    logger.info(f"👔 Task {task_id} — polling…")

    result = _poll("/s2s/v2.0/task/cloth-v4", task_id)
    return {
        "result_image":     result,
        "inference_time_s": round(time.time() - t0, 2),
        "mode":             "youcam_clothes",
        "device":           "cloud",
        "feature":          "clothes",
        "category":         category,
    }


# ─── Feature 2: Bag Try-On ───────────────────────────────────────────────────

def run_bag_tryon(
    person_bytes: bytes,
    bag_bytes: bytes,
    gender: str = "female",   # "male" | "female"
    style:  str = "random",   # "random" | "style_parisian_chic" | "style_urban_chic"
                              # "style_mediterranean_chic" | "style_art_deco_style"
) -> dict:
    """Virtual handbag / purse try-on."""
    _check_key()
    t0 = time.time()
    logger.info(f"👜 Bag try-on ({gender}, {style}) — uploading…")

    src_id = _upload(person_bytes, "person.jpg")
    ref_id = _upload(bag_bytes,    "bag.jpg")

    import requests as req
    r = req.post(
        f"{_BASE}/s2s/v2.0/task/bag",
        headers=_headers(),
        json={"src_file_id": src_id, "ref_file_id": ref_id, "gender": gender, "style": style},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Bag task error {r.status_code}: {r.text}")
    task_id = r.json()["data"]["task_id"]
    logger.info(f"👜 Task {task_id} — polling…")

    result = _poll("/s2s/v2.0/task/bag", task_id)
    return {
        "result_image":     result,
        "inference_time_s": round(time.time() - t0, 2),
        "mode":             "youcam_bag",
        "device":           "cloud",
        "feature":          "bag",
    }


# ─── Feature 3: Makeup Try-On ────────────────────────────────────────────────

# Preset makeup looks — each is a list of YouCam effect objects
MAKEUP_PRESETS = {
    "natural": [
        {
            "category": "skin_smooth",
            "skinSmoothStrength": 45,
            "skinSmoothColorIntensity": 35,
        },
        {
            "category": "blush",
            "pattern": {"name": "1color1"},
            "palettes": [{"color": "#F2A090", "texture": "matte", "colorIntensity": 40}],
        },
        {
            "category": "lip_color",
            "shape": {"name": "original"},
            "style": {"type": "full"},
            "palettes": [{"color": "#C47070", "texture": "gloss", "colorIntensity": 60, "gloss": 55}],
        },
    ],
    "glam": [
        {
            "category": "skin_smooth",
            "skinSmoothStrength": 60,
            "skinSmoothColorIntensity": 50,
        },
        {
            "category": "eye_shadow",
            "pattern": {"name": "2colors1"},
            "palettes": [
                {"color": "#8B0000", "texture": "shimmer", "colorIntensity": 65,
                 "shimmerColor": "#FF6060", "shimmerIntensity": 50, "shimmerDensity": 50, "shimmerSize": 50},
                {"color": "#4A0000", "texture": "matte",   "colorIntensity": 55},
            ],
        },
        {
            "category": "blush",
            "pattern": {"name": "2colors6"},
            "palettes": [
                {"color": "#FF6B6B", "texture": "matte", "colorIntensity": 55},
                {"color": "#E85D5D", "texture": "matte", "colorIntensity": 50},
            ],
        },
        {
            "category": "lip_color",
            "shape": {"name": "plump"},
            "style": {"type": "full"},
            "palettes": [{"color": "#CC0000", "texture": "matte", "colorIntensity": 85}],
        },
    ],
    "bold_lips": [
        {
            "category": "skin_smooth",
            "skinSmoothStrength": 50,
            "skinSmoothColorIntensity": 40,
        },
        {
            "category": "lip_color",
            "shape": {"name": "original"},
            "style": {"type": "full"},
            "palettes": [{"color": "#8B0057", "texture": "matte", "colorIntensity": 90}],
        },
    ],
    "smoky_eye": [
        {
            "category": "skin_smooth",
            "skinSmoothStrength": 55,
            "skinSmoothColorIntensity": 45,
        },
        {
            "category": "eye_shadow",
            "pattern": {"name": "3colors1"},
            "palettes": [
                {"color": "#1A1A1A", "texture": "shimmer", "colorIntensity": 80,
                 "shimmerColor": "#555555", "shimmerIntensity": 60, "shimmerDensity": 55, "shimmerSize": 50},
                {"color": "#333333", "texture": "matte",   "colorIntensity": 70},
                {"color": "#0D0D0D", "texture": "matte",   "colorIntensity": 85},
            ],
        },
        {
            "category": "blush",
            "pattern": {"name": "1color1"},
            "palettes": [{"color": "#C97070", "texture": "matte", "colorIntensity": 35}],
        },
        {
            "category": "lip_color",
            "shape": {"name": "original"},
            "style": {"type": "full"},
            "palettes": [{"color": "#8B2525", "texture": "matte", "colorIntensity": 75}],
        },
    ],
}


def run_makeup_tryon(
    person_bytes: bytes,
    preset: str = "natural",           # key from MAKEUP_PRESETS
    custom_effects: Optional[list] = None,  # override with raw YouCam effects list
) -> dict:
    """Virtual makeup try-on. Use preset name or pass raw effects list."""
    _check_key()
    t0 = time.time()

    effects = custom_effects or MAKEUP_PRESETS.get(preset, MAKEUP_PRESETS["natural"])
    logger.info(f"💄 Makeup try-on (preset={preset}) — uploading…")

    src_id = _upload(person_bytes, "face.jpg")

    import requests as req
    r = req.post(
        f"{_BASE}/s2s/v2.0/task/makeup-vto",
        headers=_headers(),
        json={"src_file_id": src_id, "effects": effects, "version": "1.0"},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Makeup task error {r.status_code}: {r.text}")
    task_id = r.json()["data"]["task_id"]
    logger.info(f"💄 Task {task_id} — polling…")

    result = _poll("/s2s/v2.0/task/makeup-vto", task_id)
    return {
        "result_image":     result,
        "inference_time_s": round(time.time() - t0, 2),
        "mode":             "youcam_makeup",
        "device":           "cloud",
        "feature":          "makeup",
        "preset":           preset,
    }


# ─── Feature 4: Eye Color Try-On ─────────────────────────────────────────────

EYE_COLOR_PRESETS = {
    "blue":       "#2E86AB",
    "green":      "#2D6A4F",
    "gray":       "#6B7280",
    "hazel":      "#8B6914",
    "violet":     "#7B2D8B",
    "amber":      "#C97D12",
    "ice_blue":   "#A8D8EA",
    "honey":      "#B5860D",
}


def run_eye_color_tryon(
    person_bytes: bytes,
    color_hex: str = "#2E86AB",   # hex color or key from EYE_COLOR_PRESETS
) -> dict:
    """Virtual colored contact lens try-on."""
    _check_key()
    t0 = time.time()

    # Allow preset name as shorthand
    color = EYE_COLOR_PRESETS.get(color_hex, color_hex)
    logger.info(f"👁️ Eye color try-on ({color}) — uploading…")

    src_id = _upload(person_bytes, "face.jpg")

    import requests as req
    r = req.post(
        f"{_BASE}/s2s/v2.0/task/eye-color-lens",
        headers=_headers(),
        json={"src_file_id": src_id, "color": color},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Eye color task error {r.status_code}: {r.text}")
    task_id = r.json()["data"]["task_id"]
    logger.info(f"👁️ Task {task_id} — polling…")

    result = _poll("/s2s/v2.0/task/eye-color-lens", task_id)
    return {
        "result_image":     result,
        "inference_time_s": round(time.time() - t0, 2),
        "mode":             "youcam_eye_color",
        "device":           "cloud",
        "feature":          "eye_color",
        "color":            color,
    }


# ─── Feature 5: Hat Try-On ───────────────────────────────────────────────────

def run_hat_tryon(person_bytes: bytes, hat_bytes: bytes) -> dict:
    """Virtual hat / cap try-on."""
    _check_key()
    t0 = time.time()
    logger.info("🎩 Hat try-on — uploading…")

    src_id = _upload(person_bytes, "person.jpg")
    ref_id = _upload(hat_bytes,    "hat.jpg")

    import requests as req
    r = req.post(
        f"{_BASE}/s2s/v2.0/task/hat",
        headers=_headers(),
        json={"src_file_id": src_id, "ref_file_id": ref_id},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Hat task error {r.status_code}: {r.text}")
    task_id = r.json()["data"]["task_id"]
    logger.info(f"🎩 Task {task_id} — polling…")

    result = _poll("/s2s/v2.0/task/hat", task_id)
    return {
        "result_image":     result,
        "inference_time_s": round(time.time() - t0, 2),
        "mode":             "youcam_hat",
        "device":           "cloud",
        "feature":          "hat",
    }


# ─── Feature 6: Shoes Try-On ─────────────────────────────────────────────────

def run_shoes_tryon(person_bytes: bytes, shoes_bytes: bytes) -> dict:
    """Virtual footwear try-on."""
    _check_key()
    t0 = time.time()
    logger.info("👟 Shoes try-on — uploading…")

    src_id = _upload(person_bytes,  "person.jpg")
    ref_id = _upload(shoes_bytes,   "shoes.jpg")

    import requests as req
    r = req.post(
        f"{_BASE}/s2s/v2.0/task/shoes",
        headers=_headers(),
        json={"src_file_id": src_id, "ref_file_id": ref_id},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Shoes task error {r.status_code}: {r.text}")
    task_id = r.json()["data"]["task_id"]
    logger.info(f"👟 Task {task_id} — polling…")

    result = _poll("/s2s/v2.0/task/shoes", task_id)
    return {
        "result_image":     result,
        "inference_time_s": round(time.time() - t0, 2),
        "mode":             "youcam_shoes",
        "device":           "cloud",
        "feature":          "shoes",
    }


# ─── Legacy entry points (backward compat) ────────────────────────────────────

def run_tryon(
    person_bytes: bytes,
    garment_bytes: bytes,
    person_mask_bytes: Optional[bytes] = None,
    **kwargs,
) -> dict:
    """Legacy route — delegates to clothes try-on."""
    return run_clothes_tryon(person_bytes, garment_bytes)


def model_status() -> dict:
    return {
        "mode":            "youcam" if _api_key() else "no_key",
        "device":          "cloud",
        "youcam_enabled":  bool(_api_key()),
        "features":        ["clothes", "bag", "makeup", "eye_color", "hat", "shoes"],
        "note":            "YouCam API (Perfect Corp) — photorealistic cloud inference, no local GPU needed",
        "register":        "https://yce.makeupar.com/ai-api",
    }
