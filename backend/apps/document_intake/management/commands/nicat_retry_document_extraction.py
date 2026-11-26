"""Explicit, fail-closed retry for documents with failed PDF extraction.

Retries re-enter the normal scan pipeline so the file is checked by ClamAV
again before OCR or text extraction. Deliberately not exposed as a public API.
"""

import hashlib
import logging
from uuid import UUID

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.document_intake.models import DocumentSubmission
from apps.document_intake.services import process_one
from apps.document_intake.storage import private_path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Re-scan and retry a failed PDF extraction. Dry-run unless --confirm is passed."

    def add_arguments(self, parser):
        parser.add_argument("document_id", help="UUID of the failed document")
        parser.add_argument("--confirm", action="store_true", help="Requeue and process immediately")

    def handle(self, *args, **options):
        try:
            document_id = UUID(options["document_id"])
        except (TypeError, ValueError) as exc:
            raise CommandError("document_id must be a UUID") from exc

        if not getattr(settings, "NICAT_DOCUMENT_OCR_ENABLED", False):
            raise CommandError("OCR is disabled. Enable NICAT_DOCUMENT_OCR_ENABLED in backend settings")

        with transaction.atomic():
            try:
                entry = DocumentSubmission.objects.select_for_update().get(pk=document_id)
            except DocumentSubmission.DoesNotExist as exc:
                raise CommandError("Document does not exist") from exc

            if not (
                entry.state == DocumentSubmission.State.PROCESSING_ERROR
                and entry.scan_state == DocumentSubmission.ScanState.CLEAN
                and entry.extraction_state == DocumentSubmission.ExtractionState.ERROR
                and entry.file_type == "pdf"
            ):
                raise CommandError("Document is not an eligible PDF extraction failure")

            if entry.rights_reviewed_by_id or entry.academic_reviewed_by_id:
                raise CommandError("A reviewed document cannot be reset by this command")

            path = private_path(entry.stored_key)
            try:
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    for chunk in iter(lambda: source.read(65_536), b""):
                        digest.update(chunk)
                if digest.hexdigest() != entry.sha256:
                    raise CommandError("The private original does not match the uploaded file hash")
            except OSError as exc:
                raise CommandError("The original private file cannot be read") from exc

            if not options["confirm"]:
                self.stdout.write(
                    f"DRY RUN: document={entry.pk} state={entry.state} "
                    "may be re-scanned and OCR-extracted; pass --confirm to proceed"
                )
                return

            # Never mark a previously scanned file as clean when requeueing:
            # process_one will require a *new* successful ClamAV scan.
            entry.state = DocumentSubmission.State.PENDING_SCAN
            entry.scan_state = DocumentSubmission.ScanState.PENDING
            entry.extraction_state = DocumentSubmission.ExtractionState.PENDING
            entry.extracted_text = ""
            entry.page_count = None
            entry.save(update_fields=[
                "state", "scan_state", "extraction_state",
                "extracted_text", "page_count", "updated_at",
            ])

        logger.info("NiCat document extraction retry requested: document_id=%s", document_id)
        result = process_one(document_id)
        self.stdout.write(f"{document_id}: {result}")
        if result != "ready":
            raise CommandError("Retry failed; document remains blocked from academic review")
