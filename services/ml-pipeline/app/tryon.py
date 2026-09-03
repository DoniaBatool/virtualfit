"""
Week 2 — IDM-VTON Virtual Try-On Inference
Uses yisol/IDM-VTON (CVPR 2024) — best open-source VTON model.

Two-path architecture:
  ① Local: Load from vendor/IDM-VTON/ (after git clone — ~6 GB download)
  ② Fallback: Composite overlay (PIL-based, instant, no download needed)

Setup command (run once, ~12 GB total):
    cd services/ml-pipeline
    git clone https://huggingface.co/spaces/yisol/IDM-VTON vendor/IDM-VTON
    # OR for model weights only:
    huggingface-cli download yisol/IDM-VTON --local-dir vendor/IDM-VTON-weights

M2 Max GPU: MPS backend auto-detected (float16 supported from PyTorch 2.4+).
"""

import io
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────
_ML_DIR      = Path(__file__).parent.parent
_VENDOR_DIR  = _ML_DIR / "vendor" / "IDM-VTON"
_WEIGHTS_DIR = _ML_DIR / "vendor" / "IDM-VTON-weights"

# ─── Lazy state ───────────────────────────────────────────────────────────────
_pipe   = None
_device = None
_mode   = None   # "local" | "fallback"


# ─── Device ───────────────────────────────────────────────────────────────────
def _get_device() -> str:
    import torch
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# ─── Path A: Local IDM-VTON via vendored Space code ──────────────────────────
def _try_load_local() -> bool:
    """Add vendor/IDM-VTON to sys.path and load the pipeline."""
    global _pipe, _device, _mode

    if not _VENDOR_DIR.exists() and not _WEIGHTS_DIR.exists():
        return False

    source_dir = _VENDOR_DIR if _VENDOR_DIR.exists() else _WEIGHTS_DIR

    # Inject IDM-VTON source into Python path
    src_str = str(source_dir)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)

    try:
        import torch
        from diffusers import DDPMScheduler, AutoencoderKL
        from transformers import CLIPTextModel, CLIPTokenizer

        # IDM-VTON's own pipeline classes (inside the Space repo)
        from src.tryon_pipeline import StableDiffusionXLInpaintPipeline as TryonPipeline
        from src.unet_hacked_tryon import UNet2DConditionModel
        from src.unet_hacked_garmnet import UNet2DConditionModel as GarmentUNet
        from preprocess.humanparsing.run_parsing import Parsing
        from preprocess.openpose.run_openpose import OpenPose

        weights = str(_WEIGHTS_DIR) if _WEIGHTS_DIR.exists() else str(source_dir)

        _device = _get_device()
        dtype   = torch.float16 if _device != "cpu" else torch.float32

        logger.info(f"🔄 Loading IDM-VTON on {_device} (float16={_device != 'cpu'})…")

        unet = UNet2DConditionModel.from_pretrained(
            weights, subfolder="unet", torch_dtype=dtype
        )
        unet_encoder = GarmentUNet.from_pretrained(
            weights, subfolder="unet_encoder", torch_dtype=dtype
        )

        vae = AutoencoderKL.from_pretrained(
            "stabilityai/sd-vae-ft-mse", torch_dtype=dtype
        )

        scheduler = DDPMScheduler.from_pretrained(weights, subfolder="scheduler")
        text_encoder    = CLIPTextModel.from_pretrained(weights, subfolder="text_encoder",    torch_dtype=dtype)
        text_encoder_2  = CLIPTextModel.from_pretrained(weights, subfolder="text_encoder_2",  torch_dtype=dtype)
        tokenizer       = CLIPTokenizer.from_pretrained(weights, subfolder="tokenizer")
        tokenizer_2     = CLIPTokenizer.from_pretrained(weights, subfolder="tokenizer_2")

        _pipe = TryonPipeline.from_pretrained(
            weights,
            unet=unet,
            unet_encoder=unet_encoder,
            vae=vae,
            text_encoder=text_encoder.to(_device),
            text_encoder_2=text_encoder_2.to(_device),
            tokenizer=tokenizer,
            tokenizer_2=tokenizer_2,
            scheduler=scheduler,
            torch_dtype=dtype,
        ).to(_device)

        if _device == "mps":
            _pipe.enable_attention_slicing()   # save VRAM on Apple Silicon

        _mode = "local"
        logger.info("✅ IDM-VTON local model ready")
        return True

    except ImportError as e:
        logger.warning(f"IDM-VTON vendor import failed (src not found): {e}")
        return False
    except Exception as e:
        logger.warning(f"IDM-VTON local load failed: {e}")
        return False


# ─── Load on first call ───────────────────────────────────────────────────────
def _ensure_loaded():
    global _mode
    if _mode is not None:
        return

    if _try_load_local():
        return

    logger.warning(
        "⚠️  IDM-VTON model not found. Using composite overlay fallback.\n"
        "   To enable full inference, run:\n"
        "   cd services/ml-pipeline\n"
        "   git clone https://huggingface.co/spaces/yisol/IDM-VTON vendor/IDM-VTON\n"
        "   huggingface-cli download yisol/IDM-VTON --local-dir vendor/IDM-VTON-weights"
    )
    _mode = "fallback"


# ─── Public API ───────────────────────────────────────────────────────────────
def run_tryon(
    person_bytes: bytes,
    garment_bytes: bytes,
    person_mask_bytes: Optional[bytes] = None,
    num_inference_steps: int = 30,
    guidance_scale: float = 2.0,
    seed: int = 42,
) -> dict:
    """
    Virtual try-on: drape a garment onto a person photo.

    Args:
        person_bytes:         JPEG/PNG of person (any size, auto-resized to 1024×1024)
        garment_bytes:        JPEG/PNG of garment on white background
        person_mask_bytes:    Optional RGBA mask from SAM2 (used for inpainting region)
        num_inference_steps:  Diffusion steps — 30 fast / 50 quality
        guidance_scale:       CFG scale (2.0 recommended for VTON)
        seed:                 Reproducibility seed

    Returns:
        {
            "result_image":     bytes,   # JPEG bytes of try-on result
            "inference_time_s": float,
            "mode":             str,     # "local" | "fallback"
            "device":           str,
        }
    """
    _ensure_loaded()

    person  = Image.open(io.BytesIO(person_bytes)).convert("RGB")
    garment = Image.open(io.BytesIO(garment_bytes)).convert("RGB")

    if _mode == "local":
        return _infer_local(person, garment, person_mask_bytes, num_inference_steps, guidance_scale, seed)
    else:
        return _infer_fallback(person, garment, person_mask_bytes)


# ─── Path A: Full IDM-VTON inference ─────────────────────────────────────────
def _infer_local(
    person: Image.Image,
    garment: Image.Image,
    mask_bytes: Optional[bytes],
    steps: int,
    cfg: float,
    seed: int,
) -> dict:
    import torch

    # IDM-VTON target size
    TARGET = (768, 1024)   # (width, height) matching their training resolution

    person_r  = person.resize(TARGET, Image.LANCZOS)
    garment_r = garment.resize(TARGET, Image.LANCZOS)

    # Build inpaint mask — upper-body region if SAM2 mask not provided
    if mask_bytes:
        mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L").resize(TARGET)
        # IDM-VTON wants the garment region masked (white = repaint)
        mask_np  = np.array(mask_img)
    else:
        # Default: mask the torso band (shoulder to hip, full width)
        W, H    = TARGET
        mask_np = np.zeros((H, W), dtype=np.uint8)
        mask_np[int(H * 0.12): int(H * 0.75), :] = 255

    mask_img = Image.fromarray(mask_np, mode="L")

    prompt = (
        "a photo of a person wearing a garment, "
        "high quality, natural lighting, clean background"
    )
    neg_prompt = (
        "monochrome, lowres, bad anatomy, worst quality, low quality, "
        "mutated hands, bad hands, bad proportions"
    )

    generator = torch.Generator(_device).manual_seed(seed)

    t0 = time.time()
    with torch.inference_mode():
        result = _pipe(
            prompt=prompt,
            negative_prompt=neg_prompt,
            image=person_r,
            mask_image=mask_img,
            ip_adapter_image=garment_r,
            num_inference_steps=steps,
            guidance_scale=cfg,
            generator=generator,
            width=TARGET[0],
            height=TARGET[1],
        ).images[0]
    elapsed = time.time() - t0

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=92)

    return {
        "result_image":     buf.getvalue(),
        "inference_time_s": round(elapsed, 2),
        "mode":             "local",
        "device":           _device,
    }


# ─── Path B: Composite overlay fallback ───────────────────────────────────────
def _infer_fallback(
    person: Image.Image,
    garment: Image.Image,
    mask_bytes: Optional[bytes],
) -> dict:
    """
    Fast PIL-based garment overlay.
    Not a real try-on, but useful for UI development before the model downloads.
    """
    t0 = time.time()

    W, H = person.size

    # Resize garment to cover torso (roughly 60% width, 55% height)
    g_w = int(W * 0.60)
    g_h = int(H * 0.55)
    garment_r = garment.resize((g_w, g_h), Image.LANCZOS)

    # Position: centred horizontally, starting at ~15% from top
    x = (W - g_w) // 2
    y = int(H * 0.15)

    # Create alpha mask: soft oval to blend garment onto body
    alpha = Image.new("L", (g_w, g_h), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(alpha)
    margin = int(g_w * 0.10)
    draw.ellipse([margin, margin, g_w - margin, g_h - margin], fill=220)
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=g_w * 0.08))

    garment_rgba = garment_r.convert("RGBA")
    garment_rgba.putalpha(alpha)

    result = person.convert("RGBA")
    result.paste(garment_rgba, (x, y), garment_rgba)
    result = result.convert("RGB")

    # Subtle warm grade
    result_np = np.array(result, dtype=np.float32)
    result_np[:, :, 0] = np.clip(result_np[:, :, 0] * 1.03, 0, 255)
    result = Image.fromarray(result_np.astype(np.uint8))

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=90)

    return {
        "result_image":     buf.getvalue(),
        "inference_time_s": round(time.time() - t0, 3),
        "mode":             "fallback",
        "device":           "cpu",
        "note":             (
            "Composite overlay — download IDM-VTON for real inference:\n"
            "  cd services/ml-pipeline\n"
            "  git clone https://huggingface.co/spaces/yisol/IDM-VTON vendor/IDM-VTON"
        ),
    }


# ─── Model status ─────────────────────────────────────────────────────────────
def model_status() -> dict:
    """Report which inference path is active."""
    return {
        "mode":          _mode or "not_loaded",
        "vendor_exists": _VENDOR_DIR.exists(),
        "weights_exist": _WEIGHTS_DIR.exists(),
        "device":        _device or "unknown",
        "setup_cmd": (
            "cd services/ml-pipeline && "
            "git clone https://huggingface.co/spaces/yisol/IDM-VTON vendor/IDM-VTON && "
            "huggingface-cli download yisol/IDM-VTON --local-dir vendor/IDM-VTON-weights"
        ) if _mode == "fallback" else None,
    }
