"""Validation and idempotent persistence for non-authoritative marking proposals."""
import hashlib
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.attempts.models import Attempt, GradeItem, StudentResponse
from apps.attempts.review_services import GradingConflict, require_reviewer

from .models import AIMarkingSuggestion
from .provider import AIProviderError, generate_marking


def _score(value, maximum: Decimal) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, str):
        raise AIProviderError("Invalid AI score")
    try:
        score = Decimal(value)
    except InvalidOperation as exc:
        raise AIProviderError("Invalid AI score") from exc
    if (not score.is_finite() or score < 0 or score > maximum
            or score.as_tuple().exponent < -2):
        raise AIProviderError("AI score is outside the grading rubric")
    return score


def validate_proposal(raw: dict, rubric: list[dict], possible: Decimal) -> tuple[Decimal, list, str]:
    """Fail closed if the model returns out-of-range or incomplete rubric scores."""
    if not isinstance(raw, dict) or not isinstance(raw.get("criterion_scores"), list):
        raise AIProviderError("AI returned no rubric scores")
    scores = raw["criterion_scores"]
    if len(scores) != len(rubric) or not rubric:
        raise AIProviderError("AI skipped or added a rubric criterion")
    by_number = {}
    for record in scores:
        if not isinstance(record, dict) or type(record.get("criterion_number")) is not int:
            raise AIProviderError("AI returned invalid criterion numbering")
        number = record["criterion_number"]
        if number in by_number or number < 1 or number > len(rubric):
            raise AIProviderError("AI repeated or invented a criterion")
        by_number[number] = record
    breakdown = []
    total = Decimal("0.00")
    for number, criterion in enumerate(rubric, 1):
        record = by_number.get(number)
        if not record:
            raise AIProviderError("AI omitted a criterion")
        maximum = Decimal(str(criterion["max_marks"]))
        awarded = _score(record.get("awarded"), maximum)
        reason = record.get("reason")
        if not isinstance(reason, str) or not 3 <= len(reason.strip()) <= 500:
            raise AIProviderError("AI criterion reason was invalid")
        total += awarded
        breakdown.append({
            "criterion_number": number,
            "criterion": criterion["criterion"],
            "max_marks": str(maximum),
            "awarded": str(awarded),
            "reason": reason.strip(),
        })
    feedback = raw.get("feedback")
    if not isinstance(feedback, str) or not 10 <= len(feedback.strip()) <= 3000:
        raise AIProviderError("AI feedback was invalid")
    if total > possible:
        raise AIProviderError("AI score exceeds question maximum")
    return total.quantize(Decimal("0.01")), breakdown, feedback.strip()


def propose_written_mark(*, item_id, actor) -> tuple[AIMarkingSuggestion, bool]:
    require_reviewer(actor)
    item = GradeItem.objects.select_related("grade__attempt", "attempt_question").filter(pk=item_id).first()
    if item is None:
        raise GradeItem.DoesNotExist()
    if (item.status != GradeItem.Status.PENDING
            or item.grade.attempt.state != Attempt.State.GRADING_PENDING
            or item.attempt_question.public_snapshot.get("kind") == "single_choice"):
        raise GradingConflict("Only pending submitted written answers may be suggested")
    existing = AIMarkingSuggestion.objects.filter(grade_item=item).first()
    if existing:
        return existing, False
    answer = StudentResponse.objects.filter(attempt_question=item.attempt_question).first()
    if not answer or not answer.text_answer.strip():
        raise GradingConflict("The written answer is empty")
    private = item.attempt_question.private_key_snapshot
    rubric = private.get("rubric", [])
    if not rubric:
        raise GradingConflict("A verified marking rubric is required")
    raw = generate_marking(
        prompt=item.attempt_question.public_snapshot["prompt"],
        answer=answer.text_answer,
        rubric=rubric,
        max_marks=str(item.possible_marks),
    )
    marks, breakdown, feedback = validate_proposal(raw, rubric, item.possible_marks)
    digest = hashlib.sha256(answer.text_answer.encode("utf-8")).hexdigest()
    try:
        with transaction.atomic():
            # Recheck after remote provider call: human grading may have completed.
            locked = GradeItem.objects.select_for_update().get(pk=item.pk)
            if locked.status != GradeItem.Status.PENDING:
                raise GradingConflict("Human marking already completed")
            suggestion, created = AIMarkingSuggestion.objects.get_or_create(
                grade_item=locked,
                defaults={
                    "proposed_marks": marks,
                    "breakdown": breakdown,
                    "feedback": feedback,
                    "model_name": settings.NICAT_AI_MODEL,
                    "answer_sha256": digest,
                    "generated_by": actor,
                },
            )
            return suggestion, created
    except IntegrityError:
        # A concurrent request may have already inserted the suggestion.
        return AIMarkingSuggestion.objects.get(grade_item=item), False


def proposal_payload(suggestion: AIMarkingSuggestion) -> dict:
    return {
        "grade_item_id": str(suggestion.grade_item_id),
        "proposed_marks": str(suggestion.proposed_marks),
        "breakdown": suggestion.breakdown,
        "feedback": suggestion.feedback,
        "model_name": suggestion.model_name,
        "review_status": suggestion.review_status,
        "generated_at": suggestion.created_at.isoformat(),
        "human_review_required": True,
    }
