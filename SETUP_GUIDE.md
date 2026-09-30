# AI-Powered PR Assistant — Setup & Deployment Guide

> **Living Document**: This guide is updated step-by-step during development on the current branch (`phase-1`). Every command here is designed to run seamlessly on both **macOS (local development)** and **Ubuntu 22.04 / 24.04 (AWS EC2 deployment)**.

---

## Target Environments
- **Local Machine**: macOS (Apple Silicon or Intel), Docker Desktop / OrbStack, Python 3.11+
- **AWS Cloud**: Ubuntu 22.04 / 24.04 LTS EC2 Instance, Docker Engine + Compose plugin, Python 3.11+

---

## Phase 1 Progress Tracker

- [ ] Step 1: AWS / Ubuntu setup & prerequisite scripts
- [ ] Step 2: Project repository & tooling configuration
- [ ] Step 3: Docker + Docker Compose (PostgreSQL, Redis, OTEL, Grafana)
- [ ] Step 4: PostgreSQL database schema & migrations
- [ ] Step 5: Redis broker & queues
- [ ] Step 6: FastAPI webhook ingestion gateway
- [ ] Step 7: GitHub App + Webhook integration
- [ ] Step 8: SHA Contract issuer & snapshot engine
- [ ] Step 9: Redis queue worker (consumer)
- [ ] Step 10: Exact git checkout & shared clone cache
- [ ] Step 11: Static analysis pipeline (Linters, SAST, Secrets)
- [ ] Step 12: pgvector & incremental repository RAG
- [ ] Step 13: LangGraph state machine orchestration
- [ ] Step 14: Code review agent (Bug, Security, Quality)
- [ ] Step 15: Unit test generation agent
- [ ] Step 16: Docker test sandbox execution
- [ ] Step 17: Evidence validation & hallucination filter
- [ ] Step 18: Freshness check gate (SHA verify before publish)
- [ ] Step 19: GitHub Check runs & markdown review comments
- [ ] Step 20: OpenTelemetry tracing, Prometheus & Grafana dashboard
- [ ] Step 21: End-to-end pipeline verification test

---

## Step 1: System Prerequisites & Provisioning

### A. Local Machine (macOS)
Verify or install:
```bash
# Verify Docker is running
docker --version
docker compose version

# Verify Python 3.11+
python3 --version

# Verify Git
git --version
```

### B. AWS Cloud (Ubuntu 22.04 / 24.04 LTS)
Run once upon spinning up the EC2 instance:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget jq python3 python3-pip python3-venv

# Install Docker Engine & Docker Compose Plugin
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Log out and log back in or run:
newgrp docker

# Verify Docker
docker --version
docker compose version
```

---

*(Additional steps will be appended dynamically as each step in Phase 1 is implemented.)*
