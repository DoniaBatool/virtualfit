"""
VirtualFit ML Pipeline — YouCam Edition
========================================
FastAPI service: Perfect Corp YouCam API (cloud inference, no local GPU needed)
Port: 8001

Features:
  👔  POST /api/tryon      — clothes try-on (upper / lower / full body)
  👜  POST /api/bag        — handbag / purse try-on
  💄  POST /api/makeup     — makeup try-on (lip color, blush, eye shadow, …)
  👁️  POST /api/eye-color  — colored contact lens try-on
  🎩  POST /api/hat        — hat / cap try-on
  👟  POST /api/shoes      — footwear try-on
  📐  POST /api/measure    — body measurements (simple estimator)
  ❤️  GET  /health         — service readiness
"""

import asyncio
import base64
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from app.tryon import (
    run_tryon,
    run_clothes_tryon,
    run_bag_tryon,
    run_makeup_tryon,
    run_eye_color_tryon,
    run_hat_tryon,
    run_shoes_tryon,
    model_status,
    MAKEUP_PRESETS,
    EYE_COLOR_PRESETS,
)
from app.storage import save_result

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

# ── Load .env from project root (picks up YOUCAM_API_KEY etc.) ───────────────
try:
    from dotenv import load_dotenv
    import pathlib
    _root = pathlib.Path(__file__).parent.parent.parent.parent
    _env  = _root / ".env"
    if _env.exists():
        load_dotenv(_env)
        logger.info(f"📄 Loaded .env from {_env}")
except ImportError:
    pass

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


# ─── Startup ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    youcam_key = os.environ.get("YOUCAM_API_KEY", "")
    if youcam_key:
        logger.info("✅ YOUCAM_API_KEY detected — all features ready (Perfect Corp cloud)")
    else:
        logger.warning(
            "⚠️  YOUCAM_API_KEY not set!\n"
            "   All try-on features require this key.\n"
            "   Register free at: https://yce.makeupar.com/ai-api\n"
            "   Then add to .env:  YOUCAM_API_KEY=your_key_here"
        )
    yield
    logger.info("👋 ML Pipeline shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="VirtualFit ML Pipeline",
    description=(
        "YouCam AI (Perfect Corp) — photorealistic virtual try-on in the cloud.\n\n"
        "Supports: 👔 Clothes · 👜 Bag · 💄 Makeup · 👁️ Eye Color · 🎩 Hat · 👟 Shoes"
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3004",
        "http://localhost:3002",
        "http://localhost:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _validate_image(upload: UploadFile, field: str):
    if upload.content_type not in ALLOWED_MIME:
        raise HTTPException(422, f"{field} must be JPEG, PNG, or WebP")


def _b64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode()


def _err(e: Exception, status_code: int = 500):
    msg = str(e)
    logger.error(f"Pipeline error: {msg}")
    if "YOUCAM_API_KEY" in msg:
        raise HTTPException(503, detail="YouCam API key not configured. See /health for instructions.")
    raise HTTPException(status_code, detail=msg)


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status":   "ok",
        "service":  "ml-pipeline",
        "version":  "3.0.0",
        "port":     8001,
        **model_status(),
    }


# ─── 👔 Clothes Try-On ────────────────────────────────────────────────────────
@app.post("/api/tryon")
async def try_on(
    person_image:  UploadFile = File(..., description="Full-body person photo"),
    garment_image: UploadFile = File(..., description="Clothing item photo"),
    category:      str        = Query(
        default="upper_body",
        description="Garment category: upper_body | lower_body | full_body",
    ),
    save_to_minio: bool = Query(default=True),
):
    """
    Virtual clothing try-on powered by YouCam AI.

    Upload a person photo and a clothing item photo.
    YouCam places the garment realistically onto the person.

    Returns:
        - result_image_b64: try-on result as base64 JPEG
        - result_url: MinIO storage URL (if MinIO is running)
        - inference_time_s: total round-trip time
        - mode: always "youcam_clothes"
    """
    _validate_image(person_image,  "person_image")
    _validate_image(garment_image, "garment_image")

    person_bytes  = await person_image.read()
    garment_bytes = await garment_image.read()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_clothes_tryon, person_bytes, garment_bytes, category
        )
    except Exception as e:
        _err(e)

    result_url = None
    if save_to_minio:
        try:
            result_url = save_result(result["result_image"])
        except Exception:
            pass

    return {
        "result_image_b64": _b64(result["result_image"]),
        "result_url":       result_url,
        "inference_time_s": result["inference_time_s"],
        "mode":             result["mode"],
        "device":           result["device"],
        "category":         result.get("category"),
    }


# ─── /api/tryon/status ────────────────────────────────────────────────────────
@app.get("/api/tryon/status")
async def tryon_status():
    """Available features and API key status."""
    return model_status()


# ─── 👜 Bag Try-On ────────────────────────────────────────────────────────────
BAG_STYLES = ["random", "style_parisian_chic", "style_urban_chic",
              "style_mediterranean_chic", "style_art_deco_style"]

@app.post("/api/bag")
async def bag_tryon(
    person_image: UploadFile = File(..., description="Full-body person photo"),
    bag_image:    UploadFile = File(..., description="Handbag / purse photo"),
    gender: str = Query(default="female", description="male | female"),
    style:  str = Query(
        default="random",
        description="Style preset: random | style_parisian_chic | style_urban_chic | "
                    "style_mediterranean_chic | style_art_deco_style",
    ),
    save_to_minio: bool = Query(default=True),
):
    """
    Virtual handbag / purse try-on.

    YouCam places the bag realistically on or beside the person.

    Style presets choose the pose / scene aesthetic:
    - random: let YouCam choose
    - style_parisian_chic: elegant Parisian look
    - style_urban_chic: modern city style
    - style_mediterranean_chic: warm Mediterranean vibes
    - style_art_deco_style: bold geometric aesthetic
    """
    _validate_image(person_image, "person_image")
    _validate_image(bag_image,    "bag_image")

    if style not in BAG_STYLES:
        raise HTTPException(422, f"style must be one of: {BAG_STYLES}")

    person_bytes = await person_image.read()
    bag_bytes    = await bag_image.read()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_bag_tryon, person_bytes, bag_bytes, gender, style
        )
    except Exception as e:
        _err(e)

    result_url = None
    if save_to_minio:
        try:
            result_url = save_result(result["result_image"])
        except Exception:
            pass

    return {
        "result_image_b64": _b64(result["result_image"]),
        "result_url":       result_url,
        "inference_time_s": result["inference_time_s"],
        "mode":             result["mode"],
        "device":           result["device"],
    }


# ─── 💄 Makeup Try-On ────────────────────────────────────────────────────────
class MakeupRequest(BaseModel):
    preset:         str        = "natural"  # key from MAKEUP_PRESETS
    custom_effects: Optional[List[dict]] = None  # raw YouCam effects list


@app.post("/api/makeup")
async def makeup_tryon(
    person_image:  UploadFile = File(..., description="Face / portrait photo"),
    preset:        str        = Query(
        default="natural",
        description="Makeup preset: natural | glam | bold_lips | smoky_eye",
    ),
    save_to_minio: bool = Query(default=True),
):
    """
    Virtual makeup try-on.

    Available presets:
    - natural     : subtle blush + glossy nude lips + skin smoothing
    - glam        : red smoky eye + bold blush + matte red lips
    - bold_lips   : deep berry matte lips + skin smoothing
    - smoky_eye   : black smoky eye + deep red lips

    For custom makeup, use POST /api/makeup/custom with a raw YouCam effects list.
    """
    _validate_image(person_image, "person_image")

    if preset not in MAKEUP_PRESETS:
        raise HTTPException(422, f"preset must be one of: {list(MAKEUP_PRESETS.keys())}")

    person_bytes = await person_image.read()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_makeup_tryon, person_bytes, preset, None
        )
    except Exception as e:
        _err(e)

    result_url = None
    if save_to_minio:
        try:
            result_url = save_result(result["result_image"])
        except Exception:
            pass

    return {
        "result_image_b64": _b64(result["result_image"]),
        "result_url":       result_url,
        "inference_time_s": result["inference_time_s"],
        "mode":             result["mode"],
        "preset":           result.get("preset"),
        "device":           result["device"],
    }


# ─── 👁️ Eye Color Try-On ─────────────────────────────────────────────────────
@app.post("/api/eye-color")
async def eye_color_tryon(
    person_image:  UploadFile = File(..., description="Portrait / face photo"),
    color:         str        = Query(
        default="blue",
        description=(
            "Color preset (blue, green, gray, hazel, violet, amber, ice_blue, honey) "
            "OR a hex color like #2E86AB"
        ),
    ),
    save_to_minio: bool = Query(default=True),
):
    """
    Virtual colored contact lens try-on.

    Color presets: blue · green · gray · hazel · violet · amber · ice_blue · honey
    Or pass any hex color: #2E86AB, #8B6914, etc.
    """
    _validate_image(person_image, "person_image")

    person_bytes = await person_image.read()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_eye_color_tryon, person_bytes, color
        )
    except Exception as e:
        _err(e)

    result_url = None
    if save_to_minio:
        try:
            result_url = save_result(result["result_image"])
        except Exception:
            pass

    return {
        "result_image_b64": _b64(result["result_image"]),
        "result_url":       result_url,
        "inference_time_s": result["inference_time_s"],
        "mode":             result["mode"],
        "color":            result.get("color"),
        "device":           result["device"],
    }


# ─── 🎩 Hat Try-On ───────────────────────────────────────────────────────────
@app.post("/api/hat")
async def hat_tryon(
    person_image: UploadFile = File(..., description="Person photo (head visible)"),
    hat_image:    UploadFile = File(..., description="Hat / cap photo"),
    save_to_minio: bool = Query(default=True),
):
    """Virtual hat / cap try-on powered by YouCam AI."""
    _validate_image(person_image, "person_image")
    _validate_image(hat_image,    "hat_image")

    person_bytes = await person_image.read()
    hat_bytes    = await hat_image.read()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_hat_tryon, person_bytes, hat_bytes
        )
    except Exception as e:
        _err(e)

    result_url = None
    if save_to_minio:
        try:
            result_url = save_result(result["result_image"])
        except Exception:
            pass

    return {
        "result_image_b64": _b64(result["result_image"]),
        "result_url":       result_url,
        "inference_time_s": result["inference_time_s"],
        "mode":             result["mode"],
        "device":           result["device"],
    }


# ─── 👟 Shoes Try-On ─────────────────────────────────────────────────────────
@app.post("/api/shoes")
async def shoes_tryon(
    person_image:  UploadFile = File(..., description="Full-body person photo (feet visible)"),
    shoes_image:   UploadFile = File(..., description="Shoe / footwear photo"),
    save_to_minio: bool = Query(default=True),
):
    """Virtual footwear try-on powered by YouCam AI."""
    _validate_image(person_image, "person_image")
    _validate_image(shoes_image,  "shoes_image")

    person_bytes = await person_image.read()
    shoes_bytes  = await shoes_image.read()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, run_shoes_tryon, person_bytes, shoes_bytes
        )
    except Exception as e:
        _err(e)

    result_url = None
    if save_to_minio:
        try:
            result_url = save_result(result["result_image"])
        except Exception:
            pass

    return {
        "result_image_b64": _b64(result["result_image"]),
        "result_url":       result_url,
        "inference_time_s": result["inference_time_s"],
        "mode":             result["mode"],
        "device":           result["device"],
    }


# ─── 📐 Body Measure (simple rule-based) ─────────────────────────────────────
def _recommend_size(chest_cm: float) -> str:
    if chest_cm < 82: return "XS"
    if chest_cm < 88: return "S"
    if chest_cm < 96: return "M"
    if chest_cm < 104: return "L"
    if chest_cm < 112: return "XL"
    return "XXL"


@app.post("/api/measure")
async def measure(
    person_image: UploadFile = File(...),
    height_cm:    float      = Query(default=165.0, ge=100.0, le=220.0),
):
    """
    Simple body measurement endpoint.
    Returns estimated measurements + size recommendation.
    Note: uses rule-based fallback (no local ML model required).
    """
    _validate_image(person_image, "person_image")
    measurements = {
        "shoulder_cm": 40.0, "chest_cm": 90.0,
        "waist_cm": 75.0, "hip_cm": 96.0,
        "note": "rule-based estimate — upload real measurements for accuracy",
    }
    return {
        **measurements,
        "recommended_size": _recommend_size(measurements["chest_cm"]),
        "height_input_cm":  height_cm,
        "fallback": True,
    }


# ─── DAPR subscriber ─────────────────────────────────────────────────────────
@app.get("/dapr/subscribe")
async def dapr_subscribe():
    return [{"pubsubname": "pubsub", "topic": "images.ready", "route": "/api/process-images"}]


@app.post("/api/process-images")
async def process_images(event: dict):
    """DAPR CloudEvent from Rust image-processor."""
    import httpx
    logger.info(f"📨 DAPR event: {event.get('type')} id={event.get('id')}")

    data        = event.get("data", {})
    request_id  = data.get("request_id", "unknown")
    person_url  = data.get("person_image_url")
    garment_url = data.get("garment_image_url")

    if not person_url or not garment_url:
        return {"status": "skipped", "reason": "missing_urls"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        person_resp  = await client.get(person_url)
        garment_resp = await client.get(garment_url)

    person_bytes  = person_resp.content
    garment_bytes = garment_resp.content

    loop         = asyncio.get_event_loop()
    tryon_result = await loop.run_in_executor(None, run_tryon, person_bytes, garment_bytes)
    result_url   = save_result(tryon_result["result_image"], prefix=f"results/{request_id}/")

    dapr_port = os.getenv("DAPR_HTTP_PORT", "3501")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://localhost:{dapr_port}/v1.0/publish/pubsub/tryon.complete",
                json={
                    "request_id":       request_id,
                    "result_url":       result_url,
                    "inference_time_s": tryon_result["inference_time_s"],
                    "mode":             tryon_result["mode"],
                },
                timeout=5.0,
            )
    except Exception as e:
        logger.warning(f"DAPR publish failed: {e}")

    return {"status": "processed", "request_id": request_id, "result_url": result_url}
