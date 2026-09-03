#!/usr/bin/env python3
"""
VirtualFit Week 2 — One-time model setup script
Run this ONCE after `uv sync` to download all required model checkpoints.

Usage:
    cd services/ml-pipeline
    python scripts/download_models.py

Downloads:
    ① SAM2.1-Hiera-Large   (~900 MB)  → checkpoints/sam2.1_hiera_large.pt
    ② MediaPipe PoseLandmarker Heavy (~29 MB) → checkpoints/pose_landmarker_heavy.task
    ③ IDM-VTON Space code  (~2 MB)   → vendor/IDM-VTON/  (HuggingFace Space clone)
    ④ IDM-VTON weights     (~9 GB)   → vendor/IDM-VTON-weights/  (optional, skip with --no-vton)

Total disk: ~10 GB with IDM-VTON, ~1 GB without.
"""

import argparse
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent   # services/ml-pipeline/
CKPT = ROOT / "checkpoints"
VEND = ROOT / "vendor"

CKPT.mkdir(parents=True, exist_ok=True)
VEND.mkdir(parents=True, exist_ok=True)


def step(msg: str):
    print(f"\n{'─'*60}")
    print(f"  {msg}")
    print('─'*60)


def download_sam2():
    """Download SAM2.1-Hiera-Large checkpoint from HuggingFace."""
    dest = CKPT / "sam2.1_hiera_large.pt"
    if dest.exists():
        print(f"  ✅ SAM2 checkpoint already exists: {dest}")
        return

    step("① Downloading SAM2.1-Hiera-Large (~900 MB from HuggingFace)…")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id="facebook/sam2.1-hiera-large",
            filename="sam2.1_hiera_large.pt",
            local_dir=str(CKPT),
        )
        print(f"  ✅ Saved → {path}")
    except ImportError:
        print("  ❌ huggingface_hub not installed. Run: uv add huggingface-hub")
        sys.exit(1)
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        sys.exit(1)


def download_mediapipe():
    """Download MediaPipe PoseLandmarker Heavy model from Google CDN."""
    dest = CKPT / "pose_landmarker_heavy.task"
    if dest.exists():
        print(f"  ✅ MediaPipe model already exists: {dest}")
        return

    step("② Downloading MediaPipe PoseLandmarker Heavy (~29 MB)…")
    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "pose_landmarker/pose_landmarker_heavy/float16/latest/"
        "pose_landmarker_heavy.task"
    )
    try:
        urllib.request.urlretrieve(url, str(dest))
        print(f"  ✅ Saved → {dest}")
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        sys.exit(1)


def clone_idm_vton_space():
    """Clone the IDM-VTON HuggingFace Space (source code only, ~2 MB)."""
    dest = VEND / "IDM-VTON"
    if dest.exists():
        print(f"  ✅ IDM-VTON Space already cloned: {dest}")
        return

    step("③ Cloning IDM-VTON Space code (~2 MB)…")
    cmd = [
        "git", "clone", "--depth=1",
        "https://huggingface.co/spaces/yisol/IDM-VTON",
        str(dest),
    ]
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ❌ git clone failed:\n{result.stderr}")
        print("  💡 Make sure git-lfs is installed: brew install git-lfs && git lfs install")
        sys.exit(1)
    print(f"  ✅ Cloned → {dest}")


def download_idm_vton_weights():
    """Download IDM-VTON model weights from HuggingFace (~9 GB)."""
    dest = VEND / "IDM-VTON-weights"
    if dest.exists() and any(dest.iterdir()):
        print(f"  ✅ IDM-VTON weights already exist: {dest}")
        return

    step("④ Downloading IDM-VTON weights (~9 GB — this takes a while)…")
    print("  ☕ Go make tea. This will take 10–30 minutes depending on your connection.")

    dest.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "huggingface_hub.cli",
        "download",
        "yisol/IDM-VTON",
        "--local-dir", str(dest),
    ]
    # Alternative: huggingface-cli download yisol/IDM-VTON --local-dir ...
    alt_cmd = [
        "huggingface-cli", "download",
        "yisol/IDM-VTON",
        "--local-dir", str(dest),
    ]
    print(f"  Running: {' '.join(alt_cmd)}")
    result = subprocess.run(alt_cmd, capture_output=False)
    if result.returncode != 0:
        print("  ❌ huggingface-cli download failed.")
        print(f"  💡 Try manually: {' '.join(alt_cmd)}")
        sys.exit(1)
    print(f"  ✅ Saved → {dest}")


def verify():
    """Print status of all downloaded models."""
    print("\n" + "═"*60)
    print("  DOWNLOAD SUMMARY")
    print("═"*60)

    items = [
        (CKPT / "sam2.1_hiera_large.pt",          "SAM2.1 checkpoint"),
        (CKPT / "pose_landmarker_heavy.task",      "MediaPipe PoseLandmarker"),
        (VEND / "IDM-VTON",                        "IDM-VTON Space code"),
        (VEND / "IDM-VTON-weights" / "unet",       "IDM-VTON weights (unet)"),
    ]
    for path, name in items:
        size_str = ""
        if path.exists():
            if path.is_file():
                size_mb = path.stat().st_size / 1_048_576
                size_str = f" ({size_mb:.0f} MB)"
            status = "✅"
        else:
            status = "❌  (not downloaded)"
        print(f"  {status}  {name}{size_str}")

    print()
    print("  Next steps:")
    print("  1. cd services/ml-pipeline && uv run uvicorn app.main:app --port 8001")
    print("  2. Test: curl http://localhost:8001/health")
    print("  3. Try-on: POST http://localhost:8001/api/tryon")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download VirtualFit Week 2 models")
    parser.add_argument("--no-vton",    action="store_true", help="Skip IDM-VTON download (~9 GB)")
    parser.add_argument("--vton-only",  action="store_true", help="Download only IDM-VTON weights")
    parser.add_argument("--verify",     action="store_true", help="Just show download status")
    args = parser.parse_args()

    if args.verify:
        verify()
        sys.exit(0)

    if args.vton_only:
        clone_idm_vton_space()
        download_idm_vton_weights()
        verify()
        sys.exit(0)

    download_sam2()
    download_mediapipe()
    clone_idm_vton_space()

    if not args.no_vton:
        download_idm_vton_weights()
    else:
        print("\n  ⏭️  IDM-VTON weights skipped (--no-vton). Fallback overlay mode will be used.")

    verify()
