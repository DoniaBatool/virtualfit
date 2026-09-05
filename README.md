# 👗 VirtualFit — AI Virtual Try-On System

> Polyglot AI system: upload your photo → see yourself wearing clothes, bags, makeup, colored contacts, hats, and shoes instantly.

**Stack:** Rust · Go · Python · TypeScript/Next.js 15 · **AI:** Cloud-based ML inference via Perfect Corp YouCam API, with custom multi-feature try-on pipeline built on top.

---

## What It Does

VirtualFit is a full-stack AI virtual try-on platform built with 4 different technologies working together:

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
│                   Next.js 15 Dashboard               │
│        Landing Page (scroll animation) → Try-On UI  │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────────────────┐
│              Go Gateway (Fiber v3)                   │
│              JWT Auth · Rate Limiting · Proxy        │
└──────────────────┬──────────────────────────────────┘
                   │ DAPR pub/sub (Redpanda/Kafka)
        ┌──────────┼──────────┐
        │          │          │
┌───────▼───┐ ┌────▼────┐ ┌──▼──────────────────────┐
│   Rust    │ │ Python  │ │      MinIO (S3)          │
│  Image    │ │   ML    │ │   Image Storage          │
│ Processor │ │Pipeline │ └─────────────────────────┘
│  (Axum)  │ │(FastAPI)│
└───────────┘ └─────────┘
```

| Service | Language | Framework | Port |
|---|---|---|---|
| Dashboard | TypeScript | Next.js 15 | 3002 |
| Gateway | Go | Fiber v3 | 8080 |
| ML Pipeline | Python | FastAPI + uv | 8001 |
| Image Processor | Rust | Axum | 3001 |
| Message Broker | — | Redpanda (Kafka) | 9092 |
| Object Storage | — | MinIO (S3) | 9000 |
| State Store | — | Redis | 6379 |

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
**No local GPU required** — all inference on Perfect Corp's cloud (A100s).

---

## Project Structure

```
virtualfit/
├── services/
│   ├── dashboard/          # Next.js 15 frontend
│   │   ├── app/
│   │   │   ├── page.tsx        # Redirects to landing page
│   │   │   ├── tryon/          # Main try-on UI
│   │   │   └── wardrobe/       # Saved results
│   │   └── public/
│   │       └── landing.html    # Cinematic scroll landing page
│   ├── gateway/            # Go Fiber v3 API gateway
│   ├── ml-pipeline/        # Python FastAPI ML service
│   │   ├── app/
│   │   │   ├── main.py         # FastAPI app + all 6 try-on endpoints
│   │   │   ├── tryon.py        # YouCam API integration (all features)
│   │   │   └── storage.py      # MinIO integration
│   │   └── pyproject.toml      # Lightweight deps (no torch/qiskit)
│   └── image-processor/    # Rust Axum image processing
├── spaces/                 # Streamlit Cloud deployment
│   ├── app.py              # Streamlit app (3 tabs)
│   └── requirements.txt
├── infra/
│   ├── dapr/components/    # DAPR pub/sub + statestore config
│   └── migrations/         # PostgreSQL schema
├── monitoring/
│   └── prometheus/         # Prometheus config
├── docker-compose.yml      # Full stack orchestration
└── PLAN.md                 # Project roadmap
```

---

## Quick Start

### Prerequisites

- Docker Desktop
- Node.js 20+ and pnpm
- Python 3.12+ and uv
- Rust (stable)
- Go 1.22+

### 1. Start Infrastructure

```bash
docker-compose up -d
```

Starts: Redpanda, Redis, MinIO, PostgreSQL, DAPR sidecar, Prometheus, Grafana.

### 2. ML Pipeline

```bash
cd services/ml-pipeline
uv sync
uv run uvicorn app.main:app --port 8001 --reload
```

**Optional — Download IDM-VTON weights (~9 GB):**
```bash
hf download yisol/IDM-VTON --local-dir vendor/IDM-VTON-weights
```
Without weights, Fast Preview (PIL composite) mode is used automatically.

### 3. Go Gateway

```bash
cd services/gateway
go run cmd/main.go
```

### 4. Rust Image Processor

```bash
cd services/image-processor
cargo run --release
```

### 5. Next.js Dashboard

```bash
cd services/dashboard
pnpm install
pnpm dev
```

Open [http://localhost:3002](http://localhost:3002) — landing page loads first, then click **Try It Free** to go to the try-on UI.

---

## API Endpoints

### ML Pipeline (port 8001)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service status + model info |
| POST | `/api/tryon` | Virtual try-on (person + garment images) |
| POST | `/api/segment` | SAM2 person segmentation |
| POST | `/api/measure` | MediaPipe body measurements |
| POST | `/api/recommend-size` | TensorFlow size prediction |
| GET | `/api/quantum-match` | Qiskit Grover's garment search |
| GET | `/api/tryon/status` | Model download status |

### Example: Try-On Request

```bash
curl -X POST http://localhost:8001/api/tryon \
  -F "person_image=@/path/to/person.jpg" \
  -F "garment_image=@/path/to/shirt.jpg" \
  -F "steps=30"
```

### Example: Quantum Search

```bash
curl "http://localhost:8001/api/quantum-match?body_type=athletic&category=shirt&top_k=5"
```

---

## Quantum Search — How It Works

VirtualFit uses **Grover's Algorithm** (quantum computing) to search through the garment catalog:

- **Classical search:** Up to N=16 checks needed
- **Quantum search:** Only √16 = **4 checks** needed — O(√N) speedup
- **Implementation:** 4-qubit circuit, oracle + diffuser, Qiskit Aer simulator
- **Result:** Top-5 garments ranked by quantum probability amplitude

```
Body type: athletic  |  Category: shirt
→ Quantum circuit: 4 qubits, 2 Grover iterations
→ Results: Classic White Shirt (87%), Striped Oxford (79%), ...
```

---

## Streamlit Demo (Free Cloud Deploy)

The `spaces/` directory contains a standalone Streamlit app with all 3 features:

```bash
pip install -r spaces/requirements.txt
streamlit run spaces/app.py
```

**Deploy free on Streamlit Cloud:**
1. Fork this repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo → set main file: `spaces/app.py` → Deploy

---

## macOS ARM64 Notes

SAM2 and MediaPipe cause SIGABRT crashes on macOS ARM64 when imported in the main process. VirtualFit handles this automatically:

- `segment_person()` runs in an isolated subprocess
- `measure_body()` returns safe default values
- The try-on pipeline works fully without these models

---

## Built By

**Donia Batool** — Full-stack AI systems, polyglot architecture

---

## License

MIT
