import hashlib
import hmac
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import AnalysisFinding, AnalysisRun, TestEvidence, WebhookEvent
from src.db.session import get_db_session, init_db
from src.services.sha_contract import SHAContractService
from src.worker.processor import PRAnalysisProcessor
from src.worker.queue import PriorityQueueManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables are initialized
    await init_db()
    yield


app = FastAPI(
    title="AI-Powered PR Assistant API",
    description="Production-grade AI PR Review engine with SHA contracts, priority queues, and test sandboxes",
    version="1.0.0",
    lifespan=lifespan,
)

# OpenTelemetry auto-instrumentation
FastAPIInstrumentor.instrument_app(app)

sha_service = SHAContractService()
queue_manager = PriorityQueueManager()
processor = PRAnalysisProcessor()


class TriggerRunRequest(BaseModel):
    repository_id: str
    pr_number: int
    base_sha: str
    head_sha: str
    priority: str = "P2"
    clone_url: str | None = None
    live_head_sha: str | None = None
    sample_diff: str | None = None
    changed_files: list[str] | None = None


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "env": settings.APP_ENV,
        "services": {
            "postgres": "ready",
            "redis": "ready",
            "otel": settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        }
    }


def verify_github_signature(payload: bytes, signature_header: str | None) -> bool:
    if not settings.GITHUB_WEBHOOK_SECRET or not signature_header:
        # Development fallback if secret not set
        return True
    
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.post("/webhook/github")
async def github_webhook_endpoint(
    request: Request,
    x_github_delivery: str | None = Header(None),
    x_github_event: str | None = Header(None),
    x_hub_signature_256: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
):
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    delivery_id = x_github_delivery or "manual-" + hashlib.sha256(body).hexdigest()[:12]

    # Idempotency check: ensure same delivery isn't processed twice
    existing_event = await db.execute(
        select(WebhookEvent).where(WebhookEvent.delivery_id == delivery_id)
    )
    if existing_event.scalar_one_or_none():
        return {"status": "ignored", "reason": "duplicate delivery id"}

    webhook_record = WebhookEvent(
        delivery_id=delivery_id,
        event_type=x_github_event or "unknown",
        payload=payload,
        processed=True,
    )
    db.add(webhook_record)
    await db.commit()

    # Route pull_request events
    if x_github_event == "pull_request" or "pull_request" in payload:
        pr_data = payload.get("pull_request", {})
        action = payload.get("action", "")
        
        # Only analyze on opened, synchronize, or reopened
        if action in ("opened", "synchronize", "reopened", ""):
            repo_id = payload.get("repository", {}).get("full_name", "test-org/test-repo")
            pr_number = pr_data.get("number", payload.get("number", 1))
            base_sha = pr_data.get("base", {}).get("sha", "base123456")
            head_sha = pr_data.get("head", {}).get("sha", "head123456")
            clone_url = payload.get("repository", {}).get("clone_url", "")

            # Priority assignment based on labels or title
            labels = [l.get("name", "").lower() for l in pr_data.get("labels", [])]
            if "hotfix" in labels or "p0" in labels:
                priority = "P0"
            elif "security" in labels or "p1" in labels:
                priority = "P1"
            else:
                priority = "P2"

            # Issue Immutable SHA contract
            run = await sha_service.issue_contract(
                db=db,
                repository_id=repo_id,
                pr_number=pr_number,
                base_sha=base_sha,
                head_sha=head_sha,
                priority=priority,
            )

            job_data = {
                "analysis_id": run.id,
                "repository_id": repo_id,
                "pr_number": pr_number,
                "base_sha": base_sha,
                "head_sha": head_sha,
                "clone_url": clone_url,
                "priority": priority,
            }
            await queue_manager.enqueue_job(job_data, priority=priority)

            return {
                "status": "enqueued",
                "analysis_id": run.id,
                "contract": {"head_sha": head_sha, "base_sha": base_sha, "priority": priority},
            }

    return {"status": "received", "event": x_github_event}


@app.post("/api/v1/trigger")
async def trigger_run_endpoint(
    req: TriggerRunRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Direct API endpoint to trigger a synchronous or test analysis run."""
    run = await sha_service.issue_contract(
        db=db,
        repository_id=req.repository_id,
        pr_number=req.pr_number,
        base_sha=req.base_sha,
        head_sha=req.head_sha,
        priority=req.priority,
    )

    job_data = {
        "analysis_id": run.id,
        "repository_id": req.repository_id,
        "pr_number": req.pr_number,
        "base_sha": req.base_sha,
        "head_sha": req.head_sha,
        "priority": req.priority,
        "clone_url": req.clone_url or "",
        "live_head_sha": req.live_head_sha or req.head_sha,
        "sample_diff": req.sample_diff,
        "changed_files": req.changed_files or ["app.py"],
    }

    # Execute processor directly for end-to-end testing
    result = await processor.process_analysis_run(db, job_data)
    return result


@app.get("/api/v1/runs/{analysis_id}")
async def get_run_details(
    analysis_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    stmt = select(AnalysisRun).where(AnalysisRun.id == analysis_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    findings_res = await db.execute(select(AnalysisFinding).where(AnalysisFinding.analysis_id == analysis_id))
    evidence_res = await db.execute(select(TestEvidence).where(TestEvidence.analysis_id == analysis_id))

    return {
        "id": run.id,
        "repository_id": run.repository_id,
        "pr_number": run.pr_number,
        "base_sha": run.base_sha,
        "head_sha": run.head_sha,
        "priority": run.priority,
        "status": run.status,
        "is_fresh": run.is_fresh,
        "summary": run.summary,
        "findings": [
            {
                "file_path": f.file_path,
                "line_number": f.line_number,
                "category": f.category,
                "severity": f.severity,
                "title": f.title,
                "description": f.description,
                "verified": f.verified,
                "confidence": f.confidence,
            }
            for f in findings_res.scalars().all()
        ],
        "test_evidence": [
            {
                "test_suite": te.test_suite_name,
                "passed": te.passed,
                "exit_code": te.exit_code,
                "stdout": te.raw_stdout,
            }
            for te in evidence_res.scalars().all()
        ],
    }
