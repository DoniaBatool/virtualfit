# VirtualFit — Development Commands
# Usage: make dev | make stop | make logs | make test

.PHONY: dev stop logs test build clean

# ─── Start everything ─────────────────────────────────────────────────────────
dev:
	@echo "🚀 Starting VirtualFit (Docker + all services with DAPR)..."
	docker compose up -d
	@sleep 3
	@echo "🤖 Starting ML Pipeline with DAPR..."
	dapr run \
		--app-id ml-pipeline \
		--app-port 8001 \
		--dapr-http-port 3501 \
		--resources-path infra/dapr/components \
		-- sh -c "cd services/ml-pipeline && uv run uvicorn app.main:app --port 8001 --reload" &
	@echo "🦀 Starting Image Processor with DAPR..."
	dapr run \
		--app-id image-processor \
		--app-port 8090 \
		--dapr-http-port 3502 \
		--resources-path infra/dapr/components \
		-- sh -c "cd services/image-processor && cargo run --release" &
	@echo "🔵 Starting Go Gateway with DAPR..."
	dapr run \
		--app-id gateway \
		--app-port 3004 \
		--dapr-http-port 3503 \
		--resources-path infra/dapr/components \
		-- sh -c "cd services/gateway && go run ./cmd/main.go" &
	@echo "🌐 Starting Next.js Dashboard..."
	sh -c "cd services/dashboard && pnpm dev" &
	@echo ""
	@echo "✅ All services starting up:"
	@echo "   Dashboard:       http://localhost:3002"
	@echo "   Gateway:         http://localhost:3004"
	@echo "   ML Pipeline:     http://localhost:8001"
	@echo "   Image Processor: http://localhost:8090"
	@echo "   MinIO Console:   http://localhost:9001"
	@echo "   Grafana:         http://localhost:3001"
	@echo "   Prometheus:      http://localhost:9090"

# ─── Stop everything ──────────────────────────────────────────────────────────
stop:
	@echo "🛑 Stopping all DAPR apps..."
	dapr stop --app-id ml-pipeline 2>/dev/null || true
	dapr stop --app-id image-processor 2>/dev/null || true
	dapr stop --app-id gateway 2>/dev/null || true
	pkill -f "pnpm dev" 2>/dev/null || true
	@echo "🛑 Stopping Docker services..."
	docker compose down
	@echo "✅ All stopped"

# ─── Individual service start (for development) ───────────────────────────────
ml:
	cd services/ml-pipeline && \
	dapr run \
		--app-id ml-pipeline \
		--app-port 8001 \
		--dapr-http-port 3501 \
		--resources-path ../../infra/dapr/components \
		-- uv run uvicorn app.main:app --port 8001 --reload

rust:
	cd services/image-processor && \
	dapr run \
		--app-id image-processor \
		--app-port 8090 \
		--dapr-http-port 3502 \
		--resources-path ../../infra/dapr/components \
		-- cargo run

gateway:
	cd services/gateway && \
	dapr run \
		--app-id gateway \
		--app-port 3004 \
		--dapr-http-port 3503 \
		--resources-path ../../infra/dapr/components \
		-- go run ./cmd/main.go

dashboard:
	cd services/dashboard && pnpm dev

# ─── Logs ─────────────────────────────────────────────────────────────────────
logs:
	docker compose logs -f --tail=50

# ─── Test all endpoints ───────────────────────────────────────────────────────
test:
	@echo "🧪 Testing all endpoints..."
	@echo "\n--- ML Pipeline Health ---"
	@curl -s http://localhost:8001/health | python3 -m json.tool
	@echo "\n--- Gateway Health ---"
	@curl -s http://localhost:3004/health | python3 -m json.tool || echo "Gateway not running"
	@echo "\n--- Quantum Match ---"
	@curl -s "http://localhost:8001/api/quantum-match?body_type=athletic&category=shirt&top_k=3" | python3 -m json.tool
	@echo "\n--- Size Predict ---"
	@curl -s -X POST http://localhost:8001/api/recommend-size \
		-H "Content-Type: application/json" \
		-d '{"shoulder_cm":42,"chest_cm":96,"waist_cm":80,"hip_cm":98}' | python3 -m json.tool
	@echo "\n✅ Tests complete"

# ─── Build ────────────────────────────────────────────────────────────────────
build:
	@echo "🔨 Building Rust image processor..."
	cd services/image-processor && cargo build --release
	@echo "🔨 Building Go gateway..."
	cd services/gateway && go build -o bin/gateway ./cmd/main.go
	@echo "🔨 Building Next.js dashboard..."
	cd services/dashboard && pnpm build
	@echo "✅ All built"

# ─── Clean ────────────────────────────────────────────────────────────────────
clean:
	docker compose down -v
	cd services/image-processor && cargo clean
	cd services/dashboard && rm -rf .next node_modules
	cd services/ml-pipeline && rm -rf .venv
