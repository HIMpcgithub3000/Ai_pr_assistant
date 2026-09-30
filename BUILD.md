# AI-Powered PR Assistant — Build & Execution Rules

> **Core Mandate**: We develop this project **locally first**, ensuring **100% AWS/Ubuntu compatibility** from day one. Once Phase 1 local development and verification are complete, the code will be pushed to GitHub (`main` + `phase-1` branch) and transitioned to the AWS Ubuntu EC2 instance via the Antigravity (`agy`) CLI.

---

## 1. Operating Model & Workflow Strategy

### 1.1 Local-to-AWS Dual Compatibility Rule
- **No macOS-only hardcoding**: Never use Darwin/macOS-specific paths, binaries, or brew-dependent scripts in application code or deployment scripts.
- **Docker-First Environment**: All external dependencies (PostgreSQL + pgvector, Redis, OpenTelemetry Collector, Prometheus, Grafana, Sandbox environments) run in containerized setups using Docker Compose.
- **Architecture Agnostic**: Containers and scripts must run cleanly on both local machine (`macOS`) and target cloud (`Ubuntu x86_64/arm64`).
- **Living Setup Guide Requirement**: Each phase maintains an updated, step-by-step setup and installation guide (e.g., [SETUP_GUIDE.md](file:///Users/himanshusharma/devops_idt_project/SETUP_GUIDE.md)). This file is updated continuously step-by-step on the current development branch until the phase closes and switches to the next branch.

### 1.2 Git & Branching Strategy
1. **Repository Initialization**: Initialize git, commit foundational architecture, build rules, and docker setup.
2. **`main` Branch**: Contains stable, reviewed milestones.
3. **`phase-1` Branch**: The active development branch for the entire 21-step Phase 1 rollout.
4. **Handoff to AWS**:
   - Push completed Phase 1 code to GitHub `main` and branch `phase-1`.
   - On the AWS Ubuntu instance, clone/pull the `phase-1` branch.
   - User logs in via `agy` CLI on AWS instance to verify and run the workload in the cloud.

---

## 2. Phase 1 Implementation Roadmap (21 Steps)

```
1. AWS / Ubuntu Setup & Environment Spec
       ↓
2. Project Repository Structure & Tooling
       ↓
3. Docker + Docker Compose Base Services
       ↓
4. PostgreSQL Database Schema & Migrations
       ↓
5. Redis Broker & State Store
       ↓
6. FastAPI Ingestion & API Gateway Service
       ↓
7. GitHub App Integration & Webhook Handling
       ↓
8. SHA Contract Issuer & Immutable Snapshot Engine
       ↓
9. Redis / Distributed Queue Worker (Analysis Consumer)
       ↓
10. Exact Git Checkout & Shared Clone Cache Layer
       ↓
11. Deterministic Static Analysis Suite (Lint, SAST, Secrets)
       ↓
12. pgvector Setup & Incremental Codebase RAG
       ↓
13. LangGraph Orchestration State Machine
       ↓
14. Multi-Agent Code Review (Bug, Security, Quality)
       ↓
15. Test Generation Agent
       ↓
16. Docker Test Sandbox Execution Engine (Isolated Container Runner)
       ↓
17. Evidence Validation & Hallucination Filter (File/Line/Symbol Proof)
       ↓
18. Freshness Check Gate (Head/Base SHA Verification)
       ↓
19. GitHub Status Checks, PR Summary & Inline Comments
       ↓
20. OpenTelemetry Instrumentation, Prometheus & Grafana Control Tower
       ↓
21. End-to-End System Testing & Validation
```

---

## 3. Step-by-Step Execution Plan for Phase 1

| Step | Component | Key Deliverables & AWS Compatibility Focus |
|:---|:---|:---|
| **1** | **AWS / Ubuntu Setup** | Base requirements definition, system packages (`git`, `docker`, `docker-compose`, `python3.11+`, `curl`, `jq`). |
| **2** | **Project Repository** | Directory structure, pyproject/poetry/uv configuration, linting (`ruff`, `mypy`), environment templates. |
| **3** | **Docker + Docker Compose** | Multi-service `docker-compose.yml` for Postgres (with pgvector), Redis, Otel Collector, Grafana. |
| **4** | **PostgreSQL** | Schema for events, snapshots, analysis runs, findings, and evidence tables. |
| **5** | **Redis** | In-memory queues, worker lease locks, SHA contract state, and capacity counters. |
| **6** | **FastAPI** | REST API for webhook ingestion, health checks, manual trigger endpoints. |
| **7** | **GitHub App + Webhook** | Webhook signature verification (`X-Hub-Signature-256`), event parsing for `pull_request` and `push`. |
| **8** | **SHA Contract** | Locking `(HEAD_SHA, BASE_SHA)` with unique `analysis_id` upon webhook ingestion. |
| **9** | **Redis Worker** | Background queue consumer picking up analysis jobs per priority. |
| **10** | **Exact Git Checkout** | Shared clone cache implementation fetching specific commit SHAs safely in worker space. |
| **11** | **Static Analysis** | Parallel runners with timeouts for linters, SAST tools, secret scanning. |
| **12** | **pgvector + RAG** | Embedding storage, similarity search, code chunking, and repository context building. |
| **13** | **LangGraph** | StateGraph with async parallel nodes, typed states, and circuit breaker timeout logic. |
| **14** | **Code Review Agent** | Specialized sub-graphs for bug detection, security, and architectural review. |
| **15** | **Test Agent** | AI agent synthesizing unit tests targeted at the diff and changed symbols. |
| **16** | **Docker Test Sandbox** | Container-in-Docker / isolated runner executing generated test suites and capturing raw stdout/stderr. |
| **17** | **Evidence Validation** | Verification that reported file, line numbers, and symbols physically exist before publishing. |
| **18** | **Freshness Check** | Pre-publish verification against live GitHub API to discard stale superseded runs gracefully. |
| **19** | **GitHub Checks & Comments**| Updating GitHub Checks API status and posting formatted markdown PR reviews with evidence links. |
| **20** | **OpenTelemetry + Grafana**| Distributed tracing across FastAPI, workers, and LangGraph; Grafana dashboard configs. |
| **21** | **End-to-End Testing** | Automated end-to-end integration test running a dummy PR through the complete pipeline. |

---

## 4. Phase-by-Phase Setup Guide Maintenance Rule

- In every phase, an active [SETUP_GUIDE.md](file:///Users/himanshusharma/devops_idt_project/SETUP_GUIDE.md) must reside at the workspace root.
- Whenever a new component or dependency is added in the branch, [SETUP_GUIDE.md](file:///Users/himanshusharma/devops_idt_project/SETUP_GUIDE.md) must be updated immediately with:
  - Exact command lines to execute locally.
  - Exact command lines to execute on AWS Ubuntu.
  - Required environment variables (`.env.example`).
  - Verification test commands.
- No branch is closed or merged until [SETUP_GUIDE.md](file:///Users/himanshusharma/devops_idt_project/SETUP_GUIDE.md) has been tested and verified to work cleanly from scratch on Ubuntu.
