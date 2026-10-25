# AI-Powered PR Assistant — Setup & Deployment Guide

> **Tested & Validated Local & AWS Cloud Setup Guide**  
> Branch: `phase-2`  
> Status: **Stage 2 (Distributed Scaling & Performance) Implementation Active & Verified**

---

## 1. System Requirements

| Environment | OS / Specs | Runtimes & Services |
|:---|:---|:---|
| **Local Development** | macOS (Apple Silicon / Intel) | Docker Desktop / OrbStack, Python 3.11+, Git |
| **AWS Cloud** | Ubuntu 22.04 / 24.04 LTS (EC2: `13.201.6.39`) | Docker Engine + Compose plugin, Python 3.11+, Git |

---

## 2. Phase Implementation Trackers

### Phase 1: Core Engine & Reliability (All 21 Steps Complete ✅)
- [x] Steps 1–21 (SHA Contract, Redis Queue, Shared Clone Cache, Static Analysis, RAG, LangGraph, Docker Sandbox, Evidence Filter, Freshness Check, Grafana).

### Phase 2: Distributed Scaling & Performance Optimization (Active & Tested ✅)
- [x] **Pre-Warmed Sandbox Pool (`POOL_MGR`)**: `src/sandbox/pool.py` sub-second runner leasing with reset scrubbing.
- [x] **Partial Artifact Salvage Gate (`SALVAGE_GATE`)**: `src/services/salvage_gate.py` unchanged file AST/embedding reuse.
- [x] **Split Write Path & Async Write Queue**: `src/db/write_queue.py` micro-batched persistence to eliminate DB lock contention.
- [x] **Agent Circuit Breakers**: `src/agents/circuit_breaker.py` 90s timeout guards and degraded static-analysis fallback.
- [x] **Dynamic Capacity Manager & Starvation Aging**: `src/worker/capacity.py` live worker heartbeat headroom & P2/P3 aging promotion.
- [x] **Multi-Topic Queue Partitioning**: `src/worker/kafka_queue.py` topic isolation (`pr-p0-hotfix`, `pr-p1-security`, `pr-p2-normal`, `pr-p3-low`).
- [x] **Stage 2 Automated Test Suite**: `tests/test_stage2_components.py` (9/9 tests passing on AWS EC2).

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
