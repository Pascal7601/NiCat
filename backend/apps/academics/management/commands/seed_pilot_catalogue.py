"""Import only the 3-unit HISTORICAL/UNVERIFIED pilot catalogue. No exam content."""
import csv
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.academics.models import University, Programme, CurriculumVersion, Unit, CurriculumUnit, Topic

class Command(BaseCommand):
    help = "Seed unverified archive pilot units and topics (idempotent)."

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR).parent / "data" / "pilot_topic_map.csv"
        university, _ = University.objects.get_or_create(name="Multimedia University of Kenya",
            defaults={"abbreviation": "MMU", "verified": False})
        programme, _ = Programme.objects.get_or_create(university=university,
            name="Bachelor of Business Information Technology", defaults={"code": "BBIT"})
        curriculum, _ = CurriculumVersion.objects.get_or_create(programme=programme,
            label="Shared archive 2020–2023 (unverified)",
            defaults={"is_officially_verified": False})
        with path.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                unit, _ = Unit.objects.get_or_create(slug="mmu-bbit-" + slugify(row["unit_name"]),
                    defaults={"title": row["unit_name"]})
                year, semester = map(int, row["semester"].split("."))
                CurriculumUnit.objects.get_or_create(curriculum_version=curriculum, unit=unit,
                    defaults={"year_number": year, "semester_number": semester,
                              "displayed_code": row["historical_unit_code"],
                              "code_verification_status": "historical_unverified"})
                Topic.objects.get_or_create(unit=unit, parent=None, title=row["proposed_topic"],
                    defaults={"position": 0})
        self.stdout.write(self.style.SUCCESS("Historical pilot catalogue ready (NOT verified/current)"))
