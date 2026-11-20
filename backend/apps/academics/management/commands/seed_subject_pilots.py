
"""Import review-gated IAP and E-Commerce pilot exams."""

import json
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.academics.models import (
    University, Programme, CurriculumVersion,
    CurriculumUnit, Unit, Topic,
)
from apps.exams.models import ExamTemplate, ExamVersion, ExamQuestion
from apps.questions.models import (
    Question, QuestionRevision, ChoiceOption, RubricCriterion,
)
from apps.resources.models import SourceDocument, SourceReference


DATASETS = {
    "iap": "iap_pilot_questions.json",
    "ecommerce": "ecommerce_pilot_questions.json",
}


def read_dataset(unit_key):
    path = (
        Path(__file__).resolve().parents[5]
        / "data"
        / DATASETS[unit_key]
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data["questions"]

    if len(questions) != 12 or len({q["key"] for q in questions}) != 12:
        raise CommandError(
            "Pilot requires 12 questions with distinct stable keys"
        )

    source_keys = {s["key"] for s in data["sources"]}
    if len(source_keys) != len(data["sources"]):
        raise CommandError("Duplicate source key")

    total = Decimal("0")

    for question in questions:
        try:
            marks = Decimal(question["marks"])
        except (InvalidOperation, KeyError) as exc:
            raise CommandError("Invalid question marks") from exc

        if (
            marks <= 0
            or question["source"] not in source_keys
            or not question["prompt"].strip()
        ):
            raise CommandError(
                f"Invalid question metadata: {question['key']}"
            )

        if question["kind"] == "single_choice":
            if (
                marks != 1
                or len(question.get("options", [])) != 4
                or not 0 <= question.get("correct_index", -1) < 4
            ):
                raise CommandError(
                    f"Invalid MCQ: {question['key']}"
                )

        elif question["kind"] == "written":
            rubric = question.get("rubric", [])
            if (
                not rubric
                or sum(
                    (Decimal(r["marks"]) for r in rubric),
                    Decimal("0"),
                ) != marks
            ):
                raise CommandError(
                    f"Invalid rubric: {question['key']}"
                )

        else:
            raise CommandError(
                f"Unsupported kind: {question['kind']}"
            )

        total += marks

    if total != Decimal("20"):
        raise CommandError(
            f"Expected 20 marks; received {total}"
        )

    return data


def stable_id(dataset_key, item_key, entity):
    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"nicat/{dataset_key}/v1/{item_key}/{entity}",
    )


def draft_matches(version, data):
    """Reject changed content instead of overwriting a reviewed exam."""

    items = list(
        version.items
        .select_related("revision__question__topic")
        .prefetch_related(
            "revision__options",
            "revision__rubric",
        )
        .order_by("position")
    )

    if (
        len(items) != len(data["questions"])
        or version.duration_seconds != data["exam"]["duration_seconds"]
        or version.instructions != data["exam"]["instructions"]
    ):
        return False

    for position, (item, q) in enumerate(
        zip(items, data["questions"]), 1
    ):
        rev = item.revision

        if (
            item.position != position
            or rev.pk != stable_id(
                data["dataset"], q["key"], "revision"
            )
            or rev.prompt != q["prompt"]
            or rev.kind != q["kind"]
            or rev.max_marks != Decimal(q["marks"])
            or rev.explanation != q["explanation"]
            or rev.question.topic.title != q["topic"]
        ):
            return False

        if q["kind"] == "single_choice":
            actual = [
                (option.text, option.is_correct)
                for option in rev.options.order_by("position")
            ]
            expected = [
                (label, i == q["correct_index"])
                for i, label in enumerate(q["options"])
            ]

        else:
            actual = [
                (criterion.description, criterion.max_marks)
                for criterion in rev.rubric.order_by("position")
            ]
            expected = [
                (r["description"], Decimal(r["marks"]))
                for r in q["rubric"]
            ]

        if actual != expected:
            return False

    return True


class Command(BaseCommand):
    help = "Seed review-gated NiCat IAP and E-Commerce practice exams."

    def add_arguments(self, parser):
        parser.add_argument(
            "--unit",
            choices=sorted(DATASETS),
            required=True,
        )
        parser.add_argument(
            "--publish",
            action="store_true",
        )
        parser.add_argument(
            "--reviewer-email",
            default="",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        data = read_dataset(options["unit"])
        reviewer = None

        if options["publish"]:
            reviewer = User.objects.filter(
                email__iexact=options["reviewer_email"],
                is_active=True,
                is_staff=True,
            ).first()

            if (
                reviewer is None
                or not reviewer.has_perm(
                    "questions.change_questionrevision"
                )
            ):
                raise CommandError(
                    "--publish requires an active staff reviewer "
                    "with question-review permission"
                )

            self.stdout.write(self.style.WARNING(
                "Publishing asserts academic, answer-key, "
                "and content-rights review is complete."
            ))

        university, _ = University.objects.get_or_create(
            name="Multimedia University of Kenya",
            defaults={"abbreviation": "MMU"},
        )

        programme, _ = Programme.objects.get_or_create(
            university=university,
            name="Bachelor of Business Information Technology",
            defaults={"code": "BBIT"},
        )

        curriculum, _ = CurriculumVersion.objects.get_or_create(
            programme=programme,
            label=(
                "Archived study collection 2020–2023 "
                "(not official curriculum)"
            ),
        )

        unit, _ = Unit.objects.get_or_create(
            slug=data["unit"]["slug"],
            defaults={"title": data["unit"]["title"]},
        )

        if unit.title != data["unit"]["title"]:
            raise CommandError(
                "Existing unit slug has a different title"
            )

        placement, created = CurriculumUnit.objects.get_or_create(
            curriculum_version=curriculum,
            unit=unit,
            defaults={
                "year_number": data["unit"]["year"],
                "semester_number": data["unit"]["semester"],
                "displayed_code": data["unit"]["code"],
                "code_verification_status": "archival_source",
            },
        )

        if not created and (
            placement.year_number,
            placement.semester_number,
        ) != (
            data["unit"]["year"],
            data["unit"]["semester"],
        ):
            raise CommandError(
                "Archive placement conflicts with the curriculum"
            )

        sources = {}

        for item in data["sources"]:
            sources[item["key"]], _ = (
                SourceDocument.objects.get_or_create(
                    unit=unit,
                    title=item["title"],
                    source_url=item["url"],
                    defaults={
                        "source_kind": item["kind"],
                        "source_year": item.get("year"),
                        "rights_status": (
                            SourceDocument.Rights.RESTRICTED
                        ),
                        "notes": (
                            "Source evidence for independent practice; "
                            "do not republish original material."
                        ),
                    },
                )
            )

        template, _ = ExamTemplate.objects.get_or_create(
            unit=unit,
            title=data["exam"]["title"],
        )

        version, _ = ExamVersion.objects.get_or_create(
            template=template,
            number=1,
            defaults={
                "duration_seconds": (
                    data["exam"]["duration_seconds"]
                ),
                "instructions": data["exam"]["instructions"],
            },
        )

        if version.is_published:
            self.stdout.write(self.style.SUCCESS(
                "Already published; left unchanged."
            ))
            return

        if version.items.exists():
            if not draft_matches(version, data):
                raise CommandError(
                    "Existing draft differs from dataset. "
                    "Create a reviewed v2 instead of overwriting it."
                )

        else:
            for position, item in enumerate(
                data["questions"], 1
            ):
                topic, _ = Topic.objects.get_or_create(
                    unit=unit,
                    parent=None,
                    title=item["topic"],
                    defaults={"position": position},
                )

                ref, _ = SourceReference.objects.get_or_create(
                    document=sources[item["source"]],
                    section_label=item["section"],
                )

                question_id = stable_id(
                    data["dataset"], item["key"], "question"
                )
                revision_id = stable_id(
                    data["dataset"], item["key"], "revision"
                )

                if (
                    Question.objects.filter(
                        pk=question_id
                    ).exists()
                    or QuestionRevision.objects.filter(
                        pk=revision_id
                    ).exists()
                ):
                    raise CommandError(
                        "Partial seed data found; "
                        "manual investigation required"
                    )

                question = Question.objects.create(
                    pk=question_id,
                    topic=topic,
                )

                revision = QuestionRevision.objects.create(
                    pk=revision_id,
                    question=question,
                    number=1,
                    kind=item["kind"],
                    provenance=(
                        QuestionRevision.Provenance.ORIGINAL
                    ),
                    prompt=item["prompt"],
                    explanation=item["explanation"],
                    max_marks=Decimal(item["marks"]),
                    source_reference=ref,
                )

                if item["kind"] == "single_choice":
                    for i, label in enumerate(item["options"]):
                        ChoiceOption.objects.create(
                            revision=revision,
                            position=i + 1,
                            text=label,
                            is_correct=(
                                i == item["correct_index"]
                            ),
                        )
                else:
                    for i, criterion in enumerate(
                        item["rubric"], 1
                    ):
                        RubricCriterion.objects.create(
                            revision=revision,
                            position=i,
                            description=criterion["description"],
                            max_marks=Decimal(
                                criterion["marks"]
                            ),
                        )

                ExamQuestion.objects.create(
                    version=version,
                    revision=revision,
                    position=position,
                )

        if options["publish"]:
            for item in version.items.select_related("revision"):
                revision = item.revision

                if (
                    revision.status
                    != QuestionRevision.Status.PUBLISHED
                ):
                    revision.reviewed_by = reviewer
                    revision.status = (
                        QuestionRevision.Status.PUBLISHED
                    )
                    revision.save()

            version.is_published = True
            version.save()

            self.stdout.write(self.style.SUCCESS(
                f"{options['unit']} pilot published."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"{options['unit']} draft ready: "
                "12 questions, 20 marks. "
                "Review before publication."
            ))
