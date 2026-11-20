"""Transactional exam workflows. Do not put grading decisions in serializers/views."""
from datetime import timedelta
from decimal import Decimal
from uuid import UUID
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Attempt, AttemptQuestion, StudentResponse, Grade, GradeItem, GradingEvent
from .grading import mark_single_choice, percentage
from apps.exams.models import ExamVersion
from apps.questions.models import QuestionRevision

class AttemptConflict(Exception):
    pass


@transaction.atomic
def start_attempt(*, exam: ExamVersion, student) -> Attempt:
    if not exam.is_published or not exam.template.is_active:
        raise AttemptConflict("Exam not available")
    parts = list(exam.items.select_related("revision", "revision__question__topic").order_by("position"))
    if not parts:
        raise AttemptConflict("Exam has no questions")
    for item in parts:
        if item.revision.status != QuestionRevision.Status.PUBLISHED:
            raise AttemptConflict("Exam references an unpublished question")
    now = timezone.now()
    attempt = Attempt.objects.create(student=student, exam_version=exam,
        started_at=now, deadline_at=now + timedelta(seconds=exam.duration_seconds))
    for item in parts:
        rev = item.revision
        options = list(rev.options.order_by("position")) if rev.kind == QuestionRevision.Kind.SINGLE_CHOICE else []
        if rev.kind == QuestionRevision.Kind.SINGLE_CHOICE and (len(options) < 2 or sum(bool(x.is_correct) for x in options) != 1):
            raise AttemptConflict("Invalid answer key")
        criteria = list(rev.rubric.order_by("position")) if rev.kind != QuestionRevision.Kind.SINGLE_CHOICE else []
        if rev.kind != QuestionRevision.Kind.SINGLE_CHOICE and (
            not criteria or sum((c.max_marks for c in criteria), Decimal("0")) != rev.max_marks
        ):
            raise AttemptConflict("Missing or inconsistent human-grading rubric")
        public = {"kind": rev.kind, "prompt": rev.prompt, "marks": str(rev.max_marks),
                  "topic": rev.question.topic.title, "provenance": rev.provenance,
                  "options": [{"id": str(x.id), "text": x.text} for x in options]}
        private = (
            {"correct_option_id": str(next(x.id for x in options if x.is_correct))}
            if options else {"rubric": [
                {"criterion": c.description, "max_marks": str(c.max_marks)} for c in criteria
            ]}
        )
        # Freeze the explanation as well. Subsequent archive edits cannot alter past results.
        private["explanation"] = rev.explanation
        AttemptQuestion.objects.create(attempt=attempt, revision=rev, position=item.position,
                                        public_snapshot=public, private_key_snapshot=private,
                                        possible_marks=rev.max_marks)
    return attempt


@transaction.atomic
def save_response(*, attempt_id: UUID, student, question_id: UUID,
                  selected_option_id: UUID | None, text_answer: str) -> StudentResponse:
    attempt = Attempt.objects.select_for_update().filter(id=attempt_id, student=student).first()
    if not attempt:
        raise Attempt.DoesNotExist()
    if attempt.state != Attempt.State.IN_PROGRESS:
        raise AttemptConflict("Attempt no longer editable")
    if timezone.now() >= attempt.deadline_at:
        raise AttemptConflict("Time limit has expired")
    item = AttemptQuestion.objects.filter(id=question_id, attempt=attempt).first()
    if not item:
        raise AttemptQuestion.DoesNotExist()
    kind = item.public_snapshot["kind"]
    if kind == QuestionRevision.Kind.SINGLE_CHOICE:
        if text_answer.strip():
            raise ValidationError("Multiple-choice questions do not accept written answers")
        valid_options = {o["id"] for o in item.public_snapshot.get("options", [])}
        if selected_option_id is not None and str(selected_option_id) not in valid_options:
            raise ValidationError("Selected option does not belong to this question")
        text_answer = ""
    elif selected_option_id is not None:
        raise ValidationError("This question requires a written answer")
    response, _ = StudentResponse.objects.update_or_create(attempt_question=item,
        defaults={"selected_option_id": selected_option_id, "text_answer": text_answer})
    return response


@transaction.atomic
def submit_attempt(*, attempt_id: UUID, student) -> Attempt:
    """One server-side, row-locked finalization; retried calls return existing result.

    After a deadline, previously autosaved answers may still be submitted but
    no new answer writes can be accepted. This policy prevents data loss.
    """
    attempt = Attempt.objects.select_for_update().filter(id=attempt_id, student=student).first()
    if not attempt:
        raise Attempt.DoesNotExist()
    if attempt.state in (Attempt.State.GRADED_FINAL, Attempt.State.GRADING_PENDING):
        return attempt
    if attempt.state != Attempt.State.IN_PROGRESS:
        raise AttemptConflict("Attempt cannot be submitted")
    parts = list(AttemptQuestion.objects.filter(attempt=attempt).order_by("position"))
    responses = {str(r.attempt_question_id): r for r in
        StudentResponse.objects.filter(attempt_question__attempt=attempt)}
    scored_marks = Decimal("0")
    scored_possible = Decimal("0")
    ungraded_possible = Decimal("0")
    grade_items = []
    for item in parts:
        response = responses.get(str(item.id))
        kind = item.public_snapshot["kind"]
        if kind == QuestionRevision.Kind.SINGLE_CHOICE:
            correct = item.private_key_snapshot["correct_option_id"]
            selected = str(response.selected_option_id) if response and response.selected_option_id else None
            earned = mark_single_choice(selected_option_id=selected, correct_option_id=correct,
                                        possible_marks=item.possible_marks)
            scored_marks += earned
            scored_possible += item.possible_marks
            grade_items.append((item, GradeItem.Status.FINAL, earned))
        elif response and response.text_answer.strip():
            ungraded_possible += item.possible_marks
            grade_items.append((item, GradeItem.Status.PENDING, None))
        else:
            scored_possible += item.possible_marks
            grade_items.append((item, GradeItem.Status.FINAL, Decimal("0")))
    is_final = ungraded_possible == 0
    grade = Grade.objects.create(attempt=attempt, scored_marks=scored_marks,
        scored_possible_marks=scored_possible, ungraded_possible_marks=ungraded_possible,
        final_percentage=percentage(earned=scored_marks, possible=scored_possible) if is_final and scored_possible else None,
        finalized_at=timezone.now() if is_final else None)
    GradeItem.objects.bulk_create([GradeItem(grade=grade, attempt_question=item,
        status=status, marks_awarded=marks, possible_marks=item.possible_marks)
        for item,status,marks in grade_items])
    GradingEvent.objects.create(grade=grade, actor=None, reason="Automatic objective marking / submission",
                                details={"type": "submission", "pending_written": not is_final})
    attempt.state = Attempt.State.GRADED_FINAL if is_final else Attempt.State.GRADING_PENDING
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["state", "submitted_at"])
    return attempt
