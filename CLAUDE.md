# Virtual Try-On System — CLAUDE.md

**Last Updated:** 2026-09-07  
**Status:** Phase 2 — Auth system + per-user YouCam keys + R2 image storage

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

User apni photo upload kare aur virtually kuch bhi try-on kar sake — YouCam (Perfect Corp) cloud API se photorealistic results.

- **👔 Clothes** — upper / lower / full body garment try-on (shirts, dresses, pants, jackets)
- **👜 Bag** — handbag / purse try-on with style presets (Parisian Chic, Urban Chic, etc.)
- **💄 Makeup** — lip color, blush, eye shadow, foundation (presets: Natural, Glam, Bold Lips, Smoky Eye)
- **👁️ Eye Color** — colored contact lens try-on (8 presets + custom hex color picker)
- **🎩 Hat** — hat / cap try-on
- **👟 Shoes** — footwear try-on
- **Next.js dashboard** se feature-tabbed virtual fitting room UI

**No local GPU needed.** YouCam API handles all inference in the cloud.  
**Industry relevance:** Zara, Amazon, Daraz jaise e-commerce platforms ke liye

### Phase 1 Setup (REQUIRED)
1. YouCam API key: [yce.makeupar.com/ai-api](https://yce.makeupar.com/ai-api) → free tier
2. Add to `.env`: `YOUCAM_API_KEY=` + `YOUCAM_SECRET_KEY=`
3. Deploy ML Pipeline to Railway, Dashboard to Vercel

### Phase 2 Setup (After Phase 1 deploys)
1. **NeonDB** — [neon.tech](https://neon.tech) → free PostgreSQL → add `DATABASE_URL` to env
2. **Cloudflare R2** — [dash.cloudflare.com](https://dash.cloudflare.com) → R2 → free 10GB → add `MINIO_ENDPOINT` + keys
   - R2 is S3-compatible — boto3 code stays unchanged, just swap the endpoint

---

## Architecture

```
User Browser
     ↓
Next.js Dashboard (Vercel)       ← TypeScript — landing, login, signup, tryon, wardrobe
     ↓ NEXT_PUBLIC_GATEWAY_URL
Python FastAPI ML Pipeline (Railway) ← auth, YouCam API calls, R2 upload, NeonDB CRUD
     ↓
Perfect Corp YouCam API (cloud)  ← AI inference — clothes, bag, makeup, eyes, hat, shoes
     ↓
Cloudflare R2                    ← wardrobe image storage (S3-compatible, free 10GB)
NeonDB (PostgreSQL)              ← users + wardrobe metadata
```

### Stack

| Service | Tech | Phase | Status |
|---|---|---|---|
| Frontend | Next.js 15 → Vercel | Phase 1 | ✅ Live |
| ML Pipeline | Python FastAPI → Railway | Phase 1 | ✅ Live |
| AI Inference | YouCam API (Perfect Corp cloud) | Phase 1 | ✅ Live |
| Database | PostgreSQL → NeonDB (serverless free) | Phase 2 | ✅ Live |
| Image Storage | S3-compatible → Cloudflare R2 (free 10GB) | Phase 2 | ✅ Live |
| Auth | JWT + bcrypt signup/login | Phase 2 | ✅ Live |
| Per-user API keys | Each user stores own YouCam keys | Phase 2 | ✅ Live |

> ⚠️ **No local ML models, no Docker, no complex infrastructure needed.**
> YouCam cloud handles all AI inference.

### Phase 2 Features (✅ Complete)
- **Auth**: JWT-based signup/login (`POST /api/auth/signup`, `POST /api/auth/login`)
- **Admin**: Donia (`donia1510aptech@gmail.com`) uses env-based YouCam keys automatically
- **Users**: New signups must provide their own YouCam API key + secret at registration
- **Wardrobe isolation**: Each user sees only their own saved items (filtered by JWT user_id)
- **R2 image storage**: Wardrobe images upload to Cloudflare R2; NeonDB stores URL only (not base64)
- **Image proxy**: `GET /api/image/<key>` endpoint serves R2 images (no public R2 URL needed)
- **NeonDB tables**: `users` (email, password_hash, youcam_api_key, youcam_secret_key, is_admin) + `wardrobe`

---

## Service Ports

| Service | Port | Deployed On | Notes |
|---|---|---|---|
| dashboard | :3002 | Vercel (prod) | Next.js 15 |
| ml-pipeline | :8001 | Railway (prod) | FastAPI + YouCam |
| NeonDB | cloud | neon.tech | PostgreSQL, free tier |
| Cloudflare R2 | cloud | cloudflare.com | S3-compatible, 10GB free |

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /api/auth/signup | none | Register (admin auto-detected by email) |
| POST | /api/auth/login | none | Login → JWT token |
| GET | /api/auth/me | JWT | Get current user |
| POST | /api/tryon | none | Clothes try-on |
| POST | /api/bag | none | Bag try-on |
| POST | /api/makeup | none | Makeup try-on |
| POST | /api/eye-color | none | Eye color try-on |
| POST | /api/hat | none | Hat try-on |
| POST | /api/shoes | none | Shoes try-on |
| GET | /api/wardrobe | JWT | Get user's wardrobe |
| POST | /api/wardrobe/save | JWT | Save result → R2 + NeonDB |
| DELETE | /api/wardrobe/{id} | JWT | Delete wardrobe item |
| GET | /api/image/{key} | none | Proxy R2 image to browser |

---

## Data Flow (Current)

```
1. User visits /tryon → redirected to /login if not logged in
2. Login/Signup → JWT stored in localStorage
3. User uploads photos → FastAPI (Railway) → YouCam API (cloud) → result base64
4. User clicks Save → Railway uploads to R2, stores URL in NeonDB
5. Wardrobe page fetches items with JWT → NeonDB rows → images served via /api/image proxy
```

---

## Local Setup Commands

```bash
# Backend
cd services/ml-pipeline
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload

# Frontend
cd services/dashboard
pnpm install
pnpm dev
```

---

## Environment Variables (.env)

```
# YouCam API (Perfect Corp)
YOUCAM_API_KEY=sk-...
YOUCAM_SECRET_KEY=MIGf...

# Auth
JWT_SECRET=<long random string>
ADMIN_EMAIL=donia1510aptech@gmail.com

# NeonDB (PostgreSQL)
DATABASE_URL=postgresql://...@neon.tech/neondb?sslmode=require&channel_binding=require

# Cloudflare R2 (image storage)
MINIO_ENDPOINT=https://<account>.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=<r2_access_key>
MINIO_SECRET_KEY=<r2_secret_key>
MINIO_BUCKET=virtualfit-images
MINIO_USE_SSL=true

# Frontend URL (for Vercel env)
NEXT_PUBLIC_GATEWAY_URL=https://virtualfit-production.up.railway.app
```

---

## Key Decisions Log

| Decision | Reason |
|----------|--------|
| YouCam API | No local GPU needed, photorealistic results, 15s inference |
| Railway for FastAPI | Simple Python deploy, free tier, auto-deploy from GitHub |
| Vercel for Next.js | Best Next.js platform, free tier |
| NeonDB | Serverless PostgreSQL, free 0.5GB, no Docker |
| Cloudflare R2 | Free 10GB, S3-compatible (boto3 unchanged) |
| R2 proxy via Railway | No public R2 URL needed; `/api/image/<key>` serves images |
| bcrypt + PyJWT | Simple, production-grade auth, no external service |

---

## Error Reference & Lessons Learned

### ✅ Railway build error: `Invalid requirement: 'uv=='`
Nixpacks detected pyproject.toml with uv and generated broken pip command.  
**Fix:** Add `requirements.txt` — Railway uses pip directly.

### ✅ Vercel TypeScript error: `Cannot find name 'GATEWAY'`
Variable in tryon/page.tsx is named `ML`, not `GATEWAY`.  
**Fix:** Use `${ML}` in all fetch calls inside that file.

### ✅ CORS error: Vercel frontend → Railway backend blocked
CORS middleware only allowed localhost origins.  
**Fix:** `allow_origins=["*"]` in FastAPI CORS middleware.

### ✅ NeonDB `channel_binding` error on connect
**Fix:** Add `channel_binding=require` to DATABASE_URL.

### ✅ Base64 images filling NeonDB (0.5GB limit hit)
Wardrobe save was storing full base64 string in `result_url` column (~500KB per image).  
**Fix (Phase 2):** Upload image bytes to Cloudflare R2, store proxy URL `/api/image/<key>` in NeonDB.

### ✅ R2 images not publicly accessible
R2 bucket is private by default — no public URL.  
**Fix:** Added `GET /api/image/{key}` proxy endpoint on Railway that fetches from R2 and streams to browser.

### 📋 General Rules
- **Always use `pnpm`** — never `npm` for dashboard
- **Railway env vars** — set in Railway dashboard under Variables tab
- **Vercel env vars** — set in Vercel dashboard under Settings → Environment Variables

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
