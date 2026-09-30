# AI-Powered PR Assistant — Setup & Deployment Guide

> **Tested & Validated Local & AWS Cloud Setup Guide**  
> Branch: `phase-1`  
> Status: **Phase 1 Implementation Complete & 100% Tested**

---

## 1. System Requirements

| Environment | OS / Specs | Runtimes & Services |
|:---|:---|:---|
| **Local Development** | macOS (Apple Silicon / Intel) | Docker Desktop / OrbStack, Python 3.11+, Git |
| **AWS Cloud** | Ubuntu 22.04 / 24.04 LTS (EC2) | Docker Engine + Compose plugin, Python 3.11+, Git |

---

## 2. Phase 1 Implementation Tracker (All 21 Steps Complete)

- [x] **Step 1: AWS / Ubuntu & Local Environment Prerequisites** (Docker, Git, Python 3.11+)
- [x] **Step 2: Project Repository Structure** (`pyproject.toml`, `ruff`, modular `src/` & `tests/`)
- [x] **Step 3: Docker + Compose Base Services** (Postgres + pgvector, Redis, OpenTelemetry Collector, Prometheus, Grafana)
- [x] **Step 4: PostgreSQL Database Schema** (`AnalysisRun`, `WebhookEvent`, `AnalysisFinding`, `TestEvidence`, `CodeEmbedding`)
- [x] **Step 5: Redis Broker & Queues** (Hot-state SHA contracts, capacity management)
- [x] **Step 6: FastAPI Gateway Service** (`/health`, `/webhook/github`, `/api/v1/trigger`, `/api/v1/runs/{id}`)
- [x] **Step 7: GitHub App + Webhook Integration** (HMAC-SHA256 signature verification, idempotency delivery check)
- [x] **Step 8: SHA Contract Issuer & Immutable Snapshot Engine** (Problem 1 Solution: SHA-locked contracts)
- [x] **Step 9: Redis Tiered Priority Worker** (Problem 2 Solution: P0 hotfix starvation-free dequeue)
- [x] **Step 10: Exact Git Checkout & Shared Clone Cache** (Bottleneck #1 Fix: bare clone caching & shallow fetch)
- [x] **Step 11: Deterministic Parallel Static Analysis** (Bottleneck #3 Fix: Linters, SAST, secret scan with timeouts & partial proceed)
- [x] **Step 12: pgvector + Incremental Repository RAG** (Bottleneck #2 Fix: cache-first embedding gate before vector search)
- [x] **Step 13: LangGraph State Machine Orchestration** (Bottleneck #5 Fix: async multi-agent graph with circuit breaker)
- [x] **Step 14: Multi-Agent Code Review** (Bug detection, security analysis, code quality)
- [x] **Step 15: Unit Test Generation Agent** (Diff-targeted unit test synthesis)
- [x] **Step 16: Docker Test Sandbox Execution Engine** (Problem 3 Solution: real sandbox execution with stdout/stderr proof)
- [x] **Step 17: Evidence Validation & Hallucination Filter** (Problem 3 Solution: hard gate dropping unverifiable file/line findings)
- [x] **Step 18: Freshness Check Gate** (Problem 1 Solution: pre-publish SHA comparison to discard stale runs)
- [x] **Step 19: GitHub Status Checks & Review Comments** (Formatted PR markdown with verified confidence scores)
- [x] **Step 20: OpenTelemetry Tracing & Observability** (FastAPI instrumentation, OTEL collector, Prometheus metrics)
- [x] **Step 21: End-to-End System Integration Testing** (Automated full pipeline integration test)

---

## 3. Step-by-Step Setup Guide

### 3.1 Initial Setup on AWS Ubuntu (or Local macOS)

#### On AWS Ubuntu:
```bash
# 1. Update system & install prerequisites
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget jq python3 python3-pip python3-venv

# 2. Install Docker & Compose plugin
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

#### On Local macOS:
Ensure Docker Desktop is open and running.

---

### 3.2 Environment & Dependencies Setup

```bash
# 1. Clone repository and checkout phase-1
git clone <YOUR_GITHUB_REPO_URL>
cd devops_idt_project
git checkout phase-1

# 2. Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -e .

# 4. Configure environment variables
cp .env.example .env
```

---

### 3.3 Start Background Services (Postgres, Redis, OTEL, Grafana)

```bash
# Start all infrastructure containers
docker compose up -d

# Verify all 5 containers are running and healthy:
docker compose ps
```
Services exposed:
- **PostgreSQL (with pgvector)**: `localhost:5433` (configurable via `.env`)
- **Redis**: `localhost:6379`
- **OTEL Collector**: `localhost:4317` (gRPC), `localhost:4318` (HTTP), `localhost:8889` (Prometheus metrics)
- **Prometheus**: `localhost:9090`
- **Grafana**: `localhost:3000` (User: `admin`, Pass: `admin`)

---

### 3.4 Initialize Database Schema

```bash
source .venv/bin/activate
python3 -c "import asyncio; from src.db.session import init_db; asyncio.run(init_db()); print('Database & pgvector ready!')"
```

---

### 3.5 Run Full Automated Test Suite

```bash
source .venv/bin/activate
pytest -v
```
All 4 test suites will execute:
1. `tests/test_sha_contract.py` (Problem 1: SHA contract locking & freshness gate)
2. `tests/test_priority_queue.py` (Problem 2: Tiered priority queue scheduling)
3. `tests/test_evidence_validator.py` (Problem 3: Physical evidence validation & hallucination filter)
4. `tests/test_e2e_pipeline.py` (Step 21: Full end-to-end PR review pipeline)

---

### 3.6 Running the Application

#### Start the FastAPI Webhook Gateway:
```bash
source .venv/bin/activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
Endpoints:
- Health check: `curl http://localhost:8000/health`
- Webhook receiver: `POST http://localhost:8000/webhook/github`
- Trigger run directly: `POST http://localhost:8000/api/v1/trigger`
- View run results: `GET http://localhost:8000/api/v1/runs/{analysis_id}`

#### Start the Background Priority Queue Worker:
```bash
source .venv/bin/activate
python3 src/worker/main.py
```
