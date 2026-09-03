-- Virtual Try-On System — Database Schema
-- Run: psql $DATABASE_URL -f infra/migrations/001_init.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Users ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email       TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    password    TEXT NOT NULL,          -- bcrypt hashed
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Garments catalog ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS garments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,          -- shirt, pants, dress, etc.
    brand       TEXT,
    color       TEXT,
    image_url   TEXT NOT NULL,          -- MinIO path
    sizes       TEXT[],                 -- ['XS','S','M','L','XL']
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Try-on results ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tryon_results (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    garment_id      UUID REFERENCES garments(id),
    person_image    TEXT NOT NULL,      -- MinIO path: original photo
    result_image    TEXT NOT NULL,      -- MinIO path: try-on output
    size_prediction TEXT,               -- 'M'
    fit_score       INTEGER,            -- 0-100
    measurements    JSONB,              -- {shoulder_cm, chest_cm, waist_cm, hip_cm}
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Wardrobe (saved looks) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wardrobe (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    tryon_result_id UUID REFERENCES tryon_results(id) ON DELETE CASCADE,
    name            TEXT,               -- user-given name for the look
    saved_at        TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tryon_user_id ON tryon_results(user_id);
CREATE INDEX IF NOT EXISTS idx_wardrobe_user_id ON wardrobe(user_id);
CREATE INDEX IF NOT EXISTS idx_garments_category ON garments(category);
