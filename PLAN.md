# Virtual Try-On System — Project Plan (2026)

**Last Updated:** 2026-08-22  
**Approach:** Polyglot Engineering — best tool for each job  
**Difficulty:** ⭐⭐⭐⭐ Advanced  
**Estimated Time:** 5–6 weeks

---

## What We Are Building

User apni photo upload kare ya webcam use kare, aur virtually kisi bhi garment ko apne body pe try-on kar sake. E-commerce ke liye (Zara, Amazon, Daraz level) production-ready system.

---

## Why Old Plan Was Replaced

| Old Plan | Problem | New Plan (2026) |
|----------|---------|-----------------|
| Train VITON-HD GAN from scratch | 2021 model, takes weeks, worse results | IDM-VTON pre-trained (best open-source 2026) |
| DensePose (detectron2) | Complex install, Mac pe issues | SAM2 + MediaPipe Pose Landmarker |
| pip for Python | Slow, no lock file | `uv` (10x faster, lock file, virtual env) |
| npm for Node | Slow installs | `pnpm` (3x faster, disk efficient) |
| VITON-HD architecture | Outdated | IDM-VTON (diffusion-based, realistic) |

---

## Polyglot Tech Stack (2026 Verified)

| Kaam | Language/Tool | Version | Kyun |
|------|--------------|---------|------|
| **Image upload + preprocessing** | Rust (Axum) | 0.8+ | 10x faster than Python PIL; zero-copy memory |
| **Try-On ML (main model)** | Python + diffusers | PyTorch 2.5+ | IDM-VTON/CatVTON sirf Python mein |
| **Body measurement** | Python + MediaPipe | 0.10+ | Easy Mac install, no DensePose hassle |
| **Size prediction** | Python + TensorFlow | 2.16+ | Simple Dense network, fast to train |
| **Quantum garment search** | Python + Qiskit | 1.x | Grover's O(√N) — unique portfolio piece |
| **API Gateway** | Go + Fiber v3 | Go 1.25+ | 10k+ req/sec; auth + rate limiting |
| **Frontend** | TypeScript + Next.js | 15 (App Router) | SSR + image optimization + type safety |
| **Users + wardrobe DB** | PostgreSQL (NeonDB) | 16 | Relational data, free serverless tier |
| **Try-on result cache** | Redis | 7.x | Same garment + body → cached result |
| **Garment vector search** | Qdrant | latest | Semantic search: "red casual shirt" |
| **Image file storage** | MinIO (local) → R2 (prod) | - | S3-compatible; R2 = cheaper than AWS S3 |
| **Service communication** | DAPR | 1.14+ | Best polyglot service mesh in 2026 |
| **Python pkg manager** | uv | latest | 10x faster than pip, proper lock file |
| **Node pkg manager** | pnpm | 9+ | 3x faster than npm |
| **Monitoring** | Prometheus + Grafana | latest | Same as PolyFlow pattern |

### ML Models (Pre-trained — No Training Needed)

| Model | Use | HuggingFace | Quality |
|-------|-----|-------------|---------|
| **IDM-VTON** | Main try-on (best quality) | `yisol/IDM-VTON` | ⭐⭐⭐⭐⭐ |
| **CatVTON** | Fast alternative (lighter on RAM) | `zhengchong/CatVTON` | ⭐⭐⭐⭐ |
| **SAM2** | Body segmentation | `facebook/sam2` | ⭐⭐⭐⭐⭐ |
| **MediaPipe Pose** | Body measurements | Google (pip install) | ⭐⭐⭐⭐ |
| Custom TF Size Model | Size prediction | Train locally (~1hr) | ⭐⭐⭐ |

---

## Architecture

```
User Browser
     ↓ HTTPS
┌─────────────────────┐
│  Next.js 15 (:3002) │  TypeScript — fitting room UI
│  App Router + SSR   │
└─────────┬───────────┘
          ↓ REST/WebSocket
┌─────────────────────┐
│  Go Gateway (:3004) │  Auth (JWT) + Rate Limit + Routing
│  Fiber v3           │
└──────┬──────────────┘
       ↓ DAPR pub/sub (Redpanda/Kafka)
   ┌───┴────────────────────────────────┐
   ↓                                    ↓
┌──────────────────────┐    ┌───────────────────────────┐
│ Rust Image Processor │    │  Python ML Pipeline       │
│ Axum (:8090)        │    │  FastAPI (:8001)           │
│ - Upload handling    │    │  - IDM-VTON try-on        │
│ - Resize 512x512    │    │  - SAM2 body parse        │
│ - Format convert     │    │  - MediaPipe measurements │
│ → MinIO storage      │    │  - TF size prediction     │
└──────────────────────┘    │  - Qiskit garment search  │
                            └───────────────────────────┘
                                         ↓
                            ┌───────────────────────────┐
                            │  Databases                │
                            │  PostgreSQL — users/data  │
                            │  Redis — cache            │
                            │  Qdrant — vector search   │
                            │  MinIO — images           │
                            └───────────────────────────┘
```

---

## Data Flow (One Try-On Request)

```
1. User uploads photo + selects garment
   → POST /api/tryon (Next.js → Go Gateway :3004)

2. Go Gateway:
   - JWT token verify
   - Rate limit check (Redis)
   - Forward to Rust image-processor

3. Rust Image Processor (:8090):
   - Photo resize → 512×512 (for IDM-VTON)
   - Garment image resize → 768×1024
   - Both saved to MinIO
   - DAPR publish: topic "images.ready" with MinIO paths

4. Python ML Pipeline receives DAPR event:
   a. SAM2 → segment person from background
   b. MediaPipe → extract body measurements (shoulder, waist, hip in cm)
   c. IDM-VTON → warp garment onto body (pre-trained, ~15 sec on M2 Max)
   d. TF Size Model → predict S/M/L/XL + fit% from measurements
   e. Result image saved to MinIO
   f. DAPR publish: "tryon.complete" with result URL

5. Go Gateway receives result → returns JSON to frontend
6. Next.js shows split-screen: original photo | try-on result
7. Result cached in Redis (garment_id + body_hash → result URL, 24hr TTL)
```

---

## Week-by-Week Build Plan

### ✅ Week 1 — Foundation (Current)
- [x] Project folder structure
- [x] CLAUDE.md + PLAN.md
- [x] docker-compose.yml (PostgreSQL, Redis, Qdrant, MinIO, Redpanda, Prometheus, Grafana)
- [x] DAPR components config
- [x] Database migrations (users, garments, tryon_results, wardrobe)
- [ ] PyTorch + TF install + MPS verify (`python3 -c "import torch; print(torch.backends.mps.is_available())")`)
- [ ] Go gateway skeleton (health check + JWT auth endpoints)
- [ ] Rust image-processor skeleton (upload + resize endpoint)
- [ ] Next.js dashboard skeleton (login + register pages)
- [ ] docker compose up → all containers healthy

### 📋 Week 2 — ML Pipeline Core
- [ ] IDM-VTON setup from HuggingFace (`yisol/IDM-VTON`)
- [ ] SAM2 body segmentation working on a sample photo
- [ ] MediaPipe Pose Landmarker → extract shoulder/waist/hip measurements
- [ ] FastAPI `/api/tryon` endpoint (person image + garment → result image)
- [ ] FastAPI `/api/measure` endpoint (person image → measurements JSON)
- [ ] Test on real photo — verify try-on output quality

### 📋 Week 3 — Size Prediction + Quantum Search
- [ ] TensorFlow size predictor model (Dense network)
  - Collect/generate body measurement dataset (~500 samples)
  - Train locally on M2 Max (~1 hour)
  - `/api/recommend-size` endpoint
- [ ] Qiskit quantum garment matcher
  - Grover's algorithm implementation
  - Garment catalog as quantum states
  - `/api/quantum-match` endpoint returns top 5 garments
- [ ] Qdrant garment vectors (semantic search: "red casual shirt")
- [ ] All 4 endpoints tested and working

### 📋 Week 4 — Rust + Go + DAPR Integration
- [ ] Rust image-processor complete (Axum + MinIO upload)
- [ ] DAPR pub/sub wiring: Rust → Python pipeline
- [ ] Go gateway complete:
  - JWT register/login (PostgreSQL + NeonDB)
  - Rate limiting (Redis)
  - Route all endpoints through gateway
- [ ] End-to-end test: browser upload → Rust → DAPR → Python → result back to browser

### 📋 Week 5 — Next.js Frontend (Cinematic UI)
- [ ] Load all 7 UI skills (project-workflow Rule 4):
  `/cinematic-ui` · `/css-scroll-effects` · `/josh-comeau-ui` · `/lets-scroll`
  `/ui-motion-craft` · `/ui-ux-pro-max` · `/shadcn-ui-blocks`
- [ ] `/lets-scroll` landing page (scroll-scrubbed camera fly-through)
  - Write 4 scene prompts (farm-to-fashion journey)
  - User generates images + videos with free tools (manual path)
- [ ] Virtual fitting room page (split-screen: photo | try-on)
- [ ] Garment gallery with semantic search (Qdrant)
- [ ] Wardrobe page (saved looks)
- [ ] Size recommendation card with fit score
- [ ] Quantum match score display

### 📋 Week 6 — Polish + Portfolio Deploy
- [ ] Prometheus metrics on all services
- [ ] Grafana dashboards (try-on latency, cache hit rate, model inference time)
- [ ] Stable Diffusion texture enhancement (optional — `diffusers` inpainting)
- [ ] Deploy to Hugging Face Spaces (Gradio interface for easy demo)
- [ ] GitHub README with before/after screenshots
- [ ] Demo video (person trying on 5 different garments)

---

## Service Ports

| Service | Port | Language |
|---------|------|----------|
| dashboard | :3002 | TypeScript (Next.js 15) |
| gateway | :3004 | Go (Fiber v3) |
| image-processor | :8090 | Rust (Axum) |
| ml-pipeline | :8001 | Python (FastAPI) |
| PostgreSQL | :5432 | — |
| Redis | :6379 | — |
| Qdrant | :6333 | — |
| MinIO API | :9000 | — |
| MinIO Console | :9001 | — |
| Redpanda | :9092 | — |
| Prometheus | :9090 | — |
| Grafana | :3001 | — |

---

## Local Dev Commands (Week 1 target)

```bash
# 1. Install Python packages
pip install uv
uv venv services/ml-pipeline/venv
uv pip install torch torchvision torchaudio
uv pip install tensorflow-macos tensorflow-metal

# 2. Start all infra
cd ~/Documents/virtual_tryon
docker compose up -d

# 3. Run ML pipeline
cd services/ml-pipeline
source venv/bin/activate
dapr run --app-id ml-pipeline --app-port 8001 --dapr-http-port 3501 \
  --resources-path ../../infra/dapr/components \
  -- uvicorn app.main:app --port 8001 --reload

# 4. Run Rust image processor
cd services/image-processor
dapr run --app-id image-processor --app-port 8090 --dapr-http-port 3502 \
  --resources-path ../../infra/dapr/components \
  -- cargo run

# 5. Run Go gateway
cd services/gateway
go run ./cmd/main.go

# 6. Run dashboard
cd services/dashboard
pnpm dev
```

---

## M2 Max GPU Configuration

```python
# PyTorch — use MPS backend (M2 Mac GPU)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# IDM-VTON on M2 Max
# Inference time: ~15-25 seconds per try-on (MPS)
# VRAM usage: ~8-12GB unified memory
# 32GB total RAM → comfortable headroom
```

---

## Portfolio Value

- "IDM-VTON (state-of-the-art 2024 model) running on Apple Silicon MPS backend"
- "Polyglot microservices: Rust + Go + Python + TypeScript unified via DAPR"
- "Qiskit Grover's O(√N) garment matching — quantum computing in production"
- "SAM2 body segmentation accurate to 2cm measurements"
- "Cinematic scroll-driven landing page (lets-scroll technique)"
- "Relevant to $500B+ e-commerce industry"

---

## Error Reference Log

*(Updated as issues are encountered)*
