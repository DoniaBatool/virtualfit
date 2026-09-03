# 👗 VirtualFit — AI Virtual Try-On System

> Polyglot AI system: upload your photo + any garment → see yourself wearing it instantly.

**Live Demo:** [Streamlit Cloud](https://share.streamlit.io) · **Stack:** Rust · Go · Python · Next.js 15

---

## What It Does

VirtualFit is a full-stack AI virtual try-on platform built with 5 different technologies working together:

- **Upload** your full-body photo and any garment image
- **AI Try-On** overlays the garment on your photo using IDM-VTON (CVPR 2024 diffusion model)
- **Body Measurements** estimated automatically from your photo (shoulder, chest, waist, hip)
- **Size Recommendation** powered by a TensorFlow neural network
- **Quantum Search** finds matching garments using Qiskit Grover's O(√N) algorithm

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

| Component | Technology | Details |
|---|---|---|
| Virtual Try-On | **IDM-VTON** (CVPR 2024) | Diffusion model, 9GB weights |
| Person Segmentation | **SAM2.1-Hiera-Large** | Meta's segment anything model |
| Body Pose | **MediaPipe PoseLandmarker** | Google, Heavy variant |
| Size Prediction | **TensorFlow** Dense Network | 3-layer, trained on synthetic data |
| Garment Search | **Qiskit Grover's O(√N)** | 4-qubit, 16-garment catalog |
| GPU Inference | **TensorFlow Metal** | Apple Silicon MPS acceleration |

> **Fast Preview mode:** When IDM-VTON weights are not downloaded, the system falls back to a PIL composite overlay (instant, no GPU needed).

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
│   │   │   ├── main.py         # FastAPI app + endpoints
│   │   │   ├── tryon.py        # IDM-VTON integration
│   │   │   ├── segmentation.py # SAM2 person segmentation
│   │   │   ├── measurements.py # MediaPipe body measurements
│   │   │   ├── size_predictor.py # TensorFlow size model
│   │   │   ├── quantum_search.py # Qiskit Grover's algorithm
│   │   │   └── storage.py      # MinIO integration
│   │   └── scripts/
│   │       └── download_models.py # One-time model download
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
