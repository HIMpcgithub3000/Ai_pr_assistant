import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    delivery_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(String, index=True)
    pr_number: Mapped[int] = mapped_column(Integer, index=True)
    
    # Immutable SHA Contract
    base_sha: Mapped[str] = mapped_column(String(64), index=True)
    head_sha: Mapped[str] = mapped_column(String(64), index=True)
    
    priority: Mapped[str] = mapped_column(String(10), default="P2") # P0, P1, P2, P3
    status: Mapped[str] = mapped_column(String(30), default="QUEUED") # QUEUED, RUNNING, VALIDATED, STALE, COMPLETED, FAILED
    
    is_fresh: Mapped[bool] = mapped_column(Boolean, default=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    findings: Mapped[list["AnalysisFinding"]] = relationship("AnalysisFinding", back_populates="run", cascade="all, delete-orphan")
    test_evidences: Mapped[list["TestEvidence"]] = relationship("TestEvidence", back_populates="run", cascade="all, delete-orphan")


class AnalysisFinding(Base):
    __tablename__ = "analysis_findings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(String, ForeignKey("analysis_runs.id"), index=True)
    
    file_path: Mapped[str] = mapped_column(String, index=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    symbol_name: Mapped[str | None] = mapped_column(String, nullable=True)
    
    category: Mapped[str] = mapped_column(String(50)) # BUG, SECURITY, ARCHITECTURE, QUALITY
    severity: Mapped[str] = mapped_column(String(20)) # CRITICAL, HIGH, MEDIUM, LOW, INFO
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Evidence Gate Verification
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="findings")


class TestEvidence(Base):
    __tablename__ = "test_evidences"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id: Mapped[str] = mapped_column(String, ForeignKey("analysis_runs.id"), index=True)
    
    test_suite_name: Mapped[str] = mapped_column(String(255))
    test_code: Mapped[str] = mapped_column(Text)
    raw_stdout: Mapped[str] = mapped_column(Text, default="")
    raw_stderr: Mapped[str] = mapped_column(Text, default="")
    exit_code: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    coverage_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)

    run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="test_evidences")


class CodeEmbedding(Base):
    __tablename__ = "code_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(String, index=True)
    file_path: Mapped[str] = mapped_column(String, index=True)
    commit_sha: Mapped[str] = mapped_column(String(64), index=True)
    
    chunk_content: Mapped[str] = mapped_column(Text)
    symbol_context: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)
