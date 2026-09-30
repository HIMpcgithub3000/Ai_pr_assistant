# AI-Powered PR Assistant --- Production System Architecture

This document contains the complete Mermaid source code for the
production architecture of the AI-powered Pull Request Assistant.

## Architecture Diagram

``` mermaid
flowchart TB

%% ============================================================
%% AI-POWERED PR ASSISTANT - PRODUCTION SYSTEM ARCHITECTURE
%% ============================================================

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

subgraph EVENT_LAYER["1. EVENT INGESTION & STATE MANAGEMENT"]
    WEBHOOK_RECEIVER["GitHub Webhook Receiver"]
    EVENT_PROCESSOR["Event Processor"]
    EVENT_ROUTER["Event Router"]
    IDEMPOTENCY["Idempotency Handler"]
    PR_STATE["PR State Manager"]
    EVENT_STORE["Event Store"]
    SNAPSHOT["Immutable PR Snapshot"]
end

WEBHOOK_EVENT --> WEBHOOK_RECEIVER
WEBHOOK_RECEIVER --> EVENT_PROCESSOR
EVENT_PROCESSOR --> EVENT_ROUTER
EVENT_ROUTER --> IDEMPOTENCY
IDEMPOTENCY --> PR_STATE
PR_STATE --> EVENT_STORE
PR_STATE --> SNAPSHOT

subgraph SNAPSHOT_DATA["PR SNAPSHOT"]
    REPOSITORY_ID["Repository ID"]
    PR_NUMBER["PR Number"]
    BASE_SHA["Base SHA"]
    HEAD_SHA["Head SHA"]
    TARGET_BRANCH["Target Branch"]
    SOURCE_BRANCH["Source Branch"]
    CHANGED_FILES["Changed Files"]
    PRIORITY_LABEL["Priority / Labels"]
end

SNAPSHOT --> REPOSITORY_ID
SNAPSHOT --> PR_NUMBER
SNAPSHOT --> BASE_SHA
SNAPSHOT --> HEAD_SHA
SNAPSHOT --> TARGET_BRANCH
SNAPSHOT --> SOURCE_BRANCH
SNAPSHOT --> CHANGED_FILES
SNAPSHOT --> PRIORITY_LABEL

subgraph CONTROL_PLANE["2. PR ORCHESTRATION CONTROL PLANE"]
    PRIORITY_ENGINE["Priority Engine"]
    DEPENDENCY_ENGINE["Dependency Engine"]
    FRESHNESS_ENGINE["Freshness Engine"]
    POLICY_ENGINE["Repository Policy Engine"]
    CAPACITY_ENGINE["Capacity Manager"]
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

subgraph PRIORITY["PR PRIORITY"]
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

subgraph QUEUE_LAYER["3. DISTRIBUTED ANALYSIS QUEUE"]
    KAFKA["Kafka / Redpanda"]
    TOPIC_PR["pr-analysis"]
    TOPIC_PRIORITY["priority-analysis"]
    TOPIC_RETRY["retry-analysis"]
    TOPIC_STALE["stale-analysis"]
    TOPIC_MERGE["merge-validation"]
end

PR_SCHEDULER --> KAFKA
KAFKA --> TOPIC_PR
KAFKA --> TOPIC_PRIORITY
KAFKA --> TOPIC_RETRY
KAFKA --> TOPIC_STALE
KAFKA --> TOPIC_MERGE

subgraph WORKERS["4. DISTRIBUTED ANALYSIS WORKERS"]
    WORKER_1["Analysis Worker 1"]
    WORKER_2["Analysis Worker 2"]
    WORKER_3["Analysis Worker 3"]
    WORKER_N["Analysis Worker N"]
end

TOPIC_PR --> WORKER_1
TOPIC_PRIORITY --> WORKER_2
TOPIC_RETRY --> WORKER_3
TOPIC_PR --> WORKER_N

subgraph SANDBOX_LAYER["ISOLATED EXECUTION"]
    SANDBOX_1["Ephemeral Sandbox<br/>PR #101 @ SHA A"]
    SANDBOX_2["Ephemeral Sandbox<br/>PR #102 @ SHA B"]
    SANDBOX_3["Ephemeral Sandbox<br/>PR #103 @ SHA C"]
    SANDBOX_N["Ephemeral Sandbox<br/>PR #N @ SHA X"]
end

WORKER_1 --> SANDBOX_1
WORKER_2 --> SANDBOX_2
WORKER_3 --> SANDBOX_3
WORKER_N --> SANDBOX_N

subgraph GIT_ANALYSIS["5. IMMUTABLE GIT ANALYSIS"]
    CLONE["Clone Repository"]
    CHECKOUT["Checkout Exact HEAD SHA"]
    RESOLVE_BASE["Resolve Exact BASE SHA"]
    DIFF_ENGINE["Deterministic PR Diff"]
    MERGE_BASE_ENGINE["Calculate Merge Base"]
    CHANGED_SYMBOLS["Changed Files + Symbols"]
    REPOSITORY_STATE["Repository State"]
end

SANDBOX_1 --> CLONE
SANDBOX_2 --> CLONE
SANDBOX_3 --> CLONE
SANDBOX_N --> CLONE
CLONE --> CHECKOUT
CHECKOUT --> RESOLVE_BASE
RESOLVE_BASE --> DIFF_ENGINE
RESOLVE_BASE --> MERGE_BASE_ENGINE
DIFF_ENGINE --> CHANGED_SYMBOLS
CHECKOUT --> REPOSITORY_STATE

subgraph CODE_INTELLIGENCE["6. REPOSITORY INTELLIGENCE"]
    AST["AST Parser / Tree-sitter"]
    SYMBOL_EXTRACTOR["Symbol Extractor"]
    DEPENDENCY_GRAPH["Code Dependency Graph"]
    REPO_INDEX["Incremental Repository Index"]
    FILE_HASH["File Hashing"]
    EMBEDDING_PIPELINE["Embedding Pipeline"]
    VECTOR_DB["Vector Database<br/>PostgreSQL + pgvector"]
    HYBRID_SEARCH["Hybrid Search"]
    RERANKER["Reranker"]
    CODE_CONTEXT["Code Context Builder"]
end

CHANGED_SYMBOLS --> AST
AST --> SYMBOL_EXTRACTOR
SYMBOL_EXTRACTOR --> DEPENDENCY_GRAPH
SYMBOL_EXTRACTOR --> REPO_INDEX
REPO_INDEX --> FILE_HASH
REPO_INDEX --> EMBEDDING_PIPELINE
EMBEDDING_PIPELINE --> VECTOR_DB
VECTOR_DB --> HYBRID_SEARCH
DEPENDENCY_GRAPH --> HYBRID_SEARCH
HYBRID_SEARCH --> RERANKER
RERANKER --> CODE_CONTEXT

subgraph STATIC_ANALYSIS["7. DETERMINISTIC CODE ANALYSIS"]
    LINTER["Lint / Formatting"]
    TYPE_CHECKER["Type Checker"]
    SAST["SAST / Security Scanner"]
    DEP_SCAN["Dependency Vulnerability Scanner"]
    SECRET_SCAN["Secret Scanner"]
    TEST_DISCOVERY["Existing Test Discovery"]
    CODE_QUALITY["Code Quality Analysis"]
end

DIFF_ENGINE --> LINTER
DIFF_ENGINE --> TYPE_CHECKER
DIFF_ENGINE --> SAST
DIFF_ENGINE --> DEP_SCAN
DIFF_ENGINE --> SECRET_SCAN
DIFF_ENGINE --> TEST_DISCOVERY
DIFF_ENGINE --> CODE_QUALITY

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

subgraph LANGGRAPH["9. LANGGRAPH AI ORCHESTRATION"]
    ANALYSIS_STATE["Shared Analysis State"]
    CONTEXT_BUILDER["Context Builder"]
    AGENT_ROUTER["Agent Router"]
    BUG_AGENT["Bug Detection Agent"]
    SECURITY_AGENT["Security Agent"]
    ARCHITECTURE_AGENT["Architecture Agent"]
    QUALITY_AGENT["Code Quality Agent"]
    TEST_AGENT["Test Generation Agent"]
    RAG_AGENT["Repository Context Agent"]
    AGENT_STATE["Agent State"]
    RESULT_AGGREGATOR["Finding Aggregator"]
end

FINAL_CONTEXT --> CONTEXT_BUILDER
LINTER --> CONTEXT_BUILDER
TYPE_CHECKER --> CONTEXT_BUILDER
SAST --> CONTEXT_BUILDER
DEP_SCAN --> CONTEXT_BUILDER
SECRET_SCAN --> CONTEXT_BUILDER
CODE_QUALITY --> CONTEXT_BUILDER
CONTEXT_BUILDER --> ANALYSIS_STATE
ANALYSIS_STATE --> AGENT_ROUTER

AGENT_ROUTER --> BUG_AGENT
AGENT_ROUTER --> SECURITY_AGENT
AGENT_ROUTER --> ARCHITECTURE_AGENT
AGENT_ROUTER --> QUALITY_AGENT
AGENT_ROUTER --> TEST_AGENT
AGENT_ROUTER --> RAG_AGENT

BUG_AGENT --> AGENT_STATE
SECURITY_AGENT --> AGENT_STATE
ARCHITECTURE_AGENT --> AGENT_STATE
QUALITY_AGENT --> AGENT_STATE
TEST_AGENT --> AGENT_STATE
RAG_AGENT --> AGENT_STATE
AGENT_STATE --> RESULT_AGGREGATOR

subgraph TESTING["10. TEST GENERATION & EXECUTION"]
    GENERATED_TESTS["Generated Unit Tests"]
    TEST_SANDBOX["Isolated Test Sandbox"]
    TEST_RUNNER["Test Runner"]
    COVERAGE["Coverage Analyzer"]
    TEST_RESULTS["Test Results"]
    REGRESSION["Regression Detection"]
end

TEST_AGENT --> GENERATED_TESTS
GENERATED_TESTS --> TEST_SANDBOX
TEST_SANDBOX --> TEST_RUNNER
TEST_RUNNER --> COVERAGE
COVERAGE --> TEST_RESULTS
TEST_RESULTS --> REGRESSION
REGRESSION --> RESULT_AGGREGATOR

subgraph VALIDATION["11. FINDING VALIDATION & RISK ENGINE"]
    EVIDENCE_VALIDATOR["Evidence Validator"]
    LOCATION_VALIDATOR["File / Line / Symbol Verification"]
    DEDUPLICATION["Finding Deduplication"]
    CONFIDENCE["Confidence Scoring"]
    SEVERITY["Severity Classification"]
    RISK_ENGINE["Risk Engine"]
    POLICY_CHECK["Policy Check"]
    FINAL_FINDINGS["Validated Findings"]
end

RESULT_AGGREGATOR --> EVIDENCE_VALIDATOR
EVIDENCE_VALIDATOR --> LOCATION_VALIDATOR
LOCATION_VALIDATOR --> DEDUPLICATION
DEDUPLICATION --> CONFIDENCE
CONFIDENCE --> SEVERITY
SEVERITY --> RISK_ENGINE
RISK_ENGINE --> POLICY_CHECK
POLICY_CHECK --> FINAL_FINDINGS

subgraph CONCURRENCY["12. FRESHNESS & CONCURRENCY CONTROL"]
    CURRENT_HEAD["Fetch Current PR HEAD SHA"]
    CURRENT_BASE["Fetch Current BASE SHA"]
    SHA_COMPARE{"SHA Still Current?"}
    VALID_ANALYSIS["VALID ANALYSIS"]
    STALE_ANALYSIS["STALE / SUPERSEDED"]
    CANCEL_WORKERS["Cancel Expensive Workers"]
    CREATE_NEW_RUN["Create New Analysis Run"]
    CACHE_REUSE["Reuse Valid Artifacts"]
end

FINAL_FINDINGS --> CURRENT_HEAD
CURRENT_HEAD --> CURRENT_BASE
CURRENT_BASE --> SHA_COMPARE
SHA_COMPARE -->|YES| VALID_ANALYSIS
SHA_COMPARE -->|NO| STALE_ANALYSIS
STALE_ANALYSIS --> CANCEL_WORKERS
CANCEL_WORKERS --> CACHE_REUSE
CACHE_REUSE --> CREATE_NEW_RUN
CREATE_NEW_RUN --> KAFKA

subgraph MERGE_READINESS["13. MERGE READINESS ENGINE"]
    REQUIRED_GATES{"All Required Gates Passed?"}
    BLOCKED["BLOCKED / WAITING"]
    MERGE_READY["MERGE READY"]
    PR_SUMMARY["Consolidated PR Summary"]
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
    FINAL_AI["Final AI Validation"]
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

subgraph POST_MERGE["15. POST-MERGE"]
    DEPLOYMENT["CI/CD Deployment"]
    PRODUCTION["Production"]
    FEEDBACK["Production Feedback"]
    MEMORY["Analysis Memory"]
end

PROTECTED_MAIN --> DEPLOYMENT
DEPLOYMENT --> PRODUCTION
PRODUCTION --> FEEDBACK
FEEDBACK --> MEMORY
MEMORY --> REPO_INDEX

subgraph CACHE["16. ANALYSIS ARTIFACT CACHE"]
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

AST_CACHE --> CACHE_REUSE
EMBEDDING_CACHE --> CACHE_REUSE
TEST_CACHE --> CACHE_REUSE
STATIC_CACHE --> CACHE_REUSE
DEP_GRAPH_CACHE --> CACHE_REUSE

subgraph STORAGE["17. PLATFORM DATA LAYER"]
    POSTGRES["PostgreSQL"]
    REDIS["Redis"]
    OBJECT_STORE["Object Storage"]
    VECTOR["Vector Store"]
end

PR_STATE --> POSTGRES
EVENT_STORE --> POSTGRES
SNAPSHOT --> POSTGRES
ANALYSIS_STATE --> POSTGRES
FINAL_FINDINGS --> POSTGRES
PRIORITY_ENGINE --> REDIS
PR_SCHEDULER --> REDIS
KAFKA --> REDIS
REPOSITORY_STATE --> OBJECT_STORE
VECTOR_DB --> VECTOR

subgraph OBSERVABILITY["18. OPEN TELEMETRY OBSERVABILITY"]
    OTEL_SDK["OpenTelemetry SDK"]
    OTEL_COLLECTOR["OpenTelemetry Collector"]
    TEMPO["Grafana Tempo<br/>Distributed Traces"]
    PROMETHEUS["Prometheus<br/>Metrics"]
    LOKI["Grafana Loki<br/>Logs"]
end

EVENT_PROCESSOR -.-> OTEL_SDK
PR_SCHEDULER -.-> OTEL_SDK
WORKER_1 -.-> OTEL_SDK
WORKER_2 -.-> OTEL_SDK
WORKER_3 -.-> OTEL_SDK
WORKER_N -.-> OTEL_SDK
CODE_CONTEXT -.-> OTEL_SDK
BUG_AGENT -.-> OTEL_SDK
SECURITY_AGENT -.-> OTEL_SDK
ARCHITECTURE_AGENT -.-> OTEL_SDK
QUALITY_AGENT -.-> OTEL_SDK
TEST_AGENT -.-> OTEL_SDK
TEST_RUNNER -.-> OTEL_SDK
EVIDENCE_VALIDATOR -.-> OTEL_SDK
CURRENT_HEAD -.-> OTEL_SDK
FINAL_CI -.-> OTEL_SDK
FINAL_AI -.-> OTEL_SDK
EXECUTE_MERGE -.-> OTEL_SDK

OTEL_SDK --> OTEL_COLLECTOR
OTEL_COLLECTOR --> TEMPO
OTEL_COLLECTOR --> PROMETHEUS
OTEL_COLLECTOR --> LOKI

subgraph GRAFANA["19. GRAFANA - AI PR CONTROL TOWER"]
    REPOSITORY_DASHBOARD["Repository Overview"]
    PR_QUEUE_DASHBOARD["PR Priority Queue"]
    DEPENDENCY_DASHBOARD["PR Dependency Graph"]
    ACTIVE_RUNS["Active Analysis Runs"]
    STALE_RUNS["Stale / Superseded Runs"]
    AGENT_TRACES["Agent Execution Traces"]
    MERGE_DASHBOARD["Merge Queue"]
    COST_DASHBOARD["LLM Token / Cost Usage"]
    LATENCY_DASHBOARD["Pipeline Latency"]
    FAILURE_DASHBOARD["Failures / Bottlenecks"]
    WORKER_DASHBOARD["Worker Capacity"]
    RAG_DASHBOARD["RAG Retrieval Metrics"]
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
DEP_GRAPH --> DEPENDENCY_DASHBOARD
MERGE_QUEUE --> MERGE_DASHBOARD
RAG_RERANKER --> RAG_DASHBOARD

WEBHOOK_EVENT -. "PR synchronize" .-> FRESHNESS_ENGINE
PROTECTED_MAIN -. "Base SHA changed" .-> FRESHNESS_ENGINE
P0 -. "Highest Priority" .-> PR_SCHEDULER
DEP_GRAPH -. "Dependency Constraint" .-> PR_SCHEDULER
HEAD_SHA -. "Immutable Analysis Identity" .-> CHECKOUT
MERGE_GROUP_SHA -. "Exact Merge State" .-> FINAL_AI
OTEL_COLLECTOR -. "Traces / Metrics / Logs" .-> GRAFANA
```

## Core Production Problems Addressed

-   Multiple repositories and multiple feature/hotfix branches
-   Concurrent pull requests
-   Priority-based scheduling for hotfixes and security changes
-   PR dependency and merge ordering
-   Immutable analysis using exact Base SHA and Head SHA
-   Stale analysis detection when a PR is updated during execution
-   Distributed analysis workers and isolated sandboxes
-   Repository-aware RAG
-   LangGraph-based agent orchestration
-   Deterministic static analysis
-   AI-generated unit tests
-   Finding validation and confidence scoring
-   GitHub Merge Queue and merge-group validation
-   Incremental indexing and artifact caching
-   OpenTelemetry tracing, metrics, and logs
-   Grafana PR Control Tower
-   LLM cost, latency, worker, RAG, and failure monitoring
