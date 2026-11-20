"""Student-only REST API: no private snapshots in payloads."""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.exams.models import ExamVersion
from .models import Attempt, AttemptQuestion, Grade, StudentResponse
from .serializers import SaveResponseSerializer
from .services import AttemptConflict, start_attempt, save_response, submit_attempt
from django.core.exceptions import ValidationError as DjangoValidationError


def safe_error(exc):
    if isinstance(exc, (Attempt.DoesNotExist, AttemptQuestion.DoesNotExist)):
        return Response({"code": "not_found", "message": "Not found"}, status=404)
    if isinstance(exc, AttemptConflict):
        return Response({"code": "attempt_conflict", "message": str(exc)}, status=409)
    if isinstance(exc, DjangoValidationError):
        return Response({"code": "validation_error", "message": "; ".join(exc.messages)}, status=400)
    raise exc


def student_attempt(attempt_id, student):
    return get_object_or_404(Attempt.objects.select_related("exam_version__template"), id=attempt_id, student=student)


def attempt_payload(attempt):
    parts = AttemptQuestion.objects.filter(attempt=attempt).order_by("position")
    responses = {str(r.attempt_question_id): r for r in
        StudentResponse.objects.filter(attempt_question__attempt=attempt)}
    return {
        "id": str(attempt.id),
        "exam_title": attempt.exam_version.template.title,
        "status": attempt.state,
        "started_at": attempt.started_at.isoformat(), "deadline_at": attempt.deadline_at.isoformat(),
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "questions": [{"id": str(q.id), "position": q.position, **q.public_snapshot,
            "response": {"selected_option_id": str(responses[str(q.id)].selected_option_id) if responses[str(q.id)].selected_option_id else None,
                         "text_answer": responses[str(q.id)].text_answer} if str(q.id) in responses else None}
            for q in parts]}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def begin(request, exam_id):
    exam = get_object_or_404(ExamVersion.objects.filter(is_published=True,template__is_active=True), id=exam_id)
    try:
        attempt = start_attempt(exam=exam, student=request.user)
    except AttemptConflict as exc:
        return safe_error(exc)
    return Response(attempt_payload(attempt), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail(request, attempt_id):
    return Response(attempt_payload(student_attempt(attempt_id, request.user)))


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def save(request, attempt_id, question_id):
    serializer = SaveResponseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        saved = save_response(attempt_id=attempt_id, question_id=question_id, student=request.user,
            selected_option_id=serializer.validated_data.get("selected_option_id"),
            text_answer=serializer.validated_data.get("text_answer", ""))
    except (Attempt.DoesNotExist, AttemptQuestion.DoesNotExist, AttemptConflict, DjangoValidationError) as exc:
        return safe_error(exc)
    return Response({"saved_at": saved.saved_at.isoformat()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit(request, attempt_id):
    try:
        attempt = submit_attempt(attempt_id=attempt_id, student=request.user)
    except (Attempt.DoesNotExist, AttemptConflict) as exc:
        return safe_error(exc)
    return Response({"id": str(attempt.id), "status": attempt.state, "result_url": f"/api/v1/attempts/{attempt.id}/result/"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def result(request, attempt_id):
    attempt = student_attempt(attempt_id, request.user)
    grade = Grade.objects.filter(attempt=attempt).first()
    if not grade:
        return Response({"code": "not_submitted", "message": "Submit the attempt first"}, status=409)
    items = list(grade.items.select_related("attempt_question", "attempt_question__revision").order_by("attempt_question__position"))
    # Withhold all explanations until every written response has been marked.
    # This prevents leakage of expected answers while review is pending.
    reveal = attempt.state == Attempt.State.GRADED_FINAL and attempt.exam_version.show_explanations_after_submit
    def correct_option_text(item):
        if not reveal or item.attempt_question.public_snapshot["kind"] != "single_choice":
            return None
        correct_id = item.attempt_question.private_key_snapshot.get("correct_option_id")
        return next((x["text"] for x in item.attempt_question.public_snapshot.get("options", [])
                     if x["id"] == correct_id), None)
    return Response({"attempt_id": str(attempt.id), "status": attempt.state,
        "scored_marks": str(grade.scored_marks), "scored_possible_marks": str(grade.scored_possible_marks),
        "ungraded_possible_marks": str(grade.ungraded_possible_marks),
        "final_percentage": str(grade.final_percentage) if grade.final_percentage is not None else None,
        "items": [{"question_id": str(i.attempt_question.id), "status": i.status,
                  "awarded": str(i.marks_awarded) if i.marks_awarded is not None else None,
                  "possible": str(i.possible_marks),
                  "explanation": i.attempt_question.private_key_snapshot.get("explanation") if reveal else None,
                  "correct_answer": correct_option_text(i),
                    "student_feedback": (
                        i.student_feedback or None
                        if attempt.state == Attempt.State.GRADED_FINAL
                        else None
                    ),}
                  for i in items]})



@api_view(["GET"])
@permission_classes([IsAuthenticated])
def history(request):
    attempts = (
        Attempt.objects
        .filter(student=request.user)
        .select_related("exam_version__template")
        .order_by("-started_at")[:50]
    )

    return Response([
        {
            "id": str(a.id),
            "exam_title": a.exam_version.template.title,
            "status": a.state,
            "started_at": a.started_at.isoformat(),
            "deadline_at": a.deadline_at.isoformat(),
            "submitted_at": (
                a.submitted_at.isoformat()
                if a.submitted_at
                else None
            ),
        }
        for a in attempts
    ])
