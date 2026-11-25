"""Sprint 8: reviewer-gated follow-ups and source-safe revision recommendations.

No external model is called by this module. In mock mode, student submissions
create clearly labelled drafts which a human must replace and approve.
"""
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.attempts.models import Attempt, AttemptQuestion, GradeItem
from apps.study_tutor.models import SourceExcerpt, TutorExplanation
from apps.study_tutor.services import (
    _eligible, fingerprint, require_academic_reviewer, student_payload,
)
from .models import TutorDailyBudget, TutorFollowUp


class CoachConflict(Exception):
    pass


class CoachQuotaExceeded(Exception):
    pass


def daily_limit():
    return max(0, int(getattr(settings, "NICAT_COACH_STUDENT_DAILY_LIMIT", 3)))


def global_limit():
    return max(0, int(getattr(settings, "NICAT_COACH_GLOBAL_DAILY_LIMIT", 100)))


def remaining_for(user):
    used = TutorFollowUp.objects.filter(student=user, quota_day=timezone.localdate()).count()
    return max(0, daily_limit() - used)


def validate_question(value):
    if not isinstance(value, str):
        raise ValueError("Enter a follow-up question")
    question = " ".join(value.split())
    if not 12 <= len(question) <= 500:
        raise ValueError("The question must contain between 12 and 500 characters")
    return question


def _released_explanation(revision):
    """Reuse Sprint 7's rights, fingerprint, academic publication checks."""
    if student_payload(revision=revision) is None:
        return None
    return TutorExplanation.objects.filter(
        revision=revision, state=TutorExplanation.State.PUBLISHED,
        approved_by__isnull=False, approved_at__isnull=False,
    ).first()


def require_released_item(*, student, attempt_id, question_id):
    """Return only the requesting student's fully released AttemptQuestion."""
    try:
        attempt = Attempt.objects.select_related("exam_version", "grade").get(
            pk=attempt_id, student=student
        )
        item = AttemptQuestion.objects.select_related(
            "revision__question__topic"
        ).get(pk=question_id, attempt=attempt)
    except (Attempt.DoesNotExist, AttemptQuestion.DoesNotExist):
        raise PermissionDenied("Attempt or question was not found")
    if (
        attempt.state != Attempt.State.GRADED_FINAL
        or not attempt.exam_version.show_explanations_after_submit
        or not hasattr(attempt, "grade")
        or not attempt.grade.finalized_at
        or GradeItem.objects.filter(grade=attempt.grade, status=GradeItem.Status.PENDING).exists()
    ):
        raise CoachConflict("Explanations are not released for this examination")
    return item


def _mock_draft(question):
    """Clearly not a model result; staff must author verified content to publish."""
    return (
        "MOCK TEST DATA — NOT AN ACADEMIC ANSWER. "
        "The student asked: " + question[:450] + "\n"
        "An academic reviewer must replace this placeholder with an answer "
        "grounded in the cited approved source excerpts before publication."
    )


def create_followup(*, student, attempt_question, question):
    question = validate_question(question)
    if getattr(settings, "NICAT_AI_PROVIDER", "openai") != "mock":
        raise CoachConflict("Sprint 8 follow-ups currently support mock mode only")

    # Verify rights and publish state before and after quota locks.
    explanation = _released_explanation(attempt_question.revision)
    if explanation is None:
        raise CoachConflict("No current academically approved explanation")

    day = timezone.localdate()
    with transaction.atomic():
        # Serializes requests by the same student on PostgreSQL.
        type(student).objects.select_for_update().get(pk=student.pk)
        budget, _ = TutorDailyBudget.objects.get_or_create(day=day)
        budget = TutorDailyBudget.objects.select_for_update().get(pk=budget.pk)
        if TutorFollowUp.objects.filter(student=student, quota_day=day).count() >= daily_limit():
            raise CoachQuotaExceeded("Your daily follow-up limit has been reached")
        if budget.requests >= global_limit():
            raise CoachQuotaExceeded("Today's platform follow-up capacity is full")
        # Fail closed if academic evidence changed while the request waited.
        explanation = _released_explanation(attempt_question.revision)
        if explanation is None:
            raise CoachConflict("Approved academic evidence is no longer available")
        cited = list(explanation.citations.all())
        if not cited:
            raise CoachConflict("The published explanation has no approved citations")
        followup = TutorFollowUp.objects.create(
            student=student, attempt_question=attempt_question, explanation=explanation,
            question=question, draft_answer=_mock_draft(question), quota_day=day,
        )
        followup.citations.set(cited)
        TutorDailyBudget.objects.filter(pk=day).update(requests=F("requests") + 1)
        return followup


def publish_followup(*, followup_id, actor):
    require_academic_reviewer(actor)
    with transaction.atomic():
        item = TutorFollowUp.objects.select_for_update().select_related(
            "attempt_question__revision__question__topic", "explanation"
        ).get(pk=followup_id)
        if item.state != TutorFollowUp.State.DRAFT:
            raise CoachConflict("Only pending follow-ups can be published")
        answer = item.draft_answer.strip()
        if not 50 <= len(answer) <= 4000 or "MOCK TEST DATA" in answer.upper():
            raise CoachConflict("Replace the mock placeholder with a verified academic answer (50–4000 chars)")
        current = _released_explanation(item.attempt_question.revision)
        if current is None or current.pk != item.explanation_id:
            raise CoachConflict("Original published explanation was withdrawn or superseded")
        sources = list(item.citations.select_related("reference__document", "topic"))
        original = list(item.explanation.citations.select_related("reference__document", "topic"))
        if (
            not _eligible(sources, revision=item.attempt_question.revision)
            or {s.pk for s in sources} != {s.pk for s in original}
            or fingerprint(original) != item.explanation.source_fingerprint
        ):
            raise CoachConflict("Cited excerpts are missing, altered, or rights-revoked")
        item.published_answer = answer
        item.state = TutorFollowUp.State.PUBLISHED
        item.reviewed_by = actor
        item.reviewed_at = timezone.now()
        item.save(update_fields=["published_answer", "state", "reviewed_by", "reviewed_at"])
        return item


def reject_followup(*, followup_id, actor):
    require_academic_reviewer(actor)
    with transaction.atomic():
        item = TutorFollowUp.objects.select_for_update().get(pk=followup_id)
        if item.state != TutorFollowUp.State.DRAFT:
            raise CoachConflict("Only pending follow-ups can be rejected")
        item.state = TutorFollowUp.State.REJECTED
        item.reviewed_by = actor
        item.reviewed_at = timezone.now()
        item.save(update_fields=["state", "reviewed_by", "reviewed_at"])
        return item


def withdraw_followup(*, followup_id, actor):
    require_academic_reviewer(actor)
    with transaction.atomic():
        item = TutorFollowUp.objects.select_for_update().get(pk=followup_id)
        if item.state != TutorFollowUp.State.PUBLISHED:
            raise CoachConflict("Only published answers can be withdrawn")
        item.state = TutorFollowUp.State.WITHDRAWN
        item.save(update_fields=["state"])
        return item


def student_followup_payload(item):
    result = {
        "id": str(item.pk), "question": item.question,
        "status": item.state, "created_at": item.created_at.isoformat(),
        "answer": None, "sources": [],
    }
    if item.state != TutorFollowUp.State.PUBLISHED or not item.reviewed_by_id:
        return result
    current = _released_explanation(item.attempt_question.revision)
    if current is None or current.pk != item.explanation_id:
        result["status"] = "unavailable"
        return result
    sources = list(item.citations.select_related("reference__document", "topic"))
    if (
        not _eligible(sources, revision=item.attempt_question.revision)
        or {s.pk for s in sources} != set(item.explanation.citations.values_list("pk", flat=True))
    ):
        result["status"] = "unavailable"
        return result
    result["answer"] = item.published_answer
    result["sources"] = [{
        "excerpt_id": str(s.pk), "title": s.reference.document.title,
        "page": s.reference.page_label, "section": s.reference.section_label,
        "evidence": s.text[:300],
    } for s in sources]
    return result


def revision_recommendations(*, student, max_attempts=20, limit=5):
    """Compute weak-topic scores only from this student's FINAL GradeItem records."""
    attempts = list(Attempt.objects.filter(
        student=student, state=Attempt.State.GRADED_FINAL,
        grade__finalized_at__isnull=False,
    ).order_by("-submitted_at")[:max_attempts])
    ids = [a.pk for a in attempts]
    totals = defaultdict(lambda: {"awarded": Decimal("0"), "possible": Decimal("0"), "questions": 0, "title": ""})
    if ids:
        graded = GradeItem.objects.filter(
            grade__attempt_id__in=ids, status=GradeItem.Status.FINAL,
        ).select_related("attempt_question__revision__question__topic")[:500]
        for item in graded:
            aq = item.attempt_question
            topic = aq.revision.question.topic
            possible = item.possible_marks
            if possible is None or possible <= 0 or item.marks_awarded is None:
                continue
            bucket = totals[str(topic.pk)]
            bucket["title"] = topic.title
            bucket["awarded"] += item.marks_awarded
            bucket["possible"] += possible
            bucket["questions"] += 1
    ranked = sorted(totals.items(), key=lambda pair: (
        pair[1]["awarded"] / pair[1]["possible"], pair[1]["title"]
    ))[:limit]
    output = []
    for topic_id, values in ranked:
        percentage = round(100 * values["awarded"] / values["possible"], 1)
        sources_available = SourceExcerpt.objects.filter(
            topic_id=topic_id, state=SourceExcerpt.State.APPROVED,
            reference__document__rights_status="allowed",
        ).exists()
        output.append({
            "topic_id": topic_id, "topic": values["title"],
            "percentage": float(percentage),
            "questions": values["questions"],
            "awarded_marks": str(values["awarded"]),
            "possible_marks": str(values["possible"]),
            "priority": "revise" if percentage < 75 else "maintain",
            "approved_sources_available": sources_available,
            "guidance": (
                "Revisit approved notes on this topic and try a new practice question."
                if sources_available else
                "Review this topic with your own course notes and try another practice question."
            ),
        })
    return {"attempts_considered": len(attempts), "recommendations": output}
