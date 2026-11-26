"""Private, source-linked question candidates. These are NOT exam questions."""
import uuid
from django.conf import settings
from django.db import models


class ExternalSourceAuthorization(models.Model):
    """Document-specific permission for sending text to a configured AI vendor."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField("document_intake.DocumentSubmission", on_delete=models.PROTECT, related_name="external_question_ai_authorization")
    provider = models.CharField(max_length=40)
    approved_source_hash = models.CharField(max_length=64)
    approved_extracted_sha256 = models.CharField(max_length=64)
    rationale = models.TextField()
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    approved_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [("approve_external_question_ai", "May authorize document text for external question AI processing")]


class QuestionGenerationJob(models.Model):
    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"
        BLOCKED = "blocked", "Source withdrawn or changed"

    class Kind(models.TextChoices):
        MCQ = "mcq", "Multiple choice"
        SHORT = "short", "Short answer"
        ESSAY = "essay", "Essay"
        MIXED = "mixed", "Mixed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey("document_intake.DocumentSubmission", on_delete=models.PROTECT, related_name="question_generation_jobs")
    topic = models.ForeignKey("academics.Topic", on_delete=models.PROTECT)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="question_generation_jobs")
    count = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=8, choices=Kind.choices)
    difficulty = models.CharField(max_length=12, choices=[("easy", "Easy"), ("medium", "Medium"), ("hard", "Hard"), ("mixed", "Mixed")])
    provider = models.CharField(max_length=32)
    model_name = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=20, default="s14-v1")
    source_sha256 = models.CharField(max_length=64)
    extracted_sha256 = models.CharField(max_length=64)
    state = models.CharField(max_length=12, choices=State.choices, default=State.QUEUED, db_index=True)
    failure_code = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("request_question_generation", "May request source-grounded question generation")]


class GeneratedQuestionCandidate(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Needs academic review"
        APPROVED = "approved", "Reviewed and approved"
        REJECTED = "rejected", "Rejected"
        IMPORTED = "imported", "Imported into question bank"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(QuestionGenerationJob, on_delete=models.PROTECT, related_name="candidates")
    position = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=8, choices=[("mcq", "MCQ"), ("short", "Short answer"), ("essay", "Essay")])
    prompt = models.TextField()
    options = models.JSONField(default=list, blank=True)
    correct_index = models.PositiveSmallIntegerField(null=True, blank=True)
    explanation = models.TextField()
    rubric = models.JSONField(default=list, blank=True)
    evidence_quote = models.TextField()
    validation_errors = models.JSONField(default=list, blank=True)
    prompt_sha256 = models.CharField(max_length=64, db_index=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT, db_index=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    bank_revision = models.OneToOneField("questions.QuestionRevision", null=True, blank=True, on_delete=models.PROTECT, related_name="generation_candidate")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [models.UniqueConstraint(fields=["job", "position"], name="qgen_unique_position")]
        permissions = [
            ("review_question_candidate", "May review generated question candidates"),
            ("import_question_candidate", "May import reviewed questions into question bank"),
        ]


class QuestionGenerationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(GeneratedQuestionCandidate, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
