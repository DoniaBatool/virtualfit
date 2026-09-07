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

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from app.tryon import (
    run_clothes_tryon,
    run_bag_tryon,
    run_makeup_tryon,
    run_eye_color_tryon,
    run_hat_tryon,
    run_shoes_tryon,
    model_status,
    MAKEUP_PRESETS,
    EYE_COLOR_PRESETS,
    set_keys as _set_youcam_keys,
)
from app.storage import save_result, save_wardrobe_image, get_wardrobe_image
from app.database import (
    save_wardrobe_item, get_wardrobe_items, delete_wardrobe_item,
    create_user, get_user_by_email, get_user_by_id,
)
from app.auth import hash_password, verify_password, create_token, extract_token

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
    allow_origins=["*"],
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
    category:      str        = Query(default="upper_body"),
    save_to_minio: bool       = Query(default=True),
    authorization: Optional[str] = Header(default=None),
):
    """Virtual clothing try-on powered by YouCam AI."""
    _validate_image(person_image,  "person_image")
    _validate_image(garment_image, "garment_image")

    person_bytes  = await person_image.read()
    garment_bytes = await garment_image.read()

    user = _current_user(authorization)
    api_key, secret_key = _get_youcam_keys(user) if user else ("", "")

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_with_keys, run_clothes_tryon, api_key, secret_key,
            person_bytes, garment_bytes, category
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


# ─── Auth helpers ─────────────────────────────────────────────────────────────

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "donia1510aptech@gmail.com")


def _current_user(authorization: Optional[str]) -> Optional[dict]:
    """Extract user from JWT Bearer header. Returns None if missing/invalid."""
    payload = extract_token(authorization)
    if not payload:
        return None
    return {"id": int(payload["sub"]), "email": payload["email"], "is_admin": payload.get("is_admin", False)}


def _require_user(authorization: Optional[str]) -> dict:
    user = _current_user(authorization)
    if not user:
        raise HTTPException(401, "Not authenticated — please login")
    return user


def _get_youcam_keys(user: dict) -> tuple[str, str]:
    """Return (api_key, secret_key) — admin uses env, others use their own stored keys."""
    if user["is_admin"]:
        return os.environ.get("YOUCAM_API_KEY", ""), os.environ.get("YOUCAM_SECRET_KEY", "")
    db_user = get_user_by_id(user["id"])
    if db_user:
        return db_user.get("youcam_api_key", ""), db_user.get("youcam_secret_key", "")
    return "", ""


def _run_with_keys(fn, api_key: str, secret_key: str, *args):
    """Wrapper: set thread-local YouCam keys before calling tryon function."""
    _set_youcam_keys(api_key, secret_key)
    try:
        return fn(*args)
    finally:
        _set_youcam_keys("", "")


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str
    youcam_api_key: str = ""
    youcam_secret_key: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    """Register a new user. Admin email uses env YouCam keys; others must supply their own."""
    email = req.email.lower().strip()
    if not email or not req.password:
        raise HTTPException(400, "Email and password required")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    is_admin = (email == ADMIN_EMAIL.lower())

    # Non-admin users must provide YouCam keys
    if not is_admin and (not req.youcam_api_key or not req.youcam_secret_key):
        raise HTTPException(400, "YouCam API key and secret required for non-admin users")

    # Check duplicate
    if get_user_by_email(email):
        raise HTTPException(409, "Account with this email already exists")

    pwd_hash = hash_password(req.password)
    user = create_user(
        email=email,
        password_hash=pwd_hash,
        youcam_api_key=req.youcam_api_key if not is_admin else "",
        youcam_secret_key=req.youcam_secret_key if not is_admin else "",
        is_admin=is_admin,
    )
    if not user:
        raise HTTPException(500, "Failed to create account — database error")

    token = create_token(user["id"], user["email"], user["is_admin"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "is_admin": user["is_admin"]}}


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Login and return JWT token."""
    email = req.email.lower().strip()
    user = get_user_by_email(email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    token = create_token(user["id"], user["email"], user["is_admin"])
    return {"token": token, "user": {"id": user["id"], "email": user["email"], "is_admin": user["is_admin"]}}


@app.get("/api/auth/me")
async def me(authorization: Optional[str] = Header(default=None)):
    """Get current user info from JWT."""
    user = _require_user(authorization)
    return {"id": user["id"], "email": user["email"], "is_admin": user["is_admin"]}


# ─── Image Proxy (serve R2 images) ───────────────────────────────────────────

@app.get("/api/image/{key:path}")
async def get_image(key: str):
    """Proxy wardrobe images from R2 → browser (so no public R2 URL needed)."""
    data = get_wardrobe_image(key)
    if data is None:
        raise HTTPException(404, "Image not found")
    return Response(content=data, media_type="image/jpeg")


# ─── 👗 Wardrobe (NeonDB + R2) ────────────────────────────────────────────────
@app.get("/api/wardrobe")
async def get_wardrobe(authorization: Optional[str] = Header(default=None)):
    """Fetch saved wardrobe items for the authenticated user."""
    user = _require_user(authorization)
    return get_wardrobe_items(str(user["id"]))


@app.delete("/api/wardrobe/{item_id}")
async def delete_wardrobe(item_id: str, authorization: Optional[str] = Header(default=None)):
    """Delete a wardrobe item (authenticated user only)."""
    user = _require_user(authorization)
    ok = delete_wardrobe_item(item_id, str(user["id"]))
    return {"deleted": ok}


@app.post("/api/wardrobe/save")
async def save_to_wardrobe(
    feature: str = Query(...),
    result_image: str = Body(..., media_type="text/plain"),
    authorization: Optional[str] = Header(default=None),
):
    """
    Save a try-on result to wardrobe.
    Uploads image to R2 (not base64 in DB), stores URL in NeonDB.
    """
    user = _require_user(authorization)
    user_id = str(user["id"])

    import base64 as _b64
    # result_image is "data:image/jpeg;base64,..." or raw base64
    try:
        if result_image.startswith("data:"):
            b64_data = result_image.split(",", 1)[1]
        else:
            b64_data = result_image
        image_bytes = _b64.b64decode(b64_data)
    except Exception:
        raise HTTPException(400, "Invalid image data")

    # Upload to R2, get key
    r2_key = save_wardrobe_image(image_bytes)
    if r2_key:
        # Store proxy URL: /api/image/<key>
        railway_base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
        if railway_base:
            result_url = f"https://{railway_base}/api/image/{r2_key}"
        else:
            result_url = f"/api/image/{r2_key}"
    else:
        # Fallback: store base64 directly (graceful degradation)
        result_url = result_image[:500] + "...[truncated]" if len(result_image) > 500 else result_image
        logger.warning("R2 upload failed — storing truncated base64 as fallback")

    saved = save_wardrobe_item(feature=feature, result_url=result_url, user_id=user_id)
    if saved:
        return {"saved": True, "id": saved["id"]}
    return {"saved": False}


# ─── 👜 Bag Try-On ────────────────────────────────────────────────────────────
BAG_STYLES = ["random", "style_parisian_chic", "style_urban_chic",
              "style_mediterranean_chic", "style_art_deco_style"]

@app.post("/api/bag")
async def bag_tryon(
    person_image: UploadFile = File(...),
    bag_image:    UploadFile = File(...),
    gender: str  = Query(default="female"),
    style:  str  = Query(default="random"),
    save_to_minio: bool = Query(default=True),
    authorization: Optional[str] = Header(default=None),
):
    """Virtual handbag / purse try-on."""
    _validate_image(person_image, "person_image")
    _validate_image(bag_image,    "bag_image")
    if style not in BAG_STYLES:
        raise HTTPException(422, f"style must be one of: {BAG_STYLES}")

    person_bytes = await person_image.read()
    bag_bytes    = await bag_image.read()

    user = _current_user(authorization)
    api_key, secret_key = _get_youcam_keys(user) if user else ("", "")

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_with_keys, run_bag_tryon, api_key, secret_key,
            person_bytes, bag_bytes, gender, style
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
    person_image:  UploadFile = File(...),
    preset:        str        = Query(default="natural"),
    save_to_minio: bool       = Query(default=True),
    authorization: Optional[str] = Header(default=None),
):
    """Virtual makeup try-on (presets: natural | glam | bold_lips | smoky_eye)."""
    _validate_image(person_image, "person_image")
    if preset not in MAKEUP_PRESETS:
        raise HTTPException(422, f"preset must be one of: {list(MAKEUP_PRESETS.keys())}")

    person_bytes = await person_image.read()
    user = _current_user(authorization)
    api_key, secret_key = _get_youcam_keys(user) if user else ("", "")

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_with_keys, run_makeup_tryon, api_key, secret_key,
            person_bytes, preset, None
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
    person_image:  UploadFile = File(...),
    color:         str        = Query(default="blue"),
    save_to_minio: bool       = Query(default=True),
    authorization: Optional[str] = Header(default=None),
):
    """Virtual colored contact lens try-on."""
    _validate_image(person_image, "person_image")

    person_bytes = await person_image.read()
    user = _current_user(authorization)
    api_key, secret_key = _get_youcam_keys(user) if user else ("", "")

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_with_keys, run_eye_color_tryon, api_key, secret_key,
            person_bytes, color
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
    person_image: UploadFile = File(...),
    hat_image:    UploadFile = File(...),
    save_to_minio: bool = Query(default=True),
    authorization: Optional[str] = Header(default=None),
):
    """Virtual hat / cap try-on powered by YouCam AI."""
    _validate_image(person_image, "person_image")
    _validate_image(hat_image,    "hat_image")

    person_bytes = await person_image.read()
    hat_bytes    = await hat_image.read()
    user = _current_user(authorization)
    api_key, secret_key = _get_youcam_keys(user) if user else ("", "")

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_with_keys, run_hat_tryon, api_key, secret_key,
            person_bytes, hat_bytes
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
    person_image:  UploadFile = File(...),
    shoes_image:   UploadFile = File(...),
    save_to_minio: bool = Query(default=True),
    authorization: Optional[str] = Header(default=None),
):
    """Virtual footwear try-on powered by YouCam AI."""
    _validate_image(person_image, "person_image")
    _validate_image(shoes_image,  "shoes_image")

    person_bytes = await person_image.read()
    shoes_bytes  = await shoes_image.read()
    user = _current_user(authorization)
    api_key, secret_key = _get_youcam_keys(user) if user else ("", "")

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, _run_with_keys, run_shoes_tryon, api_key, secret_key,
            person_bytes, shoes_bytes
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


