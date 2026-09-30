# AI-Powered PR Assistant — Proposed Architecture v2

> **Purpose of this document**: This is the revised system architecture that (a) directly solves the three core product problems, and (b) addresses every bottleneck identified in the original `ai_pr_assistant_system_architecture.md`. Each architectural change is explained with a *why*.

---

## The Three Core Problems We Must Solve

| # | Problem | Root Cause | Proposed Solution |
|---|---------|-----------|-------------------|
| 1 | AI reviews the **wrong version** of a PR | No SHA-pinning at analysis start; new commits arrive mid-analysis | **Immutable SHA Contract** — analysis is locked to `(HEAD_SHA, BASE_SHA)` at enqueue time; freshness check before publish |
| 2 | **Multiple PRs** cannot be processed fairly or concurrently | Single sequential processor; no priority awareness | **Tiered Priority Queue + Autoscaling Worker Pool** — P0–P3 topic isolation in Kafka + HPA-driven workers |
| 3 | **AI findings cannot be trusted** — hallucinations, wrong line numbers, fake test passes | LLM output goes directly to comments with no verification | **Evidence Gate** — every finding must pass file+line verification; every test must run and pass in an isolated sandbox before publishing |

---

## Bottlenecks Fixed in This Proposal

| Original Bottleneck | Fix in v2 | Where |
|--------------------|-----------|-------|
| Cold full `git clone` per sandbox | **Shared Clone Cache** with shallow fetch; only `git fetch origin <SHA>` per run | `CLONE_CACHE` layer |
| Re-embedding unchanged files | **Cache-First Embedding** — hash check before pipeline; skip if cache hit | `EMBEDDING_PIPELINE` gate |
| Context Builder blocks on slowest SAST tool | **Parallel fan-out with per-tool timeout + partial proceed** | `CONTEXT_BUILDER` |
| Stale re-queue discards all intermediate artifacts | **Partial Artifact Salvage** — reuse valid cache artifacts on re-queue | `CACHE_REUSE` → `SALVAGE_GATE` |
| LangGraph agents dispatched sequentially | **True parallel agent dispatch** — all agents run concurrently via async LangGraph graph | `AGENT_ROUTER` |
| Test sandbox cold-start per run | **Pre-warmed Sandbox Pool** — containers kept alive, assigned per run | `SANDBOX_POOL` |
| Single Kafka cluster for all priorities | **Per-priority Kafka topic isolation** — P0 gets dedicated partition group | `QUEUE_LAYER` |
| PostgreSQL write contention (5 writers) | **Write path split** — hot state to Redis; durable state to Postgres via async write queue | `STORAGE` |
| No circuit breaker on LLM agents | **Agent Circuit Breaker** — timeout + degraded-mode fallback (static analysis only) | `AGENT_ROUTER` |
| MEMORY → REPO_INDEX thrashing | **Batched Index Update** — production feedback accumulated and applied in batches | `POST_MERGE` |

---

## Architecture Diagram (v2)

```mermaid
flowchart TB

subgraph GITHUB["GITHUB PLATFORM"]
    DEV["Developer"]

    subgraph ORG["GitHub Organization"]
        subgraph REPO_A["Repository A - Payment Service"]
            A_MAIN["main"]
            A_FEATURE["feature/*"]
            A_HOTFIX["hotfix/*"]
            A_RELEASE["release/*"]
        end

        subgraph REPO_B["Repository B - User Service"]
            B_MAIN["main"]
            B_FEATURE["feature/*"]
            B_HOTFIX["hotfix/*"]
        end

        subgraph REPO_N["Repository N"]
            N_MAIN["main / release"]
            N_FEATURE["feature/*"]
            N_HOTFIX["hotfix/*"]
        end
    end

    PR["Pull Requests"]
    WEBHOOK_EVENT["GitHub Webhook Events"]
    MERGE_QUEUE["GitHub Merge Queue"]
    MERGE_GROUP["Merge Group"]
    PROTECTED_MAIN["Protected Main / Release Branch"]
end

DEV --> A_FEATURE
DEV --> A_HOTFIX
DEV --> B_FEATURE
DEV --> B_HOTFIX
DEV --> N_FEATURE
DEV --> N_HOTFIX

A_FEATURE --> PR
A_HOTFIX --> PR
B_FEATURE --> PR
B_HOTFIX --> PR
N_FEATURE --> PR
N_HOTFIX --> PR

PR --> WEBHOOK_EVENT
MERGE_QUEUE --> MERGE_GROUP
MERGE_GROUP --> PROTECTED_MAIN

subgraph EVENT_LAYER["1. EVENT INGESTION + IMMUTABLE SHA CONTRACT"]
    WEBHOOK_RECEIVER["GitHub Webhook Receiver"]
    EVENT_PROCESSOR["Event Processor"]
    EVENT_ROUTER["Event Router"]
    IDEMPOTENCY["Idempotency Handler"]
    PR_STATE["PR State Manager"]
    EVENT_STORE["Event Store"]
    SHA_LOCK["SHA Contract Issuer - HEAD_SHA + BASE_SHA locked at enqueue"]
    SNAPSHOT["Immutable PR Snapshot - Locked to exact SHA pair"]
end

WEBHOOK_EVENT --> WEBHOOK_RECEIVER
WEBHOOK_RECEIVER --> EVENT_PROCESSOR
EVENT_PROCESSOR --> EVENT_ROUTER
EVENT_ROUTER --> IDEMPOTENCY
IDEMPOTENCY --> PR_STATE
PR_STATE --> EVENT_STORE
PR_STATE --> SHA_LOCK
SHA_LOCK --> SNAPSHOT

subgraph SNAPSHOT_DATA["PR SNAPSHOT - SHA LOCKED"]
    REPOSITORY_ID["Repository ID"]
    PR_NUMBER["PR Number"]
    BASE_SHA["Base SHA (locked at enqueue)"]
    HEAD_SHA["Head SHA (locked at enqueue)"]
    TARGET_BRANCH["Target Branch"]
    SOURCE_BRANCH["Source Branch"]
    CHANGED_FILES["Changed Files"]
    PRIORITY_LABEL["Priority / Labels"]
    ANALYSIS_ID["Analysis Run ID (UUID)"]
end

SNAPSHOT --> REPOSITORY_ID
SNAPSHOT --> PR_NUMBER
SNAPSHOT --> BASE_SHA
SNAPSHOT --> HEAD_SHA
SNAPSHOT --> TARGET_BRANCH
SNAPSHOT --> SOURCE_BRANCH
SNAPSHOT --> CHANGED_FILES
SNAPSHOT --> PRIORITY_LABEL
SNAPSHOT --> ANALYSIS_ID

subgraph CONTROL_PLANE["2. PR ORCHESTRATION CONTROL PLANE"]
    PRIORITY_ENGINE["Priority Engine"]
    DEPENDENCY_ENGINE["Dependency Engine"]
    FRESHNESS_ENGINE["Freshness Engine - Tracks live HEAD SHA from GitHub API"]
    POLICY_ENGINE["Repository Policy Engine"]
    CAPACITY_ENGINE["Capacity Manager - Reads worker pool headroom from Redis"]
    PR_SCHEDULER["Priority + Dependency Scheduler"]
end

SNAPSHOT --> PRIORITY_ENGINE
SNAPSHOT --> DEPENDENCY_ENGINE
SNAPSHOT --> FRESHNESS_ENGINE
SNAPSHOT --> POLICY_ENGINE
PRIORITY_ENGINE --> PR_SCHEDULER
DEPENDENCY_ENGINE --> PR_SCHEDULER
FRESHNESS_ENGINE --> PR_SCHEDULER
POLICY_ENGINE --> PR_SCHEDULER
CAPACITY_ENGINE --> PR_SCHEDULER

subgraph PRIORITY["PR PRIORITY TIERS"]
    P0["P0 - Emergency Hotfix"]
    P1["P1 - Security / Release"]
    P2["P2 - Normal Feature"]
    P3["P3 - Low Priority"]
end

PRIORITY_ENGINE --> P0
PRIORITY_ENGINE --> P1
PRIORITY_ENGINE --> P2
PRIORITY_ENGINE --> P3

subgraph DEPENDENCIES["PR DEPENDENCY GRAPH"]
    BRANCH_RELATION["Branch Relationships"]
    COMMIT_ANCESTRY["Commit Ancestry"]
    EXPLICIT_DEPENDENCY["Explicit PR Dependencies"]
    FILE_OVERLAP["Changed File Overlap"]
    MERGE_BASE["Merge Base"]
    DEP_GRAPH["PR Dependency Graph"]
end

DEPENDENCY_ENGINE --> BRANCH_RELATION
DEPENDENCY_ENGINE --> COMMIT_ANCESTRY
DEPENDENCY_ENGINE --> EXPLICIT_DEPENDENCY
DEPENDENCY_ENGINE --> FILE_OVERLAP
DEPENDENCY_ENGINE --> MERGE_BASE

BRANCH_RELATION --> DEP_GRAPH
COMMIT_ANCESTRY --> DEP_GRAPH
EXPLICIT_DEPENDENCY --> DEP_GRAPH
FILE_OVERLAP --> DEP_GRAPH
MERGE_BASE --> DEP_GRAPH

subgraph QUEUE_LAYER["3. TIERED PRIORITY QUEUE - Per-priority topic isolation"]
    KAFKA["Kafka / Redpanda"]
    TOPIC_P0["topic: pr-p0-hotfix - Dedicated partition group"]
    TOPIC_P1["topic: pr-p1-security"]
    TOPIC_P2["topic: pr-p2-normal"]
    TOPIC_P3["topic: pr-p3-low"]
    TOPIC_RETRY["topic: retry-analysis"]
    TOPIC_STALE["topic: stale-analysis"]
    TOPIC_MERGE["topic: merge-validation"]
end

PR_SCHEDULER --> KAFKA
KAFKA --> TOPIC_P0
KAFKA --> TOPIC_P1
KAFKA --> TOPIC_P2
KAFKA --> TOPIC_P3
KAFKA --> TOPIC_RETRY
KAFKA --> TOPIC_STALE
KAFKA --> TOPIC_MERGE

subgraph WORKERS["4. AUTOSCALING WORKER POOL - HPA-driven concurrency"]
    WORKER_POOL_P0["P0 Worker Pool - Always-on reserved capacity"]
    WORKER_POOL_P1["P1 Worker Pool"]
    WORKER_POOL_P2["P2/P3 Worker Pool - Scales 1..N via HPA"]
    WORKER_RETRY["Retry Worker"]
end

TOPIC_P0 --> WORKER_POOL_P0
TOPIC_P1 --> WORKER_POOL_P1
TOPIC_P2 --> WORKER_POOL_P2
TOPIC_P3 --> WORKER_POOL_P2
TOPIC_RETRY --> WORKER_RETRY

subgraph SANDBOX_POOL["ISOLATED EXECUTION - Pre-warmed pool (no cold start)"]
    POOL_MGR["Sandbox Pool Manager - Keeps N containers warm"]
    SANDBOX_1["Assigned Sandbox - PR #101 @ SHA A"]
    SANDBOX_2["Assigned Sandbox - PR #102 @ SHA B"]
    SANDBOX_3["Assigned Sandbox - PR #103 @ SHA C"]
    SANDBOX_N["Assigned Sandbox - PR #N @ SHA X"]
end

WORKER_POOL_P0 --> POOL_MGR
WORKER_POOL_P1 --> POOL_MGR
WORKER_POOL_P2 --> POOL_MGR
WORKER_RETRY --> POOL_MGR
POOL_MGR --> SANDBOX_1
POOL_MGR --> SANDBOX_2
POOL_MGR --> SANDBOX_3
POOL_MGR --> SANDBOX_N

subgraph GIT_ANALYSIS["5. IMMUTABLE GIT ANALYSIS - Shared clone cache"]
    CLONE_CACHE["Shared Clone Cache - git fetch origin SHA only"]
    CHECKOUT["Checkout Exact HEAD SHA"]
    RESOLVE_BASE["Resolve Exact BASE SHA"]
    DIFF_ENGINE["Deterministic PR Diff"]
    MERGE_BASE_ENGINE["Calculate Merge Base"]
    CHANGED_SYMBOLS["Changed Files + Symbols"]
    REPOSITORY_STATE["Repository State"]
end

SANDBOX_1 --> CLONE_CACHE
SANDBOX_2 --> CLONE_CACHE
SANDBOX_3 --> CLONE_CACHE
SANDBOX_N --> CLONE_CACHE
CLONE_CACHE --> CHECKOUT
CHECKOUT --> RESOLVE_BASE
RESOLVE_BASE --> DIFF_ENGINE
RESOLVE_BASE --> MERGE_BASE_ENGINE
DIFF_ENGINE --> CHANGED_SYMBOLS
CHECKOUT --> REPOSITORY_STATE

subgraph CODE_INTELLIGENCE["6. REPOSITORY INTELLIGENCE - Cache-first embedding"]
    AST["AST Parser / Tree-sitter"]
    SYMBOL_EXTRACTOR["Symbol Extractor"]
    DEPENDENCY_GRAPH["Code Dependency Graph"]
    REPO_INDEX["Incremental Repository Index"]
    FILE_HASH["File Hashing"]
    CACHE_GATE{"Cache Hit?"}
    EMBEDDING_PIPELINE["Embedding Pipeline - Only runs on cache miss"]
    VECTOR_DB["Vector Database - PostgreSQL + pgvector"]
    HYBRID_SEARCH["Hybrid Search"]
    RERANKER["Reranker"]
    CODE_CONTEXT["Code Context Builder"]
end

CHANGED_SYMBOLS --> AST
AST --> SYMBOL_EXTRACTOR
SYMBOL_EXTRACTOR --> DEPENDENCY_GRAPH
SYMBOL_EXTRACTOR --> REPO_INDEX
REPO_INDEX --> FILE_HASH
FILE_HASH --> CACHE_GATE
CACHE_GATE -->|MISS| EMBEDDING_PIPELINE
CACHE_GATE -->|HIT| VECTOR_DB
EMBEDDING_PIPELINE --> VECTOR_DB
VECTOR_DB --> HYBRID_SEARCH
DEPENDENCY_GRAPH --> HYBRID_SEARCH
HYBRID_SEARCH --> RERANKER
RERANKER --> CODE_CONTEXT

subgraph STATIC_ANALYSIS["7. DETERMINISTIC CODE ANALYSIS - Parallel + timeout-gated"]
    LINTER["Lint / Formatting - timeout: 30s"]
    TYPE_CHECKER["Type Checker - timeout: 60s"]
    SAST["SAST / Security Scanner - timeout: 120s"]
    DEP_SCAN["Dependency Vulnerability Scanner - timeout: 60s"]
    SECRET_SCAN["Secret Scanner - timeout: 30s"]
    TEST_DISCOVERY["Existing Test Discovery - timeout: 30s"]
    CODE_QUALITY["Code Quality Analysis - timeout: 60s"]
    PARTIAL_PROCEED["Partial Proceed Gate - Continue with available results if timeout"]
end

DIFF_ENGINE --> LINTER
DIFF_ENGINE --> TYPE_CHECKER
DIFF_ENGINE --> SAST
DIFF_ENGINE --> DEP_SCAN
DIFF_ENGINE --> SECRET_SCAN
DIFF_ENGINE --> TEST_DISCOVERY
DIFF_ENGINE --> CODE_QUALITY

LINTER --> PARTIAL_PROCEED
TYPE_CHECKER --> PARTIAL_PROCEED
SAST --> PARTIAL_PROCEED
DEP_SCAN --> PARTIAL_PROCEED
SECRET_SCAN --> PARTIAL_PROCEED
CODE_QUALITY --> PARTIAL_PROCEED

subgraph RAG["8. RAG CONTEXT ENGINE"]
    QUERY_BUILDER["Context Query Builder"]
    CODE_RETRIEVER["Code Retriever"]
    DOC_RETRIEVER["Documentation Retriever"]
    POLICY_RETRIEVER["Repository Policy Retriever"]
    RAG_RERANKER["RAG Reranker"]
    FINAL_CONTEXT["Grounded Analysis Context"]
end

CODE_CONTEXT --> QUERY_BUILDER
QUERY_BUILDER --> CODE_RETRIEVER
QUERY_BUILDER --> DOC_RETRIEVER
QUERY_BUILDER --> POLICY_RETRIEVER
CODE_RETRIEVER --> RAG_RERANKER
DOC_RETRIEVER --> RAG_RERANKER
POLICY_RETRIEVER --> RAG_RERANKER
RAG_RERANKER --> FINAL_CONTEXT

subgraph LANGGRAPH["9. LANGGRAPH AI ORCHESTRATION - Parallel agents + circuit breaker"]
    ANALYSIS_STATE["Shared Analysis State"]
    CONTEXT_BUILDER["Context Builder - Merges static + RAG results"]
    AGENT_ROUTER["Agent Router - Dispatches ALL agents in parallel (async)"]
    CIRCUIT_BREAKER["Agent Circuit Breaker - Timeout: 90s per agent - Fallback: static-analysis-only mode"]
    BUG_AGENT["Bug Detection Agent"]
    SECURITY_AGENT["Security Agent"]
    ARCHITECTURE_AGENT["Architecture Agent"]
    QUALITY_AGENT["Code Quality Agent"]
    TEST_AGENT["Test Generation Agent"]
    RAG_AGENT["Repository Context Agent"]
    AGENT_STATE["Agent State - Thread-safe concurrent writes"]
    RESULT_AGGREGATOR["Finding Aggregator"]
end

FINAL_CONTEXT --> CONTEXT_BUILDER
PARTIAL_PROCEED --> CONTEXT_BUILDER
TEST_DISCOVERY --> CONTEXT_BUILDER
CONTEXT_BUILDER --> ANALYSIS_STATE
ANALYSIS_STATE --> AGENT_ROUTER
AGENT_ROUTER --> CIRCUIT_BREAKER

CIRCUIT_BREAKER --> BUG_AGENT
CIRCUIT_BREAKER --> SECURITY_AGENT
CIRCUIT_BREAKER --> ARCHITECTURE_AGENT
CIRCUIT_BREAKER --> QUALITY_AGENT
CIRCUIT_BREAKER --> TEST_AGENT
CIRCUIT_BREAKER --> RAG_AGENT

BUG_AGENT --> AGENT_STATE
SECURITY_AGENT --> AGENT_STATE
ARCHITECTURE_AGENT --> AGENT_STATE
QUALITY_AGENT --> AGENT_STATE
TEST_AGENT --> AGENT_STATE
RAG_AGENT --> AGENT_STATE
AGENT_STATE --> RESULT_AGGREGATOR

subgraph TESTING["10. TEST GENERATION + VERIFIED SANDBOX EXECUTION"]
    GENERATED_TESTS["Generated Unit Tests"]
    TEST_SANDBOX["Pre-warmed Test Sandbox from SANDBOX_POOL"]
    TEST_RUNNER["Test Runner - Actual execution required"]
    COVERAGE["Coverage Analyzer"]
    TEST_RESULTS["Test Results - PASS/FAIL with stdout proof"]
    REGRESSION["Regression Detection"]
    TEST_EVIDENCE["Test Evidence Package - SHA + results + coverage linked"]
end

TEST_AGENT --> GENERATED_TESTS
GENERATED_TESTS --> TEST_SANDBOX
TEST_SANDBOX --> TEST_RUNNER
TEST_RUNNER --> COVERAGE
COVERAGE --> TEST_RESULTS
TEST_RESULTS --> REGRESSION
TEST_RESULTS --> TEST_EVIDENCE
REGRESSION --> RESULT_AGGREGATOR
TEST_EVIDENCE --> RESULT_AGGREGATOR

subgraph VALIDATION["11. FINDING VALIDATION + EVIDENCE GATE"]
    EVIDENCE_VALIDATOR["Evidence Validator - Every finding must cite real code"]
    LOCATION_VALIDATOR["File / Line / Symbol Verification - Cross-checked against REPOSITORY_STATE"]
    HALLUCINATION_FILTER["Hallucination Filter - Drop findings with unverifiable locations"]
    DEDUPLICATION["Finding Deduplication"]
    CONFIDENCE["Confidence Scoring"]
    SEVERITY["Severity Classification"]
    RISK_ENGINE["Risk Engine"]
    POLICY_CHECK["Policy Check"]
    FINAL_FINDINGS["Validated Findings - Only evidence-backed findings published"]
end

RESULT_AGGREGATOR --> EVIDENCE_VALIDATOR
EVIDENCE_VALIDATOR --> LOCATION_VALIDATOR
LOCATION_VALIDATOR --> HALLUCINATION_FILTER
HALLUCINATION_FILTER --> DEDUPLICATION
DEDUPLICATION --> CONFIDENCE
CONFIDENCE --> SEVERITY
SEVERITY --> RISK_ENGINE
RISK_ENGINE --> POLICY_CHECK
POLICY_CHECK --> FINAL_FINDINGS

subgraph CONCURRENCY["12. FRESHNESS CHECK - Final SHA comparison before publish"]
    CURRENT_HEAD["Fetch Current PR HEAD SHA from GitHub API"]
    CURRENT_BASE["Fetch Current BASE SHA"]
    SHA_COMPARE{"SHA matches Analysis Contract?"}
    VALID_ANALYSIS["VALID - Publish findings"]
    STALE_ANALYSIS["STALE - Discard + Salvage"]
    CANCEL_WORKERS["Cancel Remaining Workers"]
    SALVAGE_GATE["Salvage Gate - Reuse: AST, Embeddings, Dep Graph"]
    CREATE_NEW_RUN["Create New Analysis Run - New SHA Contract issued"]
end

FINAL_FINDINGS --> CURRENT_HEAD
CURRENT_HEAD --> CURRENT_BASE
CURRENT_BASE --> SHA_COMPARE
SHA_COMPARE -->|YES - SHA still matches| VALID_ANALYSIS
SHA_COMPARE -->|NO - PR updated mid-run| STALE_ANALYSIS
STALE_ANALYSIS --> CANCEL_WORKERS
CANCEL_WORKERS --> SALVAGE_GATE
SALVAGE_GATE --> CREATE_NEW_RUN
CREATE_NEW_RUN --> KAFKA

subgraph MERGE_READINESS["13. MERGE READINESS ENGINE"]
    REQUIRED_GATES{"All Required Gates Passed?"}
    BLOCKED["BLOCKED / WAITING"]
    MERGE_READY["MERGE READY"]
    PR_SUMMARY["Consolidated PR Summary - Findings + Test Evidence + Confidence"]
    PR_COMMENT["Post PR Comment"]
end

VALID_ANALYSIS --> REQUIRED_GATES
REQUIRED_GATES -->|NO| BLOCKED
REQUIRED_GATES -->|YES| MERGE_READY
MERGE_READY --> PR_SUMMARY
PR_SUMMARY --> PR_COMMENT
BLOCKED --> PR_SCHEDULER
MERGE_READY --> MERGE_QUEUE

subgraph MERGE_VALIDATION["14. FINAL MERGE GROUP VALIDATION"]
    MERGE_GROUP_EVENT["merge_group Event"]
    MERGE_GROUP_SHA["Merge Group SHA"]
    FINAL_CI["Final CI"]
    FINAL_AI["Final AI Validation - Pinned to Merge Group SHA"]
    FINAL_POLICY["Final Policy Validation"]
    FINAL_VALIDATION{"Merge Group Valid?"}
    REQUEUE_PR["Requeue / Reanalyze"]
    EXECUTE_MERGE["Merge"]
end

MERGE_QUEUE --> MERGE_GROUP_EVENT
MERGE_GROUP_EVENT --> MERGE_GROUP_SHA
MERGE_GROUP_SHA --> FINAL_CI
MERGE_GROUP_SHA --> FINAL_AI
MERGE_GROUP_SHA --> FINAL_POLICY
FINAL_CI --> FINAL_VALIDATION
FINAL_AI --> FINAL_VALIDATION
FINAL_POLICY --> FINAL_VALIDATION
FINAL_VALIDATION -->|NO| REQUEUE_PR
FINAL_VALIDATION -->|YES| EXECUTE_MERGE
REQUEUE_PR --> PR_SCHEDULER
EXECUTE_MERGE --> PROTECTED_MAIN

subgraph POST_MERGE["15. POST-MERGE - Batched feedback loop"]
    DEPLOYMENT["CI/CD Deployment"]
    PRODUCTION["Production"]
    FEEDBACK["Production Feedback"]
    FEEDBACK_BUFFER["Feedback Accumulation Buffer - Batch window: 5 min / 50 events"]
    MEMORY["Analysis Memory"]
end

PROTECTED_MAIN --> DEPLOYMENT
DEPLOYMENT --> PRODUCTION
PRODUCTION --> FEEDBACK
FEEDBACK --> FEEDBACK_BUFFER
FEEDBACK_BUFFER --> MEMORY
MEMORY --> REPO_INDEX

subgraph CACHE["16. ANALYSIS ARTIFACT CACHE - Salvageable on stale"]
    AST_CACHE["AST Cache"]
    EMBEDDING_CACHE["Embedding Cache"]
    TEST_CACHE["Test Cache"]
    STATIC_CACHE["Static Analysis Cache"]
    DEP_GRAPH_CACHE["Dependency Graph Cache"]
end

FILE_HASH --> AST_CACHE
FILE_HASH --> EMBEDDING_CACHE
FILE_HASH --> TEST_CACHE
FILE_HASH --> STATIC_CACHE
FILE_HASH --> DEP_GRAPH_CACHE

AST_CACHE --> SALVAGE_GATE
EMBEDDING_CACHE --> SALVAGE_GATE
TEST_CACHE --> SALVAGE_GATE
STATIC_CACHE --> SALVAGE_GATE
DEP_GRAPH_CACHE --> SALVAGE_GATE

AST_CACHE --> CACHE_GATE
EMBEDDING_CACHE --> CACHE_GATE

subgraph STORAGE["17. PLATFORM DATA LAYER - Write path split"]
    REDIS["Redis - Hot state: SHA contracts, scheduler state, capacity"]
    WRITE_QUEUE["Async Write Queue - Buffers Postgres writes"]
    POSTGRES["PostgreSQL - Durable: events, snapshots, findings"]
    OBJECT_STORE["Object Storage - Repository state, test evidence"]
    VECTOR["Vector Store - pgvector"]
end

PR_STATE --> REDIS
SHA_LOCK --> REDIS
PRIORITY_ENGINE --> REDIS
PR_SCHEDULER --> REDIS
CAPACITY_ENGINE --> REDIS
KAFKA --> REDIS

EVENT_STORE --> WRITE_QUEUE
SNAPSHOT --> WRITE_QUEUE
ANALYSIS_STATE --> WRITE_QUEUE
FINAL_FINDINGS --> WRITE_QUEUE
WRITE_QUEUE --> POSTGRES

REPOSITORY_STATE --> OBJECT_STORE
TEST_EVIDENCE --> OBJECT_STORE
VECTOR_DB --> VECTOR

subgraph OBSERVABILITY["18. OPENTELEMETRY OBSERVABILITY"]
    OTEL_SDK["OpenTelemetry SDK"]
    OTEL_COLLECTOR["OpenTelemetry Collector"]
    TEMPO["Grafana Tempo - Distributed Traces"]
    PROMETHEUS["Prometheus - Metrics"]
    LOKI["Grafana Loki - Logs"]
end

EVENT_PROCESSOR -.-> OTEL_SDK
PR_SCHEDULER -.-> OTEL_SDK
WORKER_POOL_P0 -.-> OTEL_SDK
WORKER_POOL_P1 -.-> OTEL_SDK
WORKER_POOL_P2 -.-> OTEL_SDK
CODE_CONTEXT -.-> OTEL_SDK
BUG_AGENT -.-> OTEL_SDK
SECURITY_AGENT -.-> OTEL_SDK
ARCHITECTURE_AGENT -.-> OTEL_SDK
QUALITY_AGENT -.-> OTEL_SDK
TEST_AGENT -.-> OTEL_SDK
TEST_RUNNER -.-> OTEL_SDK
EVIDENCE_VALIDATOR -.-> OTEL_SDK
HALLUCINATION_FILTER -.-> OTEL_SDK
CURRENT_HEAD -.-> OTEL_SDK
FINAL_CI -.-> OTEL_SDK
FINAL_AI -.-> OTEL_SDK
EXECUTE_MERGE -.-> OTEL_SDK
CIRCUIT_BREAKER -.-> OTEL_SDK
SALVAGE_GATE -.-> OTEL_SDK

OTEL_SDK --> OTEL_COLLECTOR
OTEL_COLLECTOR --> TEMPO
OTEL_COLLECTOR --> PROMETHEUS
OTEL_COLLECTOR --> LOKI

subgraph GRAFANA["19. GRAFANA - AI PR CONTROL TOWER"]
    REPOSITORY_DASHBOARD["Repository Overview"]
    PR_QUEUE_DASHBOARD["PR Priority Queue (P0-P3 split)"]
    DEPENDENCY_DASHBOARD["PR Dependency Graph"]
    ACTIVE_RUNS["Active Analysis Runs"]
    STALE_RUNS["Stale / Superseded Runs"]
    AGENT_TRACES["Agent Execution Traces"]
    MERGE_DASHBOARD["Merge Queue"]
    COST_DASHBOARD["LLM Token / Cost Usage"]
    LATENCY_DASHBOARD["Pipeline Latency (per stage)"]
    FAILURE_DASHBOARD["Failures / Bottlenecks"]
    WORKER_DASHBOARD["Worker Capacity (per tier)"]
    RAG_DASHBOARD["RAG Retrieval Metrics"]
    HALLUCINATION_DASHBOARD["Hallucination Filter Hit Rate"]
    SALVAGE_DASHBOARD["Cache Salvage Rate (stale runs)"]
    CIRCUIT_DASHBOARD["Circuit Breaker Events"]
end

TEMPO --> REPOSITORY_DASHBOARD
TEMPO --> AGENT_TRACES
TEMPO --> ACTIVE_RUNS
PROMETHEUS --> PR_QUEUE_DASHBOARD
PROMETHEUS --> LATENCY_DASHBOARD
PROMETHEUS --> WORKER_DASHBOARD
PROMETHEUS --> COST_DASHBOARD
LOKI --> FAILURE_DASHBOARD
LOKI --> STALE_RUNS
LOKI --> HALLUCINATION_DASHBOARD
LOKI --> SALVAGE_DASHBOARD
LOKI --> CIRCUIT_DASHBOARD
DEP_GRAPH --> DEPENDENCY_DASHBOARD
MERGE_QUEUE --> MERGE_DASHBOARD
RAG_RERANKER --> RAG_DASHBOARD

WEBHOOK_EVENT -. "PR synchronize - new SHA contract" .-> FRESHNESS_ENGINE
PROTECTED_MAIN -. "Base SHA changed" .-> FRESHNESS_ENGINE
P0 -. "Highest Priority - reserved worker pool" .-> PR_SCHEDULER
DEP_GRAPH -. "Dependency Constraint" .-> PR_SCHEDULER
HEAD_SHA -. "Immutable Analysis Identity" .-> CHECKOUT
MERGE_GROUP_SHA -. "Exact Merge State" .-> FINAL_AI
OTEL_COLLECTOR -. "Traces / Metrics / Logs" .-> GRAFANA
CIRCUIT_BREAKER -. "Degraded mode - static analysis only" .-> RESULT_AGGREGATOR
```

---

## Detailed Change Log — What Changed & Why

### Problem 1 — Correct PR Version

| Component Added / Changed | What It Does | Why |
|--------------------------|-------------|-----|
| **`SHA_LOCK` (SHA Contract Issuer)** | Records `HEAD_SHA + BASE_SHA` as an immutable contract UUID at the moment of enqueue | Without a contract locked at enqueue time, the analysis could silently drift to a newer commit mid-run. The UUID ties every artifact back to a specific snapshot. |
| **`ANALYSIS_ID` in Snapshot** | UUID per analysis run, not per PR | Multiple runs of the same PR (due to pushes) must be distinguishable. The run ID makes cache lookups, observability, and artifact storage unambiguous. |
| **`SHA_COMPARE` moved to "before publish"** | Checks live GitHub SHA against the contract only at the point of publishing findings | Checking mid-run is noisy and wasteful. Run to completion with locked SHA, then validate freshness before publishing. This avoids cancelling work that may still be valid. |
| **`SALVAGE_GATE` (replaces blank re-queue)** | On stale detection, reuses AST, embedding, and dep-graph cache artifacts before starting a new run | Original architecture discarded all work on staleness. Files unchanged between commits have identical hashes — their artifacts are reusable. |

---

### Problem 2 — Multiple Concurrent PRs

| Component Added / Changed | What It Does | Why |
|--------------------------|-------------|-----|
| **Per-priority Kafka topics** (`pr-p0-hotfix`, `pr-p1-security`, `pr-p2-normal`, `pr-p3-low`) | Isolates traffic per priority tier | Original had a single `pr-analysis` topic. A surge of P2 PRs could starve a P0 hotfix waiting in the same queue. Separate topics with separate consumer groups guarantee P0 is never blocked. |
| **`WORKER_POOL_P0` — always-on reserved capacity** | A dedicated, always-warm worker pool for P0 | Hotfixes cannot wait for autoscaling to spin up new workers. Reserved capacity ensures zero-queue-time for emergencies. |
| **`WORKER_POOL_P2` with HPA** | Scales from 1 to N based on queue depth | Normal PRs follow standard cloud-native autoscaling — no over-provisioning, no under-provisioning. |
| **`CAPACITY_ENGINE` reads from Redis** | Reports live worker headroom to the scheduler | Without real-time capacity awareness, the scheduler could over-enqueue and overwhelm workers. Redis gives the scheduler a live signal. |
| **`POOL_MGR` (Sandbox Pool Manager)** | Pre-warms containers and assigns them per run | Original design spun up an ephemeral container per run. Container cold-start (image pull + runtime init + dependency install) can take 30–90 seconds. A warm pool eliminates this from the critical path entirely. |
| **Parallel `AGENT_ROUTER` dispatch** | All 6 LangGraph agents run concurrently via async graph | Original diagram implied sequential dispatch. With 6 agents each taking 10–30s, sequential execution would add 60–180s to every PR. Parallel dispatch collapses this to the slowest single agent. |

---

### Problem 3 — Trusting AI Reviews

| Component Added / Changed | What It Does | Why |
|--------------------------|-------------|-----|
| **`HALLUCINATION_FILTER`** | Drops any finding whose file path, line number, or symbol cannot be verified against `REPOSITORY_STATE` | LLMs frequently hallucinate exact line numbers or reference files that don't exist. This filter is a hard gate — unverifiable findings are never published. |
| **`TEST_EVIDENCE` package** | Bundles the test run's SHA, actual stdout/stderr, pass/fail, and coverage into a signed evidence package | Prevents publishing "test passed" based solely on LLM claims. The evidence package is stored in Object Storage and linked to the PR comment. |
| **`TEST_SANDBOX` from `SANDBOX_POOL`** | Tests run in a real isolated container, not simulated | Without real execution, an LLM could claim any test passes. Only a real runner with real output proves a test works. |
| **`AGENT_CIRCUIT_BREAKER`** | Per-agent 90s timeout with fallback to static-analysis-only mode | If an LLM agent hangs or errors, the original architecture had no escape hatch. The circuit breaker ensures the pipeline always produces some output and prevents runaway LLM cost. |
| **`PR_SUMMARY` includes evidence links** | The published PR comment includes finding confidence scores and links to test evidence | Developers and reviewers can inspect *why* the AI flagged something, not just *what* it flagged. This builds trust incrementally. |

---

### Bottleneck Fixes (Architecture-Level)

| Bottleneck | Fix | Rationale |
|-----------|-----|-----------|
| Full `git clone` per sandbox | `CLONE_CACHE` with `git fetch origin <SHA>` | A full clone of a large monorepo can take minutes. Fetching only the required commits for a specific SHA pair is orders of magnitude faster. |
| Re-embedding unchanged files | `CACHE_GATE` decision node before `EMBEDDING_PIPELINE` | Embedding is expensive (latency + LLM token cost). A file-hash cache check is microseconds. Skip the pipeline on hit. |
| Context Builder blocks on SAST | Per-tool timeout + `PARTIAL_PROCEED` gate | SAST can take 120s+. The partial proceed gate continues with available results at timeout rather than holding up the entire LangGraph invocation. |
| PostgreSQL write contention | Hot state → Redis; durable state → `WRITE_QUEUE` → Postgres | The original design had 5 concurrent synchronous writers to Postgres. The async write queue serializes and batches writes, eliminating contention while keeping read-path consistency. |
| Production feedback thrashing REPO_INDEX | `FEEDBACK_BUFFER` with 5-min/50-event batch window | High-velocity repos could trigger continuous incremental index rebuilds. Batching amortizes the cost and prevents index lock contention. |
| New Grafana panels | `HALLUCINATION_DASHBOARD`, `SALVAGE_DASHBOARD`, `CIRCUIT_DASHBOARD` | The three new failure modes need dedicated dashboards so operators can tune thresholds in production. |

---

## Summary: Before vs After

```
PROBLEM 1 (Wrong Version):
  Before: Analysis could complete on stale code silently
  After:  SHA contract locked at enqueue -> freshness gate before publish -> salvage on stale

PROBLEM 2 (Concurrent PRs):
  Before: Single topic, ephemeral sandboxes, no capacity awareness
  After:  Per-priority topic isolation + always-on P0 pool + HPA workers + warm sandbox pool

PROBLEM 3 (AI Trust):
  Before: LLM findings published directly; test results not verified
  After:  Hallucination filter (file/line/symbol check) + real sandbox test execution
          + evidence package linked in PR comment + circuit breaker fallback

BOTTLENECKS:
  Clone:        Full clone per run  -> Shared clone cache (git fetch only)
  Embedding:    Always re-embed     -> Cache-gate, embed only on miss
  Context:      Blocks on SAST      -> Per-tool timeout + partial proceed
  Postgres:     5 sync writers      -> Redis hot path + async write queue
  Stale:        Discard all work    -> Salvage valid cache artifacts
  Agents:       Sequential LLM      -> Parallel async dispatch + circuit breaker
  Sandbox:      Cold start          -> Pre-warmed pool managed by Pool Manager
  Feedback:     Continuous index    -> Batched accumulation buffer
```
