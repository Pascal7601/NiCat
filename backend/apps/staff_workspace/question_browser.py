"""Read-only, staff-scoped published-question discovery for Tutor authoring.

No answer keys, rubrics, private exam attempts, or unpublished revisions are
serialized. The existing Tutor generation service remains authoritative.
"""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academics.models import CurriculumUnit, Programme, Topic, Unit
from apps.questions.models import QuestionRevision
from apps.resources.models import SourceDocument
from apps.study_tutor.models import SourceExcerpt, TutorExplanation
from .services import require_staff


class QuestionSearchSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=120, trim_whitespace=True)
    programme_id = serializers.UUIDField(required=False, allow_null=True)
    unit_id = serializers.UUIDField(required=False, allow_null=True)
    topic_id = serializers.UUIDField(required=False, allow_null=True)
    offset = serializers.IntegerField(required=False, default=0, min_value=0, max_value=10000)
    limit = serializers.IntegerField(required=False, default=20, min_value=1, max_value=50)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def search_questions(request):
    """POST used for read-only filters because NiCat's JSON BFF rejects query strings.

    This route must be *explicitly allowlisted*. It is not a new question
    publication or editing path.
    """
    if not getattr(settings, "NICAT_STAFF_WORKSPACE_ENABLED", False):
        return Response({"code": "disabled"}, status=404)

    require_staff(request.user, "study_tutor.view_tutorexplanation", "questions.view_questionrevision")
    serializer = QuestionSearchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    args = serializer.validated_data

    published = QuestionRevision.Status.PUBLISHED
    root = QuestionRevision.objects.filter(
        status=published, question__is_active=True,
    ).select_related("question__topic__unit")

    # Programmes appear only when they have a curriculum mapping to a unit
    # containing at least one published, active question.
    programme_ids = CurriculumUnit.objects.filter(
        unit__topics__questions__is_active=True,
        unit__topics__questions__revisions__status=published,
    ).values_list("curriculum_version__programme_id", flat=True).distinct()
    programmes = [
        {"id": str(p.pk), "name": p.name, "university": p.university.name}
        for p in Programme.objects.filter(pk__in=programme_ids)
        .select_related("university").order_by("university__name", "name")[:150]
    ]

    programme_id = args.get("programme_id")
    unit_id = args.get("unit_id")
    topic_id = args.get("topic_id")
    scoped = root
    if programme_id:
        allowed_unit_ids = CurriculumUnit.objects.filter(
            curriculum_version__programme_id=programme_id
        ).values("unit_id")
        scoped = scoped.filter(question__topic__unit_id__in=allowed_unit_ids)

    # Filter choices come from *published* questions, rather than allowing
    # arbitrary unverified topic names or unrelated programme placements.
    available_units = Unit.objects.filter(
        topics__questions__is_active=True,
        topics__questions__revisions__status=published,
    )
    if programme_id:
        available_units = available_units.filter(
            pk__in=CurriculumUnit.objects.filter(
                curriculum_version__programme_id=programme_id
            ).values("unit_id")
        )
    units = [{"id": str(x.pk), "title": x.title}
             for x in available_units.distinct().order_by("title")[:300]]

    topic_scope = Topic.objects.filter(
        questions__is_active=True, questions__revisions__status=published
    )
    if programme_id:
        topic_scope = topic_scope.filter(
            unit_id__in=CurriculumUnit.objects.filter(
                curriculum_version__programme_id=programme_id
            ).values("unit_id")
        )
    if unit_id:
        scoped = scoped.filter(question__topic__unit_id=unit_id)
        topic_scope = topic_scope.filter(unit_id=unit_id)
    topics = [{"id": str(t.pk), "title": t.title, "unit_id": str(t.unit_id)}
              for t in topic_scope.distinct().order_by("unit__title", "title")[:300]]

    if topic_id:
        scoped = scoped.filter(question__topic_id=topic_id)
    search = args.get("search", "")
    if search:
        scoped = scoped.filter(
            Q(prompt__icontains=search)
            | Q(question__topic__title__icontains=search)
            | Q(question__topic__unit__title__icontains=search)
        )

    total = scoped.count()
    offset, limit = args["offset"], args["limit"]
    revisions = list(scoped.order_by("-published_at", "-pk")[offset:offset + limit])

    topic_ids = {r.question.topic_id for r in revisions}
    approved_counts = {
        row["topic_id"]: row["n"]
        for row in SourceExcerpt.objects.filter(
            topic_id__in=topic_ids,
            state=SourceExcerpt.State.APPROVED,
            reference__document__rights_status=SourceDocument.Rights.ALLOWED,
            reference__document__unit_id=F("topic__unit_id"),
        ).values("topic_id").annotate(n=Count("pk"))
    }
    revision_ids = [r.pk for r in revisions]
    tutor_states = {}
    # Published state takes precedence if both a published explanation and
    # a new draft exist for the same question.
    for row in TutorExplanation.objects.filter(revision_id__in=revision_ids).values("revision_id", "state"):
        current = tutor_states.get(row["revision_id"])
        if current != TutorExplanation.State.PUBLISHED:
            tutor_states[row["revision_id"]] = row["state"]

    return Response({
        "items": [{
            "id": str(r.pk), "question_id": str(r.question_id),
            "prompt": r.prompt[:1200], "kind": r.kind, "version": r.number,
            "max_marks": str(r.max_marks), "unit_id": str(r.question.topic.unit_id),
            "unit": r.question.topic.unit.title,
            "topic_id": str(r.question.topic_id), "topic": r.question.topic.title,
            "approved_excerpt_count": approved_counts.get(r.question.topic_id, 0),
            "tutor_state": tutor_states.get(r.pk),
        } for r in revisions],
        "programmes": programmes,
        "units": units,
        "topics": topics,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(revisions) < total,
    })
