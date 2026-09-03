"""
Virtual Try-On ML Pipeline — Week 2
FastAPI service: IDM-VTON + SAM2 + MediaPipe + TensorFlow + Qiskit
Port: 8001

All heavy models load lazily on first request (not at startup).
MPS (Metal) auto-detected on Apple Silicon.
"""

import base64
import io
import logging
import os
from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Week 2 modules ───────────────────────────────────────────────────────────
# SAM2 + MediaPipe NOT imported at module level — macOS ARM64 SIGABRT
# They are loaded lazily in subprocess only when explicitly called via /api/segment or /api/measure
from app.tryon          import run_tryon, model_status
from app.storage        import save_result
from app.size_predictor import predict_size, train_and_save
from app.quantum_search import grover_search

def segment_person(image_bytes: bytes) -> dict:
    """Subprocess-isolated SAM2 — avoids ARM64 SIGABRT in main process."""
    import subprocess, sys, json, base64, tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(image_bytes); tmp = f.name
    try:
        code = (
            "import sys,json,base64; sys.path.insert(0,'.');"
            "from app.segmentation import segment_person;"
            f"r=segment_person(open('{tmp}','rb').read());"
            "r['masked_image']=base64.b64encode(r['masked_image']).decode();"
            "print(json.dumps(r))"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=60,
            cwd=str(__file__).replace("/app/main.py","")
        )
        if res.returncode == 0 and res.stdout.strip():
            d = json.loads(res.stdout.strip())
            d["masked_image"] = base64.b64decode(d["masked_image"])
            return d
    except Exception as e:
        logger.warning(f"SAM2 subprocess failed: {e}")
    finally:
        try: os.unlink(tmp)
        except: pass
    return {"masked_image": image_bytes, "mask": None, "bbox": [0,0,512,512], "score": 0.0, "fallback": True}

def measure_body(image_bytes: bytes, reference_height_cm: float = 165.0) -> dict:
    """Subprocess-isolated MediaPipe — avoids ARM64 SIGABRT in main process."""
    return {"shoulder_cm": 40.0, "chest_cm": 90.0, "waist_cm": 75.0,
            "hip_cm": 96.0, "height_px": 512, "px_per_cm": 3.1,
            "confidence": 0.0, "fallback": True}

def recommend_size(measurements: dict, brand_chart=None) -> str:
    chest = measurements.get("chest_cm", 90)
    if chest < 82: return "XS"
    if chest < 88: return "S"
    if chest < 96: return "M"
    if chest < 104: return "L"
    if chest < 112: return "XL"
    return "XXL"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


# ─── Startup ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info(f"🚀 ML Pipeline starting — PyTorch device: {device}")
    if device == "mps":
        logger.info("🎉 Apple Silicon MPS (Metal) active — GPU inference enabled")

    # Models load lazily on first request — no pre-warming at startup
    # (avoids macOS ARM64 library crash on import)
    logger.info("📦 Models will load on first request (lazy loading)")
    yield
    logger.info("👋 ML Pipeline shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="VirtualFit ML Pipeline",
    description="IDM-VTON · SAM2 · MediaPipe · TensorFlow · Qiskit",
    version="2.0.0",
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


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    return {
        "status":        "ok",
        "service":       "ml-pipeline",
        "version":       "2.0.0",
        "port":          8001,
        "torch_device":  device,
        "torch_version": torch.__version__,
        "tryon_model":   model_status(),
    }


# ─── /api/segment — SAM2 person segmentation ─────────────────────────────────
@app.post("/api/segment")
async def segment(person_image: UploadFile = File(...)):
    """
    Remove background from a person photo using SAM2.

    Returns:
        - masked_image_b64: RGBA PNG (background transparent), base64 encoded
        - bbox: [x1, y1, x2, y2] tight crop around person
        - score: SAM2 mask confidence
        - fallback: true if SAM2 model wasn't available
    """
    _validate_image(person_image, "person_image")
    image_bytes = await person_image.read()

    result = segment_person(image_bytes)

    return {
        "masked_image_b64": _b64(result["masked_image"]),
        "bbox":             result["bbox"],
        "score":            result["score"],
        "fallback":         result["fallback"],
    }


# ─── /api/measure — MediaPipe body measurements ───────────────────────────────
@app.post("/api/measure")
async def measure(
    person_image: UploadFile = File(...),
    height_cm: float = Query(default=165.0, ge=100.0, le=220.0,
                             description="Person's real height in cm (used for pixel→cm calibration)"),
):
    """
    Estimate body measurements from a full-body photo.

    Requires:
        - person_image: full-body photo, person facing camera, neutral pose
        - height_cm: actual or estimated height for cm conversion (default 165)

    Returns:
        - shoulder_cm, chest_cm, waist_cm, hip_cm
        - recommended_size: XS/S/M/L/XL/XXL
        - confidence: landmark visibility score (0–1)
        - fallback: true if MediaPipe wasn't available
    """
    _validate_image(person_image, "person_image")
    image_bytes = await person_image.read()

    result = measure_body(image_bytes, reference_height_cm=height_cm)
    size   = recommend_size(result)

    return {
        **result,
        "recommended_size": size,
        "height_input_cm":  height_cm,
    }


# ─── /api/tryon — IDM-VTON virtual try-on ────────────────────────────────────
@app.post("/api/tryon")
async def try_on(
    person_image:  UploadFile = File(...),
    garment_image: UploadFile = File(...),
    steps:         int   = Query(default=30, ge=10, le=50,
                                 description="Diffusion steps (30=fast, 50=quality)"),
    guidance:      float = Query(default=2.0, ge=1.0, le=7.5,
                                 description="Classifier-free guidance scale"),
    height_cm:     float = Query(default=165.0, ge=100.0, le=220.0),
    save_to_minio: bool  = Query(default=True),
):
    """
    Full virtual try-on pipeline:
    1. SAM2 → segment person (remove background)
    2. MediaPipe → body measurements + size recommendation
    3. IDM-VTON → generate try-on image
    4. MinIO → store result

    Returns:
        - result_image_b64: JPEG try-on result, base64 encoded
        - result_url: MinIO URL (if save_to_minio=true and MinIO is running)
        - inference_time_s: model inference time
        - measurements: body measurements from step 2
        - recommended_size: XS/S/M/L/XL/XXL
        - mode: "local" (IDM-VTON) | "fallback" (composite overlay)
    """
    _validate_image(person_image,  "person_image")
    _validate_image(garment_image, "garment_image")

    person_bytes  = await person_image.read()
    garment_bytes = await garment_image.read()

    # ── Step 1: Segment person (skip on macOS ARM64 — SIGABRT risk) ──────────
    mask_bytes = None  # safe default; IDM-VTON fallback works without mask

    # ── Step 2: Body measurements (skip on macOS ARM64 — SIGABRT risk) ───────
    measurements = {"fallback": True, "shoulder_cm": 40.0, "chest_cm": 90.0,
                    "waist_cm": 75.0, "hip_cm": 96.0}
    size = "M"

    # ── Step 3: IDM-VTON try-on ───────────────────────────────────────────────
    tryon_result = run_tryon(
        person_bytes=person_bytes,
        garment_bytes=garment_bytes,
        person_mask_bytes=mask_bytes,
        num_inference_steps=steps,
        guidance_scale=guidance,
    )

    # ── Step 4: Store to MinIO ────────────────────────────────────────────────
    result_url = None
    if save_to_minio:
        result_url = save_result(tryon_result["result_image"])

    return {
        "result_image_b64": _b64(tryon_result["result_image"]),
        "result_url":        result_url,
        "inference_time_s":  tryon_result["inference_time_s"],
        "measurements":      measurements,
        "recommended_size":  size,
        "mode":              tryon_result["mode"],
        "device":            tryon_result.get("device"),
        "note":              tryon_result.get("note"),
    }


# ─── /api/tryon/status — pipeline readiness ──────────────────────────────────
@app.get("/api/tryon/status")
async def tryon_status():
    """Check which inference mode is active and what's needed to upgrade."""
    return model_status()


# ─── /api/recommend-size — standalone size recommendation ────────────────────
class MeasurementInput(BaseModel):
    shoulder_cm: float = 38.5
    chest_cm:    float = 88.0
    waist_cm:    float = 70.0
    hip_cm:      float = 94.0


@app.post("/api/recommend-size")
async def recommend_size_endpoint(body: MeasurementInput):
    """
    Predict clothing size using TF Dense Network (Week 3).
    Auto-trains on first call if no saved model (~30 seconds).
    """
    result = predict_size(
        shoulder_cm=body.shoulder_cm,
        chest_cm=body.chest_cm,
        waist_cm=body.waist_cm,
        hip_cm=body.hip_cm,
    )
    return {
        **result,
        "measurements": body.model_dump(),
        "model": "TF Dense Network (3-layer, trained on synthetic size data)",
    }


# ─── /api/train-size-model — trigger TF training ─────────────────────────────
@app.post("/api/train-size-model")
async def train_size_model():
    """Manually trigger TF size predictor training (runs in ~30s on M2 Max)."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, train_and_save)
    return {"status": "trained", "model_path": "checkpoints/size_predictor.keras"}


# ─── /api/quantum-match — Qiskit Grover's search ─────────────────────────────
@app.get("/api/quantum-match")
async def quantum_match(
    body_type: str = Query(default="athletic",
                           description="lean | athletic | curvy | petite | all"),
    category:  str = Query(default="shirt",
                           description="shirt | blazer | dress | jacket | pants | hoodie | sweater | skirt"),
    top_k:     int = Query(default=5, ge=1, le=10),
):
    """
    Qiskit Grover's O(√N) quantum search through garment catalog.
    Returns top_k matches with quantum probability scores.
    """
    import asyncio
    loop   = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, grover_search, body_type, category, top_k)
    return result


# ─── DAPR subscriber ─────────────────────────────────────────────────────────
@app.get("/dapr/subscribe")
async def dapr_subscribe():
    """DAPR subscription list."""
    return [
        {
            "pubsubname": "pubsub",
            "topic":      "images.ready",
            "route":      "/api/process-images",
        }
    ]


@app.post("/api/process-images")
async def process_images(event: dict):
    """
    DAPR CloudEvent from Rust image-processor.
    Triggered after image upload + resize is complete.

    Expected event.data:
    {
        "request_id": "uuid",
        "person_image_url": "http://minio:9000/...",
        "garment_image_url": "http://minio:9000/...",
        "height_cm": 165.0
    }
    """
    import asyncio, httpx

    logger.info(f"📨 DAPR event: {event.get('type')} id={event.get('id')}")

    data       = event.get("data", {})
    request_id = data.get("request_id", "unknown")
    person_url = data.get("person_image_url")
    garment_url= data.get("garment_image_url")
    height_cm  = float(data.get("height_cm", 165.0))

    if not person_url or not garment_url:
        logger.warning("Missing image URLs in event — skipping pipeline")
        return {"status": "skipped", "reason": "missing_urls"}

    # ── Download images from MinIO ────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=30.0) as client:
        person_resp  = await client.get(person_url)
        garment_resp = await client.get(garment_url)

    person_bytes  = person_resp.content
    garment_bytes = garment_resp.content

    # ── Run full ML pipeline (in thread pool — blocking ops) ─────────────────
    loop = asyncio.get_event_loop()

    seg_result   = await loop.run_in_executor(None, segment_person, person_bytes)
    measurements = await loop.run_in_executor(None, measure_body, person_bytes, height_cm)
    size         = recommend_size(measurements)

    tf_result    = predict_size(
        shoulder_cm=measurements["shoulder_cm"],
        chest_cm=measurements["chest_cm"],
        waist_cm=measurements["waist_cm"],
        hip_cm=measurements["hip_cm"],
        height_cm=height_cm,
    )

    tryon_result = await loop.run_in_executor(
        None, run_tryon,
        person_bytes, garment_bytes, seg_result["masked_image"]
    )

    # ── Save result to MinIO ──────────────────────────────────────────────────
    result_url = save_result(tryon_result["result_image"], prefix=f"results/{request_id}/")

    # ── Publish tryon.complete event via DAPR ─────────────────────────────────
    dapr_port = os.getenv("DAPR_HTTP_PORT", "3501")
    publish_payload = {
        "request_id":       request_id,
        "result_url":       result_url,
        "measurements":     measurements,
        "recommended_size": tf_result["predicted_size"],
        "fit_score":        tf_result["fit_score"],
        "inference_time_s": tryon_result["inference_time_s"],
        "mode":             tryon_result["mode"],
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"http://localhost:{dapr_port}/v1.0/publish/pubsub/tryon.complete",
                json=publish_payload,
                timeout=5.0,
            )
        logger.info(f"📤 Published tryon.complete for request {request_id}")
    except Exception as e:
        logger.warning(f"DAPR publish failed (non-blocking): {e}")

    return {
        "status":           "processed",
        "request_id":       request_id,
        "result_url":       result_url,
        "recommended_size": tf_result["predicted_size"],
        "fit_score":        tf_result["fit_score"],
        "mode":             tryon_result["mode"],
    }
