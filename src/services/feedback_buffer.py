import uuid
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import HumanReviewFeedback


class HumanReviewFeedbackBuffer:
    """
    Stage 3: Closed-Loop Human Review Feedback Buffer.
    Listens to human review decisions (pull_request_review: approved, changes_requested, dismissed)
    and stores calibrated vector memory.
    Dynamically adjusts model confidence scores so that:
      - Confirmed issue patterns gain higher confidence weighting (+0.15)
      - Dismissed / false-positive warnings are penalized (-0.25) to suppress repeated nagging
    """

    def __init__(self):
        self.default_confirmation_boost = 0.15
        self.default_dismissal_penalty = 0.25

    async def record_feedback(
        self,
        db: AsyncSession,
        repository_id: str,
        pr_number: int,
        reviewer_handle: str,
        event_type: str,  # 'approved', 'changes_requested', 'dismissed', 'comment_acknowledged'
        analysis_id: str | None = None,
        finding_category: str | None = None,
        rule_or_title: str | None = None,
        feedback_text: str | None = None,
        file_path: str | None = None,
    ) -> HumanReviewFeedback:
        """Records human engineer review feedback and assigns a calibrated weight delta."""
        if event_type in ("approved", "changes_requested", "comment_acknowledged"):
            # Engineer validated or took action on the finding
            weight_delta = self.default_confirmation_boost
        elif event_type in ("dismissed", "false_positive"):
            # Engineer dismissed finding as incorrect / false-positive
            weight_delta = -self.default_dismissal_penalty
        else:
            weight_delta = 0.0

        feedback = HumanReviewFeedback(
            id=str(uuid.uuid4()),
            repository_id=repository_id,
            pr_number=pr_number,
            analysis_id=analysis_id,
            event_type=event_type,
            reviewer_handle=reviewer_handle,
            finding_category=finding_category,
            rule_or_title=rule_or_title,
            feedback_text=feedback_text,
            file_path=file_path,
            weight_delta=weight_delta,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        return feedback

    async def get_historical_calibration(
        self,
        db: AsyncSession,
        repository_id: str,
        finding_category: str | None = None,
        rule_or_title: str | None = None,
    ) -> float:
        """
        Calculates the net historical weight calibration for a category or specific rule.
        Returns a float delta to adjust model confidence:
          Confidence_calibrated = clamp(base_confidence + net_delta, 0.05, 0.99)
        """
        stmt = select(func.sum(HumanReviewFeedback.weight_delta)).where(
            HumanReviewFeedback.repository_id == repository_id
        )
        if rule_or_title:
            stmt = stmt.where(HumanReviewFeedback.rule_or_title == rule_or_title)
        elif finding_category:
            stmt = stmt.where(HumanReviewFeedback.finding_category == finding_category)

        res = await db.execute(stmt)
        net_delta = res.scalar() or 0.0
        # Cap historical delta adjustment to [-0.4, +0.3] to prevent runaway distortion
        return max(-0.4, min(0.3, float(net_delta)))

    async def calibrate_findings(
        self,
        db: AsyncSession,
        repository_id: str,
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Applies closed-loop human feedback calibration to candidate findings.
        Suppresses false positives whose calibrated confidence drops below 0.50.
        """
        calibrated = []
        for f in findings:
            rule_or_title = f.get("title")
            category = f.get("category")
            base_conf = float(f.get("confidence", 0.8))

            delta = await self.get_historical_calibration(
                db=db,
                repository_id=repository_id,
                finding_category=category,
                rule_or_title=rule_or_title,
            )

            final_conf = max(0.05, min(0.99, base_conf + delta))

            # Suppress finding if engineers repeatedly dismissed this rule
            if final_conf < 0.50:
                continue

            f_copy = dict(f)
            f_copy["confidence"] = round(final_conf, 2)
            f_copy["calibrated"] = delta != 0.0
            f_copy["calibration_delta"] = round(delta, 2)
            calibrated.append(f_copy)

        return calibrated

    async def list_recent_feedback(
        self,
        db: AsyncSession,
        repository_id: str | None = None,
        limit: int = 50,
    ) -> list[HumanReviewFeedback]:
        """Lists recent human feedback logs."""
        stmt = select(HumanReviewFeedback).order_by(desc(HumanReviewFeedback.created_at)).limit(limit)
        if repository_id:
            stmt = stmt.where(HumanReviewFeedback.repository_id == repository_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())
