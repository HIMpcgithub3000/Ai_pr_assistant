# 🤖 AI-Powered Autonomous PR Assistant

> **A Production-Grade, Multi-Agent Pull Request Review & Verification Engine**  
> Engineered to eliminate review drift, concurrent PR starvation, and AI hallucinations through immutable SHA contracts, multi-tier priority scheduling, isolated Docker sandboxes, and physical evidence validation gates.

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [The 3 Core Engineering Problems Solved](#-the-3-core-engineering-problems-solved)
- [System Architecture](#-system-architecture)
- [DevOps & Engineering Breakdown](#-devops--engineering-breakdown)
  - [1. Ingress, Security & Idempotency Engine](#1-ingress-security--idempotency-engine)
  - [2. Immutable SHA Contract Engine](#2-immutable-sha-contract-engine)
  - [3. Tiered Priority Queue & Scheduling](#3-tiered-priority-queue--scheduling)
  - [4. Shared Git Clone Cache Layer](#4-shared-git-clone-cache-layer)
  - [5. Deterministic Static Analysis Suite](#5-deterministic-static-analysis-suite)
  - [6. pgvector Codebase RAG Retrieval](#6-pgvector-codebase-rag-retrieval)
  - [7. LangGraph Multi-Agent Orchestration](#7-langgraph-multi-agent-orchestration)
  - [8. Isolated Container Sandbox Runner](#8-isolated-container-sandbox-runner)
  - [9. Zero-Trust Physical Evidence Gate](#9-zero-trust-physical-evidence-gate)
  - [10. Pre-Publish Freshness Check Gate](#10-pre-publish-freshness-check-gate)
  - [11. GitHub PR Review Publisher](#11-github-pr-review-publisher)
  - [12. OpenTelemetry, Prometheus & Grafana Control Tower](#12-opentelemetry-prometheus--grafana-control-tower)
- [Technology Stack & Tooling Matrix](#-technology-stack--tooling-matrix)
- [Local & Cloud Deployment Guide](#-local--cloud-deployment-guide)
- [Live Production Verification](#-live-production-verification)
- [Roadmap & Development Stages](#-roadmap--development-stages)

---

## 🎯 Executive Overview

Modern continuous integration and AI-assisted code review pipelines suffer from three fatal flaws:
1. **Review Drift**: Reviewing superseded commits when developers push updates mid-analysis.
2. **Resource Starvation**: Massive routine PRs blocking critical production hotfixes.
3. **AI Hallucinations**: LLMs generating fabricated line numbers, non-existent files, or claiming tests passed without physical execution proof.

This project delivers a **production-hardened, event-driven PR assistant** designed with strict DevOps best practices. It runs a 21-step deterministic pipeline that ingests GitHub webhooks, locks exact commit SHAs, schedules tasks across isolated priority tiers, retrieves semantic repository context using vector embeddings, executes generated unit tests in isolated sandboxes, filters findings through physical code existence gates, and publishes cryptographically grounded markdown reviews directly to GitHub Pull Requests.

---

## 🛡️ The 3 Core Engineering Problems Solved

| # | Industry Bottleneck | Root Cause | Engineering Solution in This Architecture |
|:---:|---|---|---|
| **1** | **Wrong PR Version Review** | Developers push new commits while an analysis is in progress, causing the AI to post comments on stale code. | **Immutable SHA Contract**: The exact `(HEAD_SHA, BASE_SHA)` pair is locked into an immutable snapshot UUID upon ingestion. A pre-publish **Freshness Check Gate** validates against GitHub's live API before publishing; stale runs are gracefully discarded and cached artifacts salvaged. |
| **2** | **Concurrent PR Starvation** | Single FIFO queues block emergency patches behind large feature pull requests. | **Multi-Tier Priority Queue**: Redis-backed isolated queues (`P0 Hotfix` > `P1 Security` > `P2 Normal` > `P3 Low`) with non-blocking starvation-free scheduling and real-time worker capacity management. |
| **3** | **Untrusted AI Findings & Hallucinations** | LLMs hallucinate file paths, line ranges, or claim test suites passed without actually executing them. | **Dual Evidence Gate**: (1) **Physical Evidence Validator** verifies file path, line bounds, and AST symbol existence on disk before accepting any finding. (2) **Isolated Sandbox Runner** executes synthesized unit tests in an ephemeral container, capturing exit codes, raw `stdout`, and `stderr` as signed proof. |

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    %% Styling
    classDef intake fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef contract fill:#ede7f6,stroke:#512da8,stroke-width:2px;
    classDef worker fill:#fff3e0,stroke:#f57c00,stroke-width:2px;
    classDef ai fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef gate fill:#fce4ec,stroke:#c2185b,stroke-width:2px;
    classDef output fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;

    %% 1. Ingestion
    subgraph INGESTION["1. Webhook Ingestion & Ingress"]
        GH["GitHub PR Event<br/>(Opened / Synchronize)"] -->|POST Webhook| API["FastAPI Gateway (:8000)"]
        API -->|HMAC SHA-256 Verification| IDEM["Idempotency Filter<br/>(Delivery ID Deduplication)"]
    end
    class GH,API,IDEM intake;

    %% 2. SHA Contract & Queue
    subgraph CONTRACT_QUEUE["2. SHA Contract & Priority Queue"]
        IDEM -->|Lock HEAD_SHA + BASE_SHA| SHA["SHA Contract Issuer<br/>(Analysis UUID)"]
        SHA -->|Persist Snapshot| DB[("PostgreSQL 16 + Redis 7")]
        SHA -->|Enqueue by Priority| PQ{"Redis Priority Queue<br/>(P0 > P1 > P2 > P3)"}
    end
    class SHA,DB,PQ contract;

    %% 3. Worker & Context Preparation
    subgraph WORKER_STAGE["3. Worker & Repository Context"]
        PQ -->|Dequeue Job| WRK["PR Analysis Worker Daemon"]
        WRK -->|Authenticated Fetch| GIT["Shared Bare Git Cache<br/>(Named Commit Refs)"]
        GIT --> SA["Parallel Static Analysis<br/>(Ruff Lint, Bandit SAST, Secrets)"]
        GIT --> RAG["pgvector RAG Engine<br/>(Code Chunk Retrieval)"]
    end
    class WRK,GIT,SA,RAG worker;

    %% 4. AI Orchestration
    subgraph LANGGRAPH["4. LangGraph Multi-Agent Orchestration"]
        SA & RAG --> AGENTS["LangGraph State Machine"]
        AGENTS --> REV["Review Agents<br/>(Bug, Security, Quality)"]
        AGENTS --> TST["Test Generation Agent<br/>(Diff-Targeted Tests)"]
    end
    class AGENTS,REV,TST ai;

    %% 5. Verification & Gates
    subgraph GATES["5. Trust Verification & Execution Gates"]
        TST --> SBX["Isolated Docker Sandbox<br/>(pytest Execution -> stdout/stderr)"]
        REV --> EV["Physical Evidence Validator<br/>(File / Line / AST Check)"]
        EV -.->|Ungrounded Findings| DROP["Drop Hallucinations ❌"]
        
        SBX & EV --> FRESH{"Freshness Check Gate<br/>(Live GitHub HEAD SHA Compare)"}
    end
    class SBX,EV,DROP,FRESH gate;

    %% 6. Publishing
    subgraph PUBLISH["6. Publishing & Telemetry"]
        FRESH -->|STALE (Superseded)| SALVAGE["Mark STALE & Salvage Cache ♻️"]
        FRESH -->|FRESH (SHA Match)| PUB["GitHub PR Comment & Checks API"]
        PUB --> OBS["OpenTelemetry Collector (:4317)<br/>Prometheus (:9090) & Grafana (:3000)"]
    end
    class SALVAGE,PUB,OBS output;
```

---

## 🔧 DevOps & Engineering Breakdown

Every pipeline component is built with production reliability, zero-trust verification, and infrastructure scalability in mind:

### 1. Ingress, Security & Idempotency Engine
- **Framework**: FastAPI with asynchronous Uvicorn runtime.
- **HMAC Authentication**: Validates GitHub webhook payload integrity using `X-Hub-Signature-256` cryptographic signing.
- **Delivery Deduplication**: Persists `X-GitHub-Delivery` UUIDs into PostgreSQL; duplicate retries from GitHub are instantly acknowledged (`HTTP 200 OK`) and ignored without re-triggering analysis.

### 2. Immutable SHA Contract Engine
- **Module**: `src/services/sha_contract.py`
- **Mechanism**: Extracts `head.sha` and `base.sha` at ingestion time and binds them to a persistent `AnalysisRun` record with an immutable UUID.
- **Guarantee**: Every downstream process—from git checkout to static analysis, RAG embeddings, and test generation—references this explicit contract, making mid-flight commit drift impossible.

### 3. Tiered Priority Queue & Scheduling
- **Module**: `src/worker/queue.py`
- **Topology**: Four isolated Redis list queues (`pr_queue:P0`, `pr_queue:P1`, `pr_queue:P2`, `pr_queue:P3`).
- **Priority Routing**:
  - `P0`: Urgent hotfixes (labeled `hotfix`, `p0`, or critical incident branches). Zero queue wait.
  - `P1`: Security patches and vulnerability fixes.
  - `P2`: Default feature pull requests.
  - `P3`: Minor documentation, chore, and dependency bumps.
- **HPA Metric Emission**: Exposes `get_queue_metrics()` depths used by Kubernetes Horizontal Pod Autoscalers to scale workers dynamically based on queue depth.

### 4. Shared Git Clone Cache Layer
- **Module**: `src/services/git_manager.py`
- **Storage**: Bare mirror cache directory (`./cache/git/<org_repo>`).
- **Optimization**: Avoids performing full monorepo clones for each PR. Instead, performs a shallow fetch of only the required commits into the bare cache using explicit named refs:
  ```bash
  git fetch origin +<HEAD_SHA>:refs/commits/<HEAD_SHA>
  git fetch origin +<BASE_SHA>:refs/commits/<BASE_SHA>
  ```
- **Private Repository Support**: Transparently injects token authentication via `https://x-access-token:<GITHUB_TOKEN>@github.com/...`, supporting both Public and Private repositories across enterprise organizations.
- **Isolated Checkout**: Clones from local disk cache into a temporary run sandbox directory (`./sandboxes/run_<analysis_id>`) in milliseconds and computes deterministic diffs.

### 5. Deterministic Static Analysis Suite
- **Module**: `src/services/static_analysis.py`
- **Parallel Fan-out**: Dispatches static analysis tools concurrently across the changed files:
  - **Linter**: `Ruff` for Python syntax and code quality standards.
  - **SAST**: `Bandit` for common security vulnerabilities, insecure imports, and SQL injections.
  - **Secret Scanner**: High-entropy regex and pattern scanners detecting leaked API keys, tokens, and private keys.
- **Circuit Breaker Timeouts**: Each tool runs under an isolated subprocess with strict timeout guards (default: 30s), ensuring slow tools never block the PR pipeline.

### 6. pgvector Codebase RAG Retrieval
- **Module**: `src/services/rag_engine.py`
- **Vector Storage**: PostgreSQL 16 equipped with the `pgvector` extension.
- **Index & Retrieval**: Code chunks and diff symbols are converted into vector embeddings. The worker retrieves the top-$K$ nearest semantic neighbors to provide repository-wide context (e.g., related helper functions, types, schemas) to the review agents.

### 7. LangGraph Multi-Agent Orchestration
- **Module**: `src/agents/` (`graph.py`, `review_agent.py`, `test_agent.py`, `state.py`)
- **Architecture**: Asynchronous typed StateGraph state machine.
- **Specialized Agents**:
  - **Review Agents**: Concurrently analyze the diff for bug regressions, security vulnerabilities, performance anti-patterns, and architectural compliance.
  - **Test Generation Agent**: Synthesizes targeted unit test suites (e.g., `pytest`) specifically exercising changed lines and edge cases.
- **Circuit Breaker**: Degrades gracefully to static-analysis findings if LLM endpoints encounter rate limits or timeouts.

### 8. Isolated Container Sandbox Runner
- **Module**: `src/sandbox/runner.py`
- **Execution Environment**: Subprocess and isolated container environments with locked resource limits.
- **Deterministic Test Proof**: Executes the synthesized unit tests against the checked-out PR code. Captures:
  - Process exit code (`0` = pass, non-zero = fail)
  - Raw `stdout` output
  - Raw `stderr` traces
- **Persistence**: Bundles raw execution output into a `TestEvidence` record in PostgreSQL.

### 9. Zero-Trust Physical Evidence Gate
- **Module**: `src/services/evidence_validator.py`
- **Hallucination Filter**: Inspects every finding emitted by the AI models before it can reach publication.
- **Verification Rules**:
  1. **Physical File Existence**: File path must exist on disk in the checked-out repository.
  2. **Line Boundary Check**: Reported line number must be within the actual file length.
  3. **AST Symbol Verification**: Verified against the repository's syntax tree.
- **Drop Policy**: Any finding that fails verification is dropped with a logged rejection reason and emitted to telemetry (`hallucinations_dropped_total`).

### 10. Pre-Publish Freshness Check Gate
- **Module**: `src/services/freshness_checker.py`
- **Mechanism**: Immediately before publishing, queries GitHub's live API for the PR's current `head.sha`.
- **Decision Logic**:
  - **If Fresh**: Contract SHA matches live HEAD -> Proceeds to publish.
  - **If Stale**: Developer pushed new code while analysis was running -> Marks run `STALE`, skips comment publication, and flags intermediate AST and embedding artifacts for salvage.

### 11. GitHub PR Review Publisher
- **Module**: `src/services/github_client.py`
- **API Integration**: Connects via GitHub Personal Access Tokens or GitHub App private keys.
- **Publishing Channels**:
  - **PR Discussion Comments**: Formats and posts clean markdown review summaries containing validated findings, confidence ratings, and sandbox execution logs.
  - **Commit Checks**: Updates the GitHub Checks API (`check-runs`) with status and pass/fail conclusions.

### 12. OpenTelemetry, Prometheus & Grafana Control Tower
- **OpenTelemetry Collector**: Listens on `:4317` (gRPC) and `:4318` (HTTP), aggregating traces and metrics across FastAPI, workers, and LangGraph.
- **Prometheus Server**: Scrapes the collector every 5 seconds on port `:8889`, persisting time-series data for:
  - `pr_queue_depth{priority="P0|P1|P2|P3"}`
  - `pipeline_stage_duration_seconds`
  - `hallucinations_dropped_total`
  - `sandbox_test_runs_total`
- **Grafana Mission Control Dashboard**: Available on port `:3000` (`uid: pr-assistant-control-tower`), presenting live visual telemetry for queue depths, scrape latencies, container health, and worker capacity.

---

## 📊 Technology Stack & Tooling Matrix

| Layer | Technology | Version | Role in Architecture |
|---|---|---|---|
| **API Framework** | FastAPI / Starlette | 0.142+ | Webhook ingestion, HMAC verification, REST endpoints |
| **ASGI Server** | Uvicorn (uvloop) | 0.54+ | High-throughput asynchronous HTTP server |
| **Relational Database** | PostgreSQL | 16 | Event store, snapshot contracts, findings, test evidence |
| **Vector Database** | pgvector | 0.5.0 | High-dimensional embedding storage & hybrid similarity search |
| **Broker & State Store** | Redis | 7-alpine | Tiered priority queue broker, worker locks, capacity counters |
| **Agent Framework** | LangGraph / LangChain | 1.2+ / 1.4+ | Async multi-agent state machine and prompt routing |
| **Static Linters & SAST** | Ruff / Bandit | 0.16+ / 1.8+ | Deterministic static analysis, code linting, security scanning |
| **Test Runner** | pytest / pytest-asyncio | 9.1+ / 1.4+ | Isolated test execution in sandboxes |
| **ORM & Database Driver** | SQLAlchemy / asyncpg | 2.1+ / 0.31+ | Asynchronous database access and connection pooling |
| **Telemetry Collector** | OpenTelemetry Collector Contrib | 0.109.0 | Central telemetry pipeline for traces and metrics |
| **Metrics Engine** | Prometheus | 2.54.1 | Time-series metrics collection and PromQL querying |
| **Visualization** | Grafana | 11.2.0 | Mission Control operational dashboards and alerting |
| **Containerization** | Docker & Docker Compose | 29.8+ / 5.6+ | Multi-service local and cloud container orchestration |
| **CLI & Runtime** | Antigravity CLI (`agy`) | 1.2.17 | Agent orchestration and command-line execution |

---

## 🚀 Local & Cloud Deployment Guide

This project strictly adheres to the **Dual-Compatibility Standard**: 100% identical operation across macOS and Ubuntu x86_64 / arm64.

### 1. Prerequisites
- Docker & Docker Compose
- Python 3.11+ (Python 3.14 compatible)
- Git 2.40+

### 2. Environment Configuration
Clone the repository and copy the environment template:
```bash
git clone https://github.com/HIMpcgithub3000/Ai_pr_assistant.git
cd Ai_pr_assistant
cp .env.example .env
```
Configure your `.env`:
```ini
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=development_webhook_secret_12345
POSTGRES_PORT=5433
REDIS_PORT=6379
```

### 3. Start Container Infrastructure
Spin up PostgreSQL (with pgvector), Redis, OTel Collector, Prometheus, and Grafana:
```bash
docker compose up -d
docker compose ps
```

### 4. Setup Python Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Initialize Database Schema
```bash
python3 -c "import asyncio; from src.db.session import init_db; asyncio.run(init_db()); print('Database Initialized!')"
```

### 6. Run Automated Test Suite
```bash
pytest -v
```
*Expected output: `4 passed in ~10s` (covering SHA contract, priority queue, evidence validator, and end-to-end pipeline).*

### 7. Start Services
In separate terminal sessions (or via background daemons):
```bash
# Terminal 1: Webhook API Gateway
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Priority Queue Worker Daemon
PYTHONUNBUFFERED=1 python3 -u -m src.worker.main
```

### 8. Access Dashboards
- **Grafana Mission Control**: `http://localhost:3000` (Default credentials: `admin` / `admin` or custom)
- **Prometheus Web UI**: `http://localhost:9090`
- **FastAPI OpenAPI Swagger**: `http://localhost:8000/docs`

---

## 🏆 Live Production Verification

The complete Phase 1 pipeline was deployed and verified on an **AWS EC2 Ubuntu 26.04 LTS instance (`13.207.68.8`)** integrated with a real private GitHub repository:

- **Target Repository**: `HIMpcgithub3000/Airbnb-clone` (Private)
- **Target Pull Request**: PR #1 (`feat(search): add Indian cities destination search in header search bar`)
- **Verification Milestones**:
  - ✅ Webhook delivered from GitHub and verified via HMAC-SHA256 signature.
  - ✅ Issued immutable SHA contract (`Analysis ID: cb5029cb-9860-445e-8896-da0b939dde76`).
  - ✅ Enqueued and scheduled through Redis `pr_queue:P2`.
  - ✅ Authenticated shallow git fetch of commit `67f24c2` and base `28b8d65` via token.
  - ✅ Parallel static analysis executed without timeouts.
  - ✅ Sandbox test execution passed with exit code `0` (`test_generated_suite.py`).
  - ✅ Evidence validator verified file paths and line ranges on disk.
  - ✅ Published formatted review summary directly to GitHub PR discussion thread (**Comment ID: `6021075382`**).

---

## 🗺️ Roadmap & Development Stages

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: Core Engine & Reliability Foundation (COMPLETED)   │
│ ✅ 21-Step Pipeline, SHA Contracts, Evidence Gate, Grafana  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: Distributed Scaling & Performance (UPCOMING)       │
│ ⏳ Kafka Per-Tier Topics, Warm Sandbox Pool, Async Writers   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ STAGE 3: Merge Queue Speculation & Closed-Loop Learning     │
│ ⏳ Merge Group Re-Analysis, Human Feedback RAG Buffer        │
└─────────────────────────────────────────────────────────────┘
```

- **Stage 1 (Completed ✅)**: Complete 21-step pipeline, SHA contracts, priority queue, clone cache, deterministic static analysis, pgvector RAG, LangGraph agents, test sandboxes, evidence validation gate, and Grafana dashboard.
- **Stage 2 (Next ⏳)**: Distributed Kafka priority topic partitioning, pre-warmed sandbox pool manager (`POOL_MGR`), async write queue buffer for PostgreSQL, partial artifact salvage gate (`SALVAGE_GATE`), and agent circuit breakers.
- **Stage 3 (Future ⏳)**: Speculative GitHub Merge Queue analysis (`MERGE_GROUP_SHA`), batched repository re-indexing, and closed-loop learning from human reviewer accept/reject decisions stored in vector memory.

---

## 📄 License
This project is licensed under the Apache 2.0 License.
