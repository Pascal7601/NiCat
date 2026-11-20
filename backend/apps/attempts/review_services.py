"""Audited, transactional human marking of submitted written answers.

API views perform authorization; these functions also enforce permissions so
management commands and future entry points cannot bypass the reviewer role.
Never call this service with an untrusted user without checking permissions.
"""
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .grading import percentage
from .models import Attempt, Grade, GradeItem, GradingEvent


class GradingConflict(Exception):
    """The grade is in a state that forbids this transition."""


def require_reviewer(actor, *, correction=False):
    permission = "attempts.correct_final_grades" if correction else "attempts.review_written_answers"
    if not actor or not actor.is_authenticated or not actor.is_active or not actor.is_staff or not actor.has_perm(permission):
        raise PermissionDenied("A designated reviewer is required")


def _validate_marks(marks: Decimal, possible: Decimal) -> None:
    if not isinstance(marks, Decimal) or not marks.is_finite():
        raise ValidationError("Marks must be a finite decimal")
    if marks.as_tuple().exponent < -2:
        raise ValidationError("Marks may have at most two decimal places")
    if not Decimal("0.00") <= marks <= possible:
        raise ValidationError("Marks must be between zero and the question maximum")


def _recalculate_totals(grade: Grade) -> bool:
    """Recalculate from grade items; never increment totals optimistically."""
    earned = Decimal("0.00")
    finalized_possible = Decimal("0.00")
    pending_possible = Decimal("0.00")
    for item in GradeItem.objects.filter(grade=grade):
        if item.status == GradeItem.Status.PENDING:
            pending_possible += item.possible_marks
        else:
            if item.marks_awarded is None:
                raise GradingConflict("Final grade item missing awarded marks")
            earned += item.marks_awarded
            finalized_possible += item.possible_marks
    is_final = pending_possible == 0
    if is_final and finalized_possible <= 0:
        raise GradingConflict("Cannot finalize an exam with zero assessable marks")
    grade.scored_marks = earned
    grade.scored_possible_marks = finalized_possible
    grade.ungraded_possible_marks = pending_possible
    grade.final_percentage = percentage(earned=earned, possible=finalized_possible) if is_final and finalized_possible else None
    if is_final and grade.finalized_at is None:
        grade.finalized_at = timezone.now()
    grade.save(update_fields=["scored_marks", "scored_possible_marks", "ungraded_possible_marks", "final_percentage", "finalized_at"])
    return is_final



@transaction.atomic
def review_written_answer(
    *,
    item_id,
    actor,
    marks: Decimal,
    rationale: str,
    student_feedback: str,
) -> GradeItem:
    """Mark a written answer once and audit the decision."""

    require_reviewer(actor)

    if len(rationale.strip()) < 10:
        raise ValidationError(
            "Reviewer rationale must be at least 10 characters"
        )

    if not 10 <= len(student_feedback.strip()) <= 2000:
        raise ValidationError(
            "Student feedback must contain 10–2000 characters"
        )

    item = (
        GradeItem.objects
        .select_related("grade__attempt", "attempt_question")
        .filter(pk=item_id)
        .first()
    )

    if item is None:
        raise GradeItem.DoesNotExist()

    # Serialize grading operations for this examination attempt.
    grade = Grade.objects.select_for_update().get(
        pk=item.grade_id
    )

    item.refresh_from_db()

    if (
        grade.attempt.state != Attempt.State.GRADING_PENDING
        or item.status != GradeItem.Status.PENDING
    ):
        raise GradingConflict(
            "This answer is not pending first review"
        )

    if (
        item.attempt_question.public_snapshot.get("kind")
        == "single_choice"
    ):
        raise GradingConflict(
            "Objective questions are marked automatically"
        )

    _validate_marks(marks, item.possible_marks)

    item.status = GradeItem.Status.FINAL
    item.marks_awarded = marks
    item.student_feedback = student_feedback.strip()

    item.save(
        update_fields=[
            "status",
            "marks_awarded",
            "student_feedback",
        ]
    )

    all_final = _recalculate_totals(grade)

    if all_final:
        Attempt.objects.filter(
            pk=grade.attempt_id,
            state=Attempt.State.GRADING_PENDING,
        ).update(state=Attempt.State.GRADED_FINAL)

    GradingEvent.objects.create(
        grade=grade,
        actor=actor,
        reason=rationale.strip(),
        details={
            "action": "first_review",
            "grade_item_id": str(item.pk),
            "new_marks": str(marks),
            "all_final": all_final,
        },
    )

    return item

@transaction.atomic
def correct_final_answer(
    *,
    item_id,
    actor,
    marks: Decimal,
    reason: str,
    student_feedback: str | None = None,
) -> GradeItem:
    """Correct a finalized grade with a separate permission."""

    require_reviewer(actor, correction=True)

    if len(reason.strip()) < 15:
        raise ValidationError(
            "Correction reason must be at least 15 characters"
        )

    item = (
        GradeItem.objects
        .select_related("grade__attempt")
        .filter(pk=item_id)
        .first()
    )

    if item is None:
        raise GradeItem.DoesNotExist()

    grade = Grade.objects.select_for_update().get(
        pk=item.grade_id
    )

    item.refresh_from_db()

    if (
        grade.attempt.state != Attempt.State.GRADED_FINAL
        or item.status != GradeItem.Status.FINAL
    ):
        raise GradingConflict(
            "Only finalized grade items can be corrected"
        )

    _validate_marks(marks, item.possible_marks)

    previous = item.marks_awarded
    previous_feedback = item.student_feedback

    if (
        student_feedback is not None
        and not 10 <= len(student_feedback.strip()) <= 2000
    ):
        raise ValidationError(
            "Student feedback must contain 10–2000 characters"
        )

    updated_feedback = (
        student_feedback.strip()
        if student_feedback is not None
        else previous_feedback
    )

    if (
        previous == marks
        and previous_feedback == updated_feedback
    ):
        raise GradingConflict(
            "No grade or feedback change to record"
        )

    item.marks_awarded = marks
    item.student_feedback = updated_feedback

    item.save(
        update_fields=["marks_awarded", "student_feedback"]
    )

    _recalculate_totals(grade)

    GradingEvent.objects.create(
        grade=grade,
        actor=actor,
        reason=reason.strip(),
        details={
            "action": "correction",
            "grade_item_id": str(item.pk),
            "old_marks": str(previous),
            "new_marks": str(marks),
            "old_feedback": previous_feedback,
            "new_feedback": updated_feedback,
        },
    )

    return item
