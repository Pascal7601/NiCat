"""Private past-paper OCR corrections and separately reviewed practice variations.

No model here is a public QuestionRevision. Import/publication is deliberately
outside this Sprint 15 verification boundary.
"""
import uuid
from django.conf import settings
from django.db import models


class PaperQuestionDraft(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Needs visual comparison with original paper"
        VERIFIED = "verified", "Verified against original paper"
        REJECTED = "rejected", "Rejected OCR question"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey("document_intake.DocumentSubmission", on_delete=models.PROTECT, related_name="paper_questions")
    position = models.PositiveSmallIntegerField()
    source_sha256 = models.CharField(max_length=64)
    extracted_sha256 = models.CharField(max_length=64)
    original_ocr_text = models.TextField(blank=True)
    corrected_text = models.TextField()
    page_number = models.PositiveSmallIntegerField(null=True, blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    topic = models.ForeignKey("academics.Topic", on_delete=models.PROTECT, null=True, blank=True)
    # Verified against a marking scheme, a lecturer's reference, or another checked resource.
    verified_answer_context = models.TextField(blank=True)
    flags = models.JSONField(default=list, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    extracted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="paper_extractions")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="verified_paper_questions")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("position", "created_at")
        constraints = [models.UniqueConstraint(fields=["document", "position"], name="paper_question_doc_position_uq")]
        permissions = [
            ("extract_paper_questions", "May extract and correct past-paper questions"),
            ("verify_paper_questions", "May verify corrected past-paper questions"),
        ]


class PaperVariationJob(models.Model):
    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Generation failed"
        BLOCKED = "blocked", "Source invalidated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(PaperQuestionDraft, on_delete=models.PROTECT, related_name="variation_jobs")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    provider = models.CharField(max_length=32)
    model_name = models.CharField(max_length=100, blank=True)
    kind = models.CharField(max_length=8, choices=[("mcq", "MCQ"), ("short", "Short answer"), ("essay", "Essay")])
    difficulty = models.CharField(max_length=8, choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard")])
    count = models.PositiveSmallIntegerField(default=1)
    source_sha256 = models.CharField(max_length=64)
    extracted_sha256 = models.CharField(max_length=64)
    verified_question_sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=12, choices=State.choices, default=State.QUEUED, db_index=True)
    failure_code = models.CharField(max_length=48, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        permissions = [("request_paper_variations", "May request variations of verified past-paper questions")]


class PaperVariationCandidate(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Needs academic review"
        APPROVED = "approved", "Approved private candidate"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(PaperVariationJob, on_delete=models.PROTECT, related_name="candidates")
    position = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=8)
    prompt = models.TextField()
    options = models.JSONField(default=list, blank=True)
    correct_index = models.PositiveSmallIntegerField(null=True, blank=True)
    explanation = models.TextField()
    rubric = models.JSONField(default=list, blank=True)
    evidence_quote = models.TextField()
    validation_errors = models.JSONField(default=list, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position",)
        constraints = [models.UniqueConstraint(fields=["job", "position"], name="paper_var_job_position_uq")]
        permissions = [("review_paper_variations", "May review practice variations from past papers")]


class PaperReviewEvent(models.Model):
    """Append-only private audit for OCR verification and variations."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey("document_intake.DocumentSubmission", on_delete=models.PROTECT, related_name="paper_review_events")
    question = models.ForeignKey(PaperQuestionDraft, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    candidate = models.ForeignKey(PaperVariationCandidate, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
