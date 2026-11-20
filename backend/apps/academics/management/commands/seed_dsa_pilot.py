"""Idempotent, review-gated demo data loader for the NiCat DSA pilot."""
import json
import uuid
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.academics.models import CurriculumUnit, CurriculumVersion, Programme, Topic, Unit, University
from apps.exams.models import ExamQuestion, ExamTemplate, ExamVersion
from apps.questions.models import ChoiceOption, Question, QuestionRevision, RubricCriterion
from apps.resources.models import SourceDocument, SourceReference


class Command(BaseCommand):
    help = "Seed an independently authored MMU DSA pilot; --publish requires verified reviewer identity."

    def add_arguments(self, parser):
        parser.add_argument("--publish", action="store_true", help="Publish only after human academic review")
        parser.add_argument("--reviewer-email", type=str, default="")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[5] / "data" / "dsa_pilot_questions.json"
        # project/backend/apps/academics/management/commands/seed_dsa_pilot.py
        # parents[5] == project, independent of current working directory.
        data = json.loads(path.read_text(encoding="utf-8"))
        reviewer = None
        if options["publish"]:
            reviewer = User.objects.filter(email__iexact=options["reviewer_email"], is_active=True,
                                           is_staff=True).first()
            if reviewer is None or not reviewer.has_perm("questions.change_questionrevision"):
                raise CommandError("--publish requires an active staff reviewer with question-review permission")
            self.stdout.write(self.style.WARNING(
                "Publication asserts human academic review and content rights checks have already occurred."))

        university, _ = University.objects.get_or_create(name="Multimedia University of Kenya",
                                                         defaults={"abbreviation": "MMU"})
        programme, _ = Programme.objects.get_or_create(university=university,
            name="Bachelor of Business Information Technology", defaults={"code": "BBIT"})
        curriculum, _ = CurriculumVersion.objects.get_or_create(programme=programme,
            label="Archived study collection 2020–2023 (not official curriculum)")
        unit, _ = Unit.objects.get_or_create(slug=data["unit"]["slug"], defaults={"title": data["unit"]["title"]})
        CurriculumUnit.objects.get_or_create(curriculum_version=curriculum, unit=unit,
            defaults={"year_number": 2, "semester_number": 1, "displayed_code": "BIT 216",
                      "code_verification_status": "archival_source"})
        topic_map = {}
        source_map = {}
        for source in data["sources"]:
            source_map[source["key"]], _ = SourceDocument.objects.get_or_create(
                unit=unit, title=source["title"], source_url=source["url"],
                defaults={"source_kind": SourceDocument.Kind.COURSE_OUTLINE if source["key"] == "outline"
                          else SourceDocument.Kind.LECTURE_NOTES,
                          "source_year": source["year"], "rights_status": SourceDocument.Rights.RESTRICTED,
                          "notes": "Archive source for independent practice only, not publicly distributed."})
        template, _ = ExamTemplate.objects.get_or_create(unit=unit, title=data["exam"]["title"])
        existing_version = ExamVersion.objects.filter(template=template, number=1).first()
        if existing_version and existing_version.is_published:
            self.stdout.write(self.style.SUCCESS("Pilot exam is already published; no changes made."))
            return
        if existing_version and existing_version.items.exists():
            # Promote a *reviewed* draft, or return without modifying it.
            existing_items = list(existing_version.items.select_related("revision").order_by("position"))
            if len(existing_items) != len(data["questions"]):
                raise CommandError("Draft count differs from the reviewed pilot dataset")
            for item, record in zip(existing_items, data["questions"]):
                expected_id = uuid.uuid5(uuid.NAMESPACE_URL, "nicat/dsa-pilot/v1/" + record["key"] + "/revision")
                if (item.revision_id != expected_id or item.revision.prompt != record["prompt"]
                        or item.revision.kind != record["kind"] or item.revision.max_marks != Decimal(record["marks"])):
                    raise CommandError("Existing draft differs from the reviewed pilot content; inspect manually")
            if options["publish"]:
                for item in existing_items:
                    revision = item.revision
                    if revision.status != QuestionRevision.Status.PUBLISHED:
                        revision.reviewed_by = reviewer
                        revision.status = QuestionRevision.Status.PUBLISHED
                        revision.save()
                existing_version.is_published = True
                existing_version.save()
                self.stdout.write(self.style.SUCCESS("Existing reviewed DSA pilot published."))
            else:
                self.stdout.write("Existing DSA pilot draft unchanged; use --publish after review.")
            return
        version = existing_version or ExamVersion.objects.create(
            template=template, number=1, duration_seconds=data["exam"]["duration_seconds"],
            instructions=data["exam"]["instructions"])
        for position, datum in enumerate(data["questions"], start=1):
            if datum["topic"] not in topic_map:
                topic_map[datum["topic"]], _ = Topic.objects.get_or_create(
                    unit=unit, parent=None, title=datum["topic"], defaults={"position": len(topic_map) + 1})
            document = source_map[datum["source"]]
            ref, _ = SourceReference.objects.get_or_create(document=document, section_label=datum["section"])
            question_id = uuid.uuid5(uuid.NAMESPACE_URL, "nicat/dsa-pilot/v1/" + datum["key"] + "/question")
            revision_id = uuid.uuid5(uuid.NAMESPACE_URL, "nicat/dsa-pilot/v1/" + datum["key"] + "/revision")
            if Question.objects.filter(pk=question_id).exists() or QuestionRevision.objects.filter(pk=revision_id).exists():
                raise CommandError(f"Found orphan or mismatched DSA pilot data: {datum['key']}")
            question = Question.objects.create(id=question_id, topic=topic_map[datum["topic"]])
            revision = QuestionRevision.objects.create(
                id=revision_id,
                question=question, number=1, kind=datum["kind"],
                provenance=QuestionRevision.Provenance.ORIGINAL, prompt=datum["prompt"],
                max_marks=Decimal(datum["marks"]), source_reference=ref,
                explanation=datum["explanation"])
            if datum["kind"] == "single_choice":
                for option_position, text in enumerate(datum["options"], start=1):
                    ChoiceOption.objects.create(revision=revision, position=option_position,
                         text=text, is_correct=option_position - 1 == datum["correct_index"])
            else:
                for criterion_position, criterion in enumerate(datum["rubric"], start=1):
                    RubricCriterion.objects.create(revision=revision, position=criterion_position,
                        description=criterion["description"], max_marks=Decimal(criterion["marks"]))
            if options["publish"]:
                revision.reviewed_by = reviewer
                revision.status = QuestionRevision.Status.PUBLISHED
                revision.save()
            ExamQuestion.objects.create(version=version, revision=revision, position=position)
        if options["publish"]:
            version.is_published = True
            version.save()
        self.stdout.write(self.style.SUCCESS(
            f"DSA pilot created: {len(data['questions'])} questions, total 20 marks. "
            + ("Published" if options["publish"] else "Draft; reviewer approval required")))
