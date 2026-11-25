"""Original student-written revision notes; intentionally NOT indexed or public."""
import uuid
from django.conf import settings
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from apps.academics.models import Unit


class Contribution(models.Model):
    class State(models.TextChoices):
        PENDING = "pending_review", "Pending review"
        RIGHTS_HOLD = "rights_hold", "Rights hold"
        APPROVED = "approved", "Approved for later publication"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="contributions")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="student_contributions")
    title = models.CharField(max_length=160)
    body = models.TextField(validators=[MinLengthValidator(100), MaxLengthValidator(6000)])
    # This first slice accepts author-written text only, no files or third-party past papers.
    author_declaration = models.BooleanField(default=False)
    allow_display = models.BooleanField(default=False)
    allow_ai_use = models.BooleanField(default=False)
    content_sha256 = models.CharField(max_length=64, db_index=True)
    possible_duplicate = models.BooleanField(default=False)
    state = models.CharField(max_length=24, choices=State.choices, default=State.PENDING, db_index=True)
    rights_review_note = models.TextField(blank=True)
    academic_review_note = models.TextField(blank=True)
    rights_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="rights_reviewed_contributions")
    rights_reviewed_at = models.DateTimeField(null=True, blank=True)
    academic_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="academically_reviewed_contributions")
    academic_reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("review_contribution_rights", "Can verify student contribution rights"),
            ("review_contribution_content", "Can approve student contribution academic content"),
        ]
        indexes = [models.Index(fields=["student", "created_at"], name="contrib_student_created_idx")]

    def __str__(self):
        return self.title


class ContributionDecision(models.Model):
    """Append-only history written by services; no direct admin editing."""
    class Action(models.TextChoices):
        RIGHTS_CLEARED = "rights_cleared", "Rights cleared"
        RIGHTS_HOLD = "rights_hold", "Rights hold"
        APPROVED = "approved", "Academic approval"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contribution = models.ForeignKey(Contribution, on_delete=models.PROTECT, related_name="decisions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="contribution_decisions")
    action = models.CharField(max_length=30, choices=Action.choices)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
