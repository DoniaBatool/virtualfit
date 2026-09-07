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
         ↓ wardrobe images
┌─────────────────────────────────────────────────────┐
│              Cloudflare R2 (image storage)           │
│   NeonDB PostgreSQL (users + wardrobe metadata)     │
└─────────────────────────────────────────────────────┘
```

| Service | Tech | Deployed On | Status |
|---|---|---|---|
| Dashboard | Next.js 15 | Vercel | ✅ Live |
| ML Pipeline | Python FastAPI | Railway | ✅ Live |
| AI Inference | YouCam API | Perfect Corp cloud | ✅ Live |
| Auth (JWT) | bcrypt + PyJWT | Railway | ✅ Phase 2 |
| Database | PostgreSQL | NeonDB (serverless) | ✅ Phase 2 |
| Image Storage | S3-compatible | Cloudflare R2 | ✅ Phase 2 |

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
│   │   │   ├── login/page.tsx      # Login page (JWT)
│   │   │   ├── signup/page.tsx     # Signup page (with YouCam key input)
│   │   │   ├── tryon/page.tsx      # Main try-on UI (6 feature tabs, auth-protected)
│   │   │   └── wardrobe/page.tsx   # Saved results with lightbox (auth-protected)
│   │   ├── public/
│   │   │   └── landing.html        # Cinematic scroll landing page
│   │   └── vercel.json             # Vercel deployment config
│   └── ml-pipeline/            # Python FastAPI ML service (deployed to Railway)
│       ├── app/
│       │   ├── main.py             # FastAPI app + all endpoints + auth
│       │   ├── auth.py             # JWT create/decode + bcrypt password hashing
│       │   ├── tryon.py            # YouCam API integration (all features)
│       │   ├── database.py         # NeonDB CRUD (users + wardrobe)
│       │   └── storage.py          # Cloudflare R2 upload + image proxy
│       ├── requirements.txt        # Deps including bcrypt + PyJWT
│       ├── railway.json            # Railway deployment config
│       └── Procfile                # Railway start command
├── .env                        # API keys (gitignored)
├── PLAN.md                     # Project plan + phase completion
└── CLAUDE.md                   # Dev notes + architecture
```

---

## Quick Start (Local Dev)

### Prerequisites
- Node.js 20+ and pnpm
- Python 3.12+
- YouCam API key from [yce.makeupar.com/ai-api](https://yce.makeupar.com/ai-api)

### 1. Backend

```bash
cd services/ml-pipeline
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload
```

### 2. Frontend

```bash
cd services/dashboard
pnpm install
pnpm dev
```

Open [http://localhost:3002](http://localhost:3002)

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | — | Register account |
| POST | `/api/auth/login` | — | Login → JWT token |
| GET | `/api/auth/me` | JWT | Current user |
| POST | `/api/tryon` | — | Clothes try-on |
| POST | `/api/bag` | — | Bag try-on |
| POST | `/api/makeup` | — | Makeup try-on |
| POST | `/api/eye-color` | — | Eye color try-on |
| POST | `/api/hat` | — | Hat try-on |
| POST | `/api/shoes` | — | Shoes try-on |
| GET | `/api/wardrobe` | JWT | User's wardrobe |
| POST | `/api/wardrobe/save` | JWT | Save to wardrobe (→ R2) |
| DELETE | `/api/wardrobe/{id}` | JWT | Delete item |
| GET | `/api/image/{key}` | — | Proxy R2 image |

---

## Deployment (Live)

| Service | URL |
|---|---|
| Frontend | https://virtualfit-tau.vercel.app |
| Backend | https://virtualfit-production.up.railway.app |

---

## Environment Variables

### Railway (backend)
```env
YOUCAM_API_KEY=sk-...
YOUCAM_SECRET_KEY=MIGf...
JWT_SECRET=<long random string>
ADMIN_EMAIL=donia1510aptech@gmail.com
DATABASE_URL=postgresql://...@neon.tech/neondb?sslmode=require&channel_binding=require
MINIO_ENDPOINT=https://<account>.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=<r2_access_key>
MINIO_SECRET_KEY=<r2_secret_key>
MINIO_BUCKET=virtualfit-images
MINIO_USE_SSL=true
```

### Vercel (frontend)
```env
NEXT_PUBLIC_GATEWAY_URL=https://virtualfit-production.up.railway.app
```

---

## Built By

**Donia Batool** — Full-stack AI systems

---

## License

MIT
