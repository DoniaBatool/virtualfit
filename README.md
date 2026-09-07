# 👗 VirtualFit — AI Virtual Try-On System

> Upload your photo → see yourself wearing clothes, bags, makeup, colored contacts, hats, and shoes instantly.

**Stack:** Python FastAPI · Next.js 15 · **AI:** Cloud-based ML inference via Perfect Corp YouCam API, with custom multi-feature try-on pipeline built on top.

---

## What It Does

- 👔 **Clothes Try-On** — shirt, dress, jacket, pants (upper / lower / full body)
- 👜 **Bag Try-On** — handbag / purse with style presets (Parisian Chic, Urban Chic, Art Deco…)
- 💄 **Makeup Try-On** — lip color, blush, eye shadow (presets: Natural, Glam, Bold Lips, Smoky Eye)
- 👁️ **Eye Color Try-On** — colored contact lenses (8 presets + custom hex color picker)
- 🎩 **Hat Try-On** — hats and caps
- 👟 **Shoes Try-On** — any footwear

All AI inference runs on **Perfect Corp's cloud** (YouCam API) — photorealistic results, no local GPU needed.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Next.js 15 Dashboard (Vercel)           │
│   / → Landing Page   /tryon → Try-On   /wardrobe    │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP (NEXT_PUBLIC_GATEWAY_URL)
┌──────────────────▼──────────────────────────────────┐
│         Python ML Pipeline (Railway / local)         │
│              FastAPI · YouCam API calls              │
└──────────────────┬──────────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────────┐
│         Perfect Corp YouCam AI (cloud)               │
│  Clothes · Bag · Makeup · Eye Color · Hat · Shoes   │
└─────────────────────────────────────────────────────┘
         ↓ result images
┌─────────────────────────────────────────────────────┐
│              MinIO (local Docker, optional)          │
│              S3-compatible image storage             │
└─────────────────────────────────────────────────────┘
```

| Service | Tech | Deployed On | Status |
|---|---|---|---|
| Dashboard | Next.js 15 | Vercel | ✅ Phase 1 |
| ML Pipeline | Python FastAPI | Railway | ✅ Phase 1 |
| AI Inference | YouCam API | Perfect Corp cloud | ✅ Phase 1 |
| Database | PostgreSQL | NeonDB (serverless) | 🔜 Phase 2 |
| Image Storage | S3-compatible | Cloudflare R2 | 🔜 Phase 2 |

---

## AI / ML Stack

| Feature | API Endpoint | Details |
|---|---|---|
| 👔 Clothes Try-On | YouCam `/task/cloth-v4` | Photorealistic garment fitting |
| 👜 Bag Try-On | YouCam `/task/bag` | 5 style presets, gender-aware |
| 💄 Makeup Try-On | YouCam `/task/makeup-vto` | Lips, blush, eye shadow, foundation |
| 👁️ Eye Color | YouCam `/task/eye-color-lens` | 8 presets + custom hex color |
| 🎩 Hat Try-On | YouCam `/task/hat` | Head-aware placement |
| 👟 Shoes Try-On | YouCam `/task/shoes` | Full-body foot detection |

**Provider:** [Perfect Corp YouCam API](https://yce.makeupar.com/ai-api) — register free, get API key, add to `.env`  
**No local GPU required** — all inference on Perfect Corp's cloud.

---

## Project Structure

```
virtual_tryon/
├── services/
│   ├── dashboard/              # Next.js 15 frontend (deployed to Vercel)
│   │   ├── app/
│   │   │   ├── page.tsx            # Redirects to landing page
│   │   │   ├── tryon/page.tsx      # Main try-on UI (6 feature tabs)
│   │   │   └── wardrobe/page.tsx   # Saved results with lightbox
│   │   ├── public/
│   │   │   └── landing.html        # Cinematic scroll landing page
│   │   └── vercel.json             # Vercel deployment config
│   └── ml-pipeline/            # Python FastAPI ML service (deployed to Railway)
│       ├── app/
│       │   ├── main.py             # FastAPI app + all 6 try-on endpoints
│       │   ├── tryon.py            # YouCam API integration (all features)
│       │   └── storage.py          # MinIO integration
│       ├── pyproject.toml          # Lightweight deps (no torch/diffusers)
│       ├── railway.json            # Railway deployment config
│       └── Procfile                # Railway start command
├── docker-compose.yml          # MinIO + PostgreSQL only
├── .env                        # API keys (gitignored)
└── CLAUDE.md                   # Dev notes + architecture
```

---

## Quick Start

### Prerequisites

- Docker Desktop (for MinIO, optional)
- Node.js 20+ and pnpm
- Python 3.12+ and uv
- YouCam API key from [yce.makeupar.com/ai-api](https://yce.makeupar.com/ai-api)

### 1. Set up environment

```bash
# Add your YouCam API key to .env
echo "YOUCAM_API_KEY=your_key_here" >> .env
```

### 2. ML Pipeline

```bash
cd services/ml-pipeline
uv sync
uv run uvicorn app.main:app --port 8001 --reload
```

### 3. Next.js Dashboard

```bash
cd services/dashboard
pnpm install
pnpm dev
```

Open [http://localhost:3002](http://localhost:3002) — landing page loads first.

### 4. (Optional) Start MinIO for image storage

```bash
docker compose up -d
```

---

## API Endpoints

### ML Pipeline (port 8001)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service status |
| GET | `/api/tryon/status` | YouCam API connection status |
| POST | `/api/tryon` | Clothes virtual try-on |
| POST | `/api/bag` | Bag try-on |
| POST | `/api/makeup` | Makeup try-on |
| POST | `/api/eye-color` | Eye color try-on |
| POST | `/api/hat` | Hat try-on |
| POST | `/api/shoes` | Shoes try-on |

### Example: Clothes Try-On

```bash
curl -X POST http://localhost:8001/api/tryon \
  -F "person_image=@/path/to/person.jpg" \
  -F "garment_image=@/path/to/shirt.jpg" \
  -F "category=upper_body"
```

---

## Deployment

### Phase 1 — Core (Vercel + Railway)

**Railway (ML Pipeline):**
1. [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Root Directory: `services/ml-pipeline`
3. Env vars: `YOUCAM_API_KEY`, `YOUCAM_SECRET_KEY`
4. Deploy — auto-detected from `railway.json`

**Vercel (Dashboard):**
1. [vercel.com](https://vercel.com) → New Project → import repo
2. Root Directory: `services/dashboard`
3. Env var: `NEXT_PUBLIC_GATEWAY_URL=https://your-railway-url`
4. Deploy

### Phase 2 — Database + Storage (NeonDB + Cloudflare R2)

**NeonDB (PostgreSQL — user accounts, wardrobe):**
1. [neon.tech](https://neon.tech) → free account → create database `virtualfit`
2. Copy connection string → add to `.env` and Railway/Vercel env vars:
   ```
   DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/virtualfit
   ```

**Cloudflare R2 (image storage — replaces local MinIO):**
1. [dash.cloudflare.com](https://dash.cloudflare.com) → R2 → Create bucket `virtualfit-images`
2. Create API token → add to `.env` and Railway env vars:
   ```
   MINIO_ENDPOINT=https://xxx.r2.cloudflarestorage.com
   MINIO_ACCESS_KEY=your_r2_access_key
   MINIO_SECRET_KEY=your_r2_secret_key
   MINIO_BUCKET=virtualfit-images
   ```
   > Code stays identical — R2 is S3-compatible, boto3 works unchanged.

---

## Environment Variables

```env
# ── Phase 1 (required now) ──────────────────────────────
YOUCAM_API_KEY=your_api_key_here
YOUCAM_SECRET_KEY=your_secret_key_here
NEXT_PUBLIC_GATEWAY_URL=http://localhost:8001   # → Railway URL in production

# ── Phase 2 (NeonDB + Cloudflare R2 — add later) ───────
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/virtualfit
JWT_SECRET=your_jwt_secret

MINIO_ENDPOINT=https://xxx.r2.cloudflarestorage.com   # Cloudflare R2 in prod
MINIO_ACCESS_KEY=your_r2_access_key                   # or minioadmin locally
MINIO_SECRET_KEY=your_r2_secret_key
MINIO_BUCKET=virtualfit-images
```

---

## Error Reference

### dotenv timing issue — API key "not set" even after adding to .env
**Cause:** `_API_KEY = os.environ.get(...)` at module level runs before `load_dotenv()`.  
**Fix:** Use lazy function `_api_key()` that reads `os.environ.get()` at call time. Also load dotenv inside `tryon.py` itself.

### PostgreSQL port conflict (5432 already in use)
**Fix:** Use port `5433:5432` in docker-compose.yml (macOS Homebrew already uses 5432).

### uv sync — correct way to install/remove packages
Always use `uv sync` after updating `pyproject.toml` — never `pip install` directly.

---

## Built By

**Donia Batool** — Full-stack AI systems

---

## License

MIT
