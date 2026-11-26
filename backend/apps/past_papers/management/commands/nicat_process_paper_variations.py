"""Bounded local worker. Run intentionally, never from public HTTP requests."""
from django.core.management.base import BaseCommand
from apps.past_papers.models import PaperVariationJob
from apps.past_papers.services import process_variation_job


class Command(BaseCommand):
    help = "Process queued private past-paper practice variation jobs"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=3)

    def handle(self, *args, **options):
        limit = min(20, max(0, options["limit"]))
        ids = list(PaperVariationJob.objects.filter(state=PaperVariationJob.State.QUEUED).order_by("created_at")[:limit].values_list("pk", flat=True))
        for job_id in ids:
            result = process_variation_job(job_id)
            self.stdout.write(f"{job_id}: {result}")
        if not ids:
            self.stdout.write("No queued paper-variation jobs")
