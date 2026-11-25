"""Private original-document intake. Not a public library or AI retrieval index."""
import uuid
from django.conf import settings
from django.db import models
from apps.academics.models import Programme, Unit


class DocumentSubmission(models.Model):
    class State(models.TextChoices):
        PENDING_SCAN = "pending_scan", "Waiting for security scanning"
        NEEDS_MAPPING = "needs_mapping", "Unit verification needed"
        PENDING_REVIEW = "pending_review", "Rights and academic review"
        RIGHTS_HOLD = "rights_hold", "Rights clarification required"
        APPROVED = "approved_for_questions", "Approved for future question drafting"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        PROCESSING_ERROR = "processing_error", "Processing problem"

    class DocumentType(models.TextChoices):
        OWN_NOTES = "original_notes", "My own original notes"
        AUTHORIZED_NOTES = "licensed_notes", "Notes shared with permission"
        AUTHORIZED_PAPER = "licensed_paper", "Past paper shared with permission"
        OTHER_LICENSED = "other_licensed", "Other licensed academic material"

    class RightsBasis(models.TextChoices):
        AUTHOR = "own_work", "I authored the material"
        PERMISSION = "permission", "I have explicit permission to share/use it"
        LICENSE = "open_license", "I verified an applicable open license"

    class ScanState(models.TextChoices):
        PENDING = "pending", "Not scanned"
        PROCESSING = "processing", "Processing"
        CLEAN = "clean", "Clean scan"
        BLOCKED = "blocked", "Threat detected"
        ERROR = "error", "Scanner unavailable/error"

    class ExtractionState(models.TextChoices):
        PENDING = "pending", "Not extracted"
        DONE = "done", "Text extracted"
        ERROR = "error", "Extraction failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="document_submissions")
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="document_submissions")
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name="document_submissions")
    # Not a new official Unit; only verified academic editors may resolve it.
    suggested_unit_title = models.CharField(max_length=200, blank=True)
    suggested_unit_code = models.CharField(max_length=50, blank=True)
    year_number = models.PositiveSmallIntegerField(null=True, blank=True)
    semester_number = models.PositiveSmallIntegerField(null=True, blank=True)
    title = models.CharField(max_length=180)
    description = models.CharField(max_length=1000, blank=True)
    suggested_topics = models.CharField(max_length=350, blank=True)
    document_type = models.CharField(max_length=24, choices=DocumentType.choices)
    rights_basis = models.CharField(max_length=24, choices=RightsBasis.choices)
    rights_evidence = models.CharField(max_length=1000, blank=True)
    author_or_owner = models.CharField(max_length=180)
    permit_question_generation = models.BooleanField(default=False)
    permit_resource_display = models.BooleanField(default=False)
    permit_tutor_use = models.BooleanField(default=False)
    original_filename = models.CharField(max_length=180)
    stored_key = models.CharField(max_length=72, unique=True)
    file_type = models.CharField(max_length=8, choices=[("pdf", "PDF"), ("txt", "Plain text")])
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64, db_index=True)
    possible_duplicate = models.BooleanField(default=False)
    scan_state = models.CharField(max_length=16, choices=ScanState.choices, default=ScanState.PENDING)
    extraction_state = models.CharField(max_length=16, choices=ExtractionState.choices, default=ExtractionState.PENDING)
    # Private, bounded, never serialized to students and never added to Tutor by this sprint.
    extracted_text = models.TextField(blank=True)
    page_count = models.PositiveSmallIntegerField(null=True, blank=True)
    state = models.CharField(max_length=32, choices=State.choices, default=State.PENDING_SCAN, db_index=True)
    rights_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="document_rights_reviews")
    rights_reviewed_at = models.DateTimeField(null=True, blank=True)
    academic_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="document_academic_reviews")
    academic_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("review_document_rights", "Can verify rights for uploaded academic documents"),
            ("review_document_academic", "Can approve academic documents for future question drafting"),
            ("map_document_units", "Can map submitted documents to verified units"),
        ]
        indexes = [models.Index(fields=["student", "created_at"], name="docint_student_created_idx")]

    def __str__(self):
        return self.title


class DocumentReviewEvent(models.Model):
    """Append-only decision and mapping event; never editable from Django Admin."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(DocumentSubmission, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="document_review_events")
    action = models.CharField(max_length=40)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
