# VirtualFit — Project Plan

**Last Updated:** 2026-09-07  
**Stack:** Python FastAPI + Next.js 15 + YouCam API  
**Deployed:** Railway (backend) + Vercel (frontend)

---

## What We Built

An AI-powered virtual try-on web app. Users upload their photo and virtually try on clothes, bags, makeup, colored contacts, hats, and shoes — all via Perfect Corp's YouCam cloud API.

**No local GPU. No local ML models. No Docker required for deployment.**

---

## Architecture

```
User Browser
     ↓
Next.js 15 Dashboard (Vercel)
  /           → landing page (public/landing.html)
  /login      → JWT login
  /signup     → account creation (with YouCam key input)
  /tryon      → 6-feature virtual try-on UI (auth-protected)
  /wardrobe   → saved results gallery (auth-protected)
     ↓ NEXT_PUBLIC_GATEWAY_URL (https://virtualfit-production.up.railway.app)
Python FastAPI ML Pipeline (Railway)
  POST /api/auth/signup   → register user
  POST /api/auth/login    → JWT token
  GET  /api/auth/me       → current user
  POST /api/tryon         → clothes try-on
  POST /api/bag           → bag try-on
  POST /api/makeup        → makeup try-on
  POST /api/eye-color     → eye color try-on
  POST /api/hat           → hat try-on
  POST /api/shoes         → shoes try-on
  GET  /api/wardrobe      → user's saved items (JWT)
  POST /api/wardrobe/save → upload to R2 + save URL in NeonDB (JWT)
  DELETE /api/wardrobe/{id} → delete item (JWT)
  GET  /api/image/{key}   → proxy R2 image to browser
     ↓
Perfect Corp YouCam API (cloud inference)
     ↓
Cloudflare R2 (wardrobe image storage)
NeonDB PostgreSQL (users + wardrobe metadata)
```

---

## Tech Stack

| Layer | Tech | Hosted On |
|---|---|---|
| Frontend | Next.js 15 (App Router, TypeScript) | Vercel |
| Backend | Python FastAPI + uvicorn | Railway |
| AI Inference | YouCam API (Perfect Corp) | Perfect Corp cloud |
| Auth | JWT (PyJWT) + bcrypt | Railway |
| Database | PostgreSQL (NeonDB serverless) | neon.tech |
| Image Storage | S3-compatible (Cloudflare R2) | cloudflare.com |

---

## Database Schema (NeonDB)

```sql
-- Users
CREATE TABLE users (
  id               SERIAL PRIMARY KEY,
  email            TEXT UNIQUE NOT NULL,
  password_hash    TEXT NOT NULL,
  youcam_api_key   TEXT DEFAULT '',
  youcam_secret_key TEXT DEFAULT '',
  is_admin         BOOLEAN DEFAULT FALSE,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Wardrobe
CREATE TABLE wardrobe (
  id           SERIAL PRIMARY KEY,
  user_id      TEXT NOT NULL,
  feature      TEXT NOT NULL,
  result_url   TEXT NOT NULL,        -- /api/image/<r2_key> proxy URL
  thumbnail_url TEXT,
  settings     JSONB,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_wardrobe_user ON wardrobe(user_id);
```

---

## Auth Flow

1. **Admin** (`donia1510aptech@gmail.com`) → signup/login → backend uses env `YOUCAM_API_KEY`
2. **Regular users** → signup with their own YouCam API key + secret → stored in `users` table
3. JWT stored in `localStorage` as `vf_token`
4. All wardrobe API calls include `Authorization: Bearer <token>`

---

## Phase Completion

### ✅ Phase 1 — Core Try-On (Complete)
- [x] FastAPI ML pipeline with all 6 YouCam features
- [x] Next.js dashboard with feature tabs UI
- [x] Landing page (cinematic scroll)
- [x] Railway deployment (backend)
- [x] Vercel deployment (frontend)

### ✅ Phase 2 — Auth + Storage (Complete)
- [x] NeonDB `users` table with YouCam key storage
- [x] JWT signup/login endpoints
- [x] Admin auto-detection by email
- [x] Per-user YouCam key injection
- [x] Cloudflare R2 bucket (`virtualfit-images`)
- [x] Wardrobe images upload to R2 (not base64 in DB)
- [x] `/api/image/<key>` proxy endpoint
- [x] Wardrobe isolation per user (JWT-filtered)
- [x] Login + Signup pages in Next.js
- [x] `/tryon` and `/wardrobe` protected (redirect to /login)

---

## Environment Variables

### Railway (ML Pipeline)
```
YOUCAM_API_KEY=sk-...
YOUCAM_SECRET_KEY=MIGf...
JWT_SECRET=<long random string>
DATABASE_URL=postgresql://...@neon.tech/neondb?sslmode=require
MINIO_ENDPOINT=https://<account>.r2.cloudflarestorage.com
MINIO_ACCESS_KEY=<r2_access_key>
MINIO_SECRET_KEY=<r2_secret_key>
MINIO_BUCKET=virtualfit-images
ADMIN_EMAIL=donia1510aptech@gmail.com
```

### Vercel (Dashboard)
```
NEXT_PUBLIC_GATEWAY_URL=https://virtualfit-production.up.railway.app
```

---

## Local Dev

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

## Deployed URLs

- **Frontend:** https://virtualfit-tau.vercel.app
- **Backend:** https://virtualfit-production.up.railway.app
- **Health:** https://virtualfit-production.up.railway.app/health

---

## Key Technical Decisions

| Decision | Reason |
|---|---|
| YouCam API instead of local models | No GPU needed, photorealistic results, 15s inference |
| Railway for FastAPI | Simple Python deployment, free tier, auto-deploy from GitHub |
| Vercel for Next.js | Best Next.js platform, free tier, instant deploys |
| NeonDB for PostgreSQL | Serverless, free 0.5GB, no Docker needed |
| Cloudflare R2 for images | Free 10GB, S3-compatible (boto3 works unchanged) |
| R2 image proxy via Railway | No need for public R2 URL; images served via /api/image endpoint |
| bcrypt + PyJWT for auth | Simple, production-grade, no external auth service needed |

---

## Error Reference

### ✅ Railway build error: `Invalid requirement: 'uv=='`
Nixpacks detected pyproject.toml and generated broken pip command.  
**Fix:** Add `requirements.txt` — Railway uses pip directly.

### ✅ Vercel TypeScript error: `Cannot find name 'GATEWAY'`
Variable in tryon/page.tsx is named `ML`, not `GATEWAY`.  
**Fix:** Use `${ML}` in all fetch calls.

### ✅ CORS error: Vercel → Railway blocked
CORS middleware only allowed localhost origins.  
**Fix:** `allow_origins=["*"]` in FastAPI CORS middleware.

### ✅ NeonDB `channel_binding` error
Add `channel_binding=require` to DATABASE_URL query string.

### ✅ Base64 images filling NeonDB (0.5GB limit)
Images stored as base64 strings in `result_url` column.  
**Fix (Phase 2):** Upload to R2, store only the proxy URL in NeonDB.
