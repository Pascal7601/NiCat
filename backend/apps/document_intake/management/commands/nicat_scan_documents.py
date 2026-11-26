"""Manual/worker-run scanner. No bypass if clamscan or extraction fails."""
from django.core.management.base import BaseCommand
from apps.document_intake.models import DocumentSubmission
from apps.document_intake.services import process_one


class Command(BaseCommand):
    help = "Scan quarantined documents and extract limited text (needs ClamAV and pypdf)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        qs = DocumentSubmission.objects.filter(
            scan_state__in=[DocumentSubmission.ScanState.PENDING, DocumentSubmission.ScanState.ERROR],
        ).exclude(state__in=[DocumentSubmission.State.WITHDRAWN, DocumentSubmission.State.REJECTED])[:min(max(options["limit"], 0), 100)]
        ids = list(qs.values_list("pk", flat=True))
        for doc_id in ids:
            result = process_one(doc_id)
            self.stdout.write(f"{doc_id}: {result}")
