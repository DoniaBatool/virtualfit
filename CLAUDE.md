# Virtual Try-On System — CLAUDE.md

**Last Updated:** 2026-09-03  
**Status:** Week 2 — ML Pipeline (IDM-VTON + SAM2 + MediaPipe)

> 📋 **Is project ka full roadmap:** [`PLAN.md`](./PLAN.md) — har session mein yahan se start karo. PLAN.md mein week-by-week checklist, architecture, data flow, aur all commands hain.

---

## ⚙️ DONIA'S WORKING STYLE — Follow These Rules Always

### 1. After Every Feature → Run Auto-Eval
> Har module/feature complete hone ke baad `/auto-eval` skill ZAROOR run karo. No exceptions.

### 2. Repeated Pattern → Create Skill
> Agar koi kaam 2+ bar repeat ho raha ho, immediately `/skill-creator` use karo.

### 3. README.md Auto-Update — Har Change Ke Baad
> Har significant feature, fix, ya architecture change ke baad README.md update karo.

### 4. UI Stack — Always Use These Together
> UI se related koi bhi kaam — ek component bhi — toh ye SAARI skills load karo pehle:
> `/cinematic-ui` · `/css-scroll-effects` · `/josh-comeau-ui` · `/lets-scroll`
> `/ui-motion-craft` · `/ui-ux-pro-max` · `/shadcn-ui-blocks`

### 5. Always Use Latest Tech Stack
> Before choosing any library: WebSearch first.
> Search: "latest [framework] 2026 best practices"

### 6. Pre-trained Models First
> Virtual Try-On mein: NEVER train from scratch. Use HuggingFace pre-trained models.
> Training = days/weeks. Pre-trained inference = minutes.

---

## What This Project Does

User apni photo upload kare ya webcam use kare, aur virtually kisi bhi garment ko apne body pe try-on kar sake.

- **DensePose** se exact body shape detect hoti hai (shoulder, waist, hip measurements)
- **PyTorch GAN** (VITON-HD style) se cloth warping hoti hai — garment body shape pe fit hota hai
- **TensorFlow** se size recommendation hoti hai (S/M/L/XL + fit %)
- **Qiskit** Grover's algorithm se 1000s garments mein se best match dhundha jaata hai
- **Next.js dashboard** se virtual fitting room experience milta hai

**Industry relevance:** Zara, Amazon, Daraz jaise e-commerce platforms ke liye

---

## Polyglot Architecture — Why Each Language

```
User Browser
     ↓
Next.js Dashboard (:3002)        ← TypeScript — rich UI, SSR, image optimization
     ↓
Go Gateway (:3004)               ← Go Fiber — auth, routing, rate limiting (10k req/s)
     ↓ (DAPR pub/sub)
     ├── Rust Image Processor (:8090)   ← Rust Axum — fast resize/compress before ML
     └── Python ML Pipeline (:8001)     ← Python FastAPI — PyTorch, TensorFlow, DensePose
              ↓
         Databases:
         ├── PostgreSQL (NeonDB)   ← users, wardrobe saves, garment metadata
         ├── Redis                 ← cache processed try-on results
         ├── Qdrant                ← garment vector search (semantic: "red casual shirt")
         └── MinIO                 ← image storage (S3-compatible, local)
```

### Why this split?
- **Rust** for image preprocessing: 10x faster than Python PIL/OpenCV for resize/compress
- **Python** for ML: PyTorch, TensorFlow, DensePose libraries only exist in Python
- **Go** for gateway: handles 10,000+ concurrent requests; Python can't
- **TypeScript/Next.js** for frontend: type safety + built-in image optimization

---

## Service Ports

| Service            | Port  | Language   | Kaam                          |
|--------------------|-------|------------|-------------------------------|
| dashboard          | :3002 | TypeScript | Frontend UI                   |
| gateway            | :3004 | Go         | Auth + routing + rate limit   |
| image-processor    | :8090 | Rust       | Upload handler + preprocessing|
| ml-pipeline        | :8001 | Python     | DensePose + GAN + TF + Qiskit |
| PostgreSQL         | :5433 | -          | Users, wardrobe, garments DB  |
| Redis              | :6379 | -          | Cache                         |
| Qdrant             | :6333 | -          | Vector search                 |
| MinIO              | :9000 | -          | Image file storage            |
| DAPR sidecar       | :3500 | -          | Service mesh                  |
| Prometheus         | :9090 | -          | Metrics                       |
| Grafana            | :3001 | -          | Dashboards                    |

---

## Data Flow (Request Lifecycle)

```
1. User uploads photo + selects garment
   → POST /api/tryon (dashboard → gateway :3004)

2. Gateway validates JWT token + rate limit check
   → Forwards to image-processor :8090

3. Rust image-processor:
   - Resizes photo to 512x512
   - Compresses garment image
   - Stores both in MinIO
   - Publishes event via DAPR: "images.ready"

4. Python ml-pipeline receives DAPR event:
   - DensePose: body UV mapping → measurements
   - GAN cloth_warper: warp garment to body shape
   - TF size_predictor: predict S/M/L + fit score
   - image_composer: blend warped cloth onto person
   - Saves result to MinIO
   - Publishes: "tryon.complete"

5. Gateway receives result → returns to dashboard
6. Dashboard shows split-screen: original | try-on result
```

---

## ML Models Used

| Model                    | Framework       | Purpose                             | Status     |
|--------------------------|-----------------|-------------------------------------|------------|
| IDM-VTON (yisol/IDM-VTON)| diffusers/PyTorch | Virtual try-on (CVPR 2024 SOTA)   | Week 2 ✅  |
| SAM2.1-Hiera-Large       | PyTorch (MPS)  | Person segmentation (background rm) | Week 2 ✅  |
| MediaPipe PoseLandmarker | MediaPipe      | Body measurements (33 landmarks)    | Week 2 ✅  |
| Size Recommender         | TensorFlow     | Predict XS/S/M/L/XL + fit %        | Week 3     |
| Quantum Matcher          | Qiskit         | Grover's O(√N) garment search       | Week 3     |

> **Note:** DensePose/detectron2 dropped — IDM-VTON is SOTA and doesn't need DensePose separately.

---

## Datasets Required

| Dataset         | Size     | Use                        | Source                    |
|-----------------|----------|----------------------------|---------------------------|
| VITON-HD        | ~11K pairs | GAN training             | GitHub: shadow2496/VITON-HD |
| DeepFashion     | 800K+    | Garment catalog            | CUHK mmlab                |
| Body Measurement| ~50K     | TF size model training     | Kaggle                    |

---

## Week-by-Week Plan

### Week 1 — Setup + Infrastructure (Current)
- [x] Project structure created
- [ ] PyTorch + TF installed + MPS verified
- [ ] Docker Compose up (PostgreSQL, Redis, Qdrant, MinIO)
- [ ] DAPR initialized
- [ ] Go gateway skeleton (auth endpoints)
- [ ] Rust image-processor skeleton (upload endpoint)
- [ ] Next.js dashboard skeleton

### Week 2 — DensePose Body Parsing
- [ ] detectron2 + DensePose installed
- [ ] `densepose_body.py` — extract 24 UV maps → measurements (cm)
- [ ] `/api/measure` endpoint — person image → body measurements
- [ ] Test with real photos

### Week 3 — PyTorch GAN (Cloth Warping)
- [ ] VITON-HD dataset downloaded
- [ ] `cloth_warper.py` — GMM + Try-On module architecture
- [ ] Training script (Kaggle/Colab Pro if needed)
- [ ] Inference tested locally on M2 Max via MPS

### Week 4 — TensorFlow Size Recommender + Qiskit
- [ ] `size_predictor.py` — Dense network, body measurements → S/M/L/XL
- [ ] `quantum_matcher.py` — Grover's algorithm for garment search
- [ ] Both integrated into `/api/recommend-size` + `/api/quantum-match`

### Week 5 — Frontend + Full Integration
- [ ] Next.js virtual fitting room UI
- [ ] Split-screen: original photo | try-on result
- [ ] Garment gallery with Qdrant semantic search
- [ ] Size recommendation badge
- [ ] Wardrobe save feature

### Week 6 — Polish + Deploy
- [ ] Stable Diffusion texture enhancement (optional)
- [ ] Hugging Face Spaces deployment (Gradio demo)
- [ ] Portfolio README + demo video

---

## Local Setup Commands

```bash
# 1. Start infrastructure (Docker Desktop must be open first)
cd ~/Documents/virtual_tryon
docker compose up -d

# 2. Python ML pipeline (use uv — NOT pip/venv)
cd services/ml-pipeline
uv sync                                        # install all deps
python scripts/download_models.py --no-vton   # SAM2 + MediaPipe (~930 MB)
uv run uvicorn app.main:app --port 8001 --reload

# 3. Download full IDM-VTON weights (optional, ~9 GB, run once)
python scripts/download_models.py --vton-only

# 4. Rust image processor
cd services/image-processor
cargo run

# 5. Go gateway
cd services/gateway
go run ./cmd/main.go

# 6. Dashboard
cd services/dashboard
pnpm dev

# 7. Landing page preview (requires local server, NOT file://)
cd lets_scroll
python3 -m http.server 8080
# → open http://localhost:8080
```

---

## Environment Variables (.env)

```
# PostgreSQL (NeonDB or local)
DATABASE_URL=postgresql://user:password@localhost:5432/virtual_tryon

# JWT
JWT_SECRET=your_secret_here

# MinIO (image storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=tryon-images

# Qdrant
QDRANT_URL=http://localhost:6333

# Redis
REDIS_URL=redis://localhost:6379

# ML Pipeline
ML_PIPELINE_URL=http://localhost:8001
IMAGE_PROCESSOR_URL=http://localhost:8090
```

---

## M2 Max GPU Notes

- PyTorch MPS backend: `device = torch.device("mps")`
- TensorFlow Metal: `pip install tensorflow-metal`
- DensePose: CPU-only on Mac (detectron2 MPS support limited)
- GAN inference: MPS works well
- GAN training: MPS works but slower than NVIDIA — use Kaggle P100 for full training

### Verify GPU:
```bash
python3 -c "import torch; print('MPS:', torch.backends.mps.is_available())"
```

---

## Key Decisions Log

| Decision | Reason |
|----------|--------|
| Rust for image upload | Python PIL 3x slower for bulk preprocessing |
| Go for gateway | Handles concurrent WebSocket + HTTP connections |
| MinIO instead of S3 | Local dev, S3-compatible API — swap to real S3 for prod |
| DAPR for messaging | Same pattern as PolyFlow — language-agnostic pub/sub |
| Qdrant for search | "Show me similar garments" — vector similarity search |
| NeonDB (PostgreSQL) | Serverless Postgres, free tier, same as PolyFlow |

---

## Error Reference & Lessons Learned

### ✅ docker-compose.yml — `version` attribute warning
**Error:** `WARN: the attribute 'version' is obsolete`  
**Fix:** Remove `version: "3.9"` line from top of docker-compose.yml entirely. Modern Docker Compose doesn't need it.

---

### ✅ PostgreSQL port conflict (5432 already allocated)
**Error:** `Bind for 0.0.0.0:5432 failed: port is already allocated`  
**Cause:** macOS local PostgreSQL (Homebrew) already running on 5432.  
**Fix:** Change docker-compose.yml postgres port to `"5433:5432"` (host:container).  
**Note:** DATABASE_URL in .env must use port 5433.

---

### ✅ numpy version conflict with tensorflow-macos
**Error:** `numpy>=2.0.0` incompatible with `tensorflow-macos>=2.16.0` which requires `numpy<2.0.0`  
**Fix in pyproject.toml:** Change `"numpy>=2.0.0"` → `"numpy>=1.26.0,<2.0.0"`

---

### ✅ hatchling "unable to determine which files to ship"
**Error:** `ValueError: Unable to determine which files to ship inside the wheel`  
**Cause:** Package name is `virtual-tryon-ml` but source folder is `app/` — hatchling can't auto-detect.  
**Fix:** Add to pyproject.toml:
```toml
[tool.hatch.build.targets.wheel]
packages = ["app"]
```

---

### ✅ `tool.uv.dev-dependencies` deprecation warning
**Warning:** `The 'tool.uv.dev-dependencies' field is deprecated`  
**Fix (future):** Change `[tool.uv]` `dev-dependencies` → `[dependency-groups]` `dev` format.  
**Impact:** Just a warning, not blocking. Works fine for now.

---

### ✅ Python SIGABRT crash on macOS ARM64 (uvicorn startup)
**Error:** `EXC_CRASH (SIGABRT)` — `abort() called` — Python quits unexpectedly  
**Cause:** Both `opencv-python` AND `opencv-contrib-python` installed simultaneously — conflict on ARM64.  
**Fix:** Remove `opencv-python` from pyproject.toml, keep only `opencv-contrib-python` (it includes everything). Then `uv sync`.  
**Also:** Remove any MediaPipe pre-warm from FastAPI `lifespan` startup — import at request time only (lazy loading).

---

### ✅ `uv run python` vs `python` — always use uv run
**Error:** `huggingface_hub not installed` even though it was in `uv sync` output  
**Cause:** `python` runs system Python, not the `.venv` created by uv  
**Fix:** Always use `uv run python script.py` or `uv run uvicorn ...` — never bare `python`

---

### 📋 General Rules (Learned)
- **Always use `uv sync`** — never `pip install` in this project
- **Always use `pnpm`** — never `npm` for dashboard
- **Docker Desktop must be open** before any `docker compose` command
- **Landing page needs local server** — `python3 -m http.server 8080`, not `file://` URL
- **IDM-VTON has fallback mode** — composite overlay works without 9 GB download, good for UI dev
- **Models load lazily** — ML service starts fast, models load on first request

---

## Sections

1. What This Project Does
2. Polyglot Architecture
3. Service Ports
4. Data Flow
5. ML Models
6. Datasets
7. Week Plan
8. Setup Commands
9. Environment Variables
10. M2 Max GPU Notes
11. Key Decisions
12. Error Reference
