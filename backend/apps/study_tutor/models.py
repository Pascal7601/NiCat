"""Approved excerpts and versioned, human-published AI explanations.

This app is additive and never modifies attempts, answer keys or grades.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.academics.models import UUIDModel


class SourceExcerpt(UUIDModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Awaiting source review"
        APPROVED = "approved", "Approved for tutor use"
        WITHDRAWN = "withdrawn", "Withdrawn"

    reference = models.ForeignKey(
        "resources.SourceReference", on_delete=models.PROTECT, related_name="tutor_excerpts"
    )
    topic = models.ForeignKey("academics.Topic", on_delete=models.PROTECT, related_name="tutor_excerpts")
    text = models.TextField(help_text="Short reviewed excerpt, not an entire copyrighted document")
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="approved_tutor_excerpts",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["topic_id", "created_at"]
        indexes = [models.Index(fields=["topic", "state"], name="tutor_topic_state_idx")]
        permissions = [("approve_tutor_content", "May approve tutor sources and explanations")]

    def clean(self):
        if not 30 <= len(self.text.strip()) <= 5000:
            raise ValidationError("A source excerpt must contain 30–5000 characters")
        if self.reference_id and self.topic_id:
            document = self.reference.document
            if document.unit_id != self.topic.unit_id:
                raise ValidationError("Source document and topic must belong to the same unit")
            if self.state == self.State.APPROVED and document.rights_status != "allowed":
                raise ValidationError("Source rights must be explicitly allowed before approval")
        if self.state == self.State.APPROVED and (not self.approved_by_id or not self.approved_at):
            raise ValidationError("Approval must identify a reviewer and time")
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values("state", "reference_id", "topic_id", "text").first()
            if previous and previous["state"] != self.State.DRAFT:
                if any(previous[name] != getattr(self, name) for name in ("reference_id", "topic_id", "text")):
                    raise ValidationError("Reviewed source content is immutable; create a new excerpt")
                if previous["state"] == self.State.WITHDRAWN and self.state != self.State.WITHDRAWN:
                    raise ValidationError("A withdrawn source cannot be reactivated")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.topic.title}: {self.reference.document.title} ({self.state})"


class TutorExplanation(UUIDModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Academic review required"
        PUBLISHED = "published", "Reviewer-approved"
        WITHDRAWN = "withdrawn", "Withdrawn"

    revision = models.ForeignKey(
        "questions.QuestionRevision", on_delete=models.PROTECT, related_name="tutor_explanations"
    )
    explanation = models.TextField()
    common_mistake = models.TextField()
    practice_tip = models.TextField()
    citations = models.ManyToManyField(SourceExcerpt, related_name="tutor_explanations")
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    version = models.PositiveIntegerField(default=1)
    prompt_version = models.CharField(max_length=32, default="grounded-explanation-v1")
    model_name = models.CharField(max_length=100)
    source_fingerprint = models.CharField(max_length=64)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="drafted_tutor_explanations"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="published_tutor_explanations",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["revision"], condition=Q(state="published"),
                name="unique_published_tutor_explanation_per_revision",
            ),
            models.UniqueConstraint(fields=["revision", "version"], name="unique_tutor_explanation_version"),
        ]

    def clean(self):
        if not 30 <= len(self.explanation.strip()) <= 5000:
            raise ValidationError("Explanation must contain 30–5000 characters")
        if not 10 <= len(self.common_mistake.strip()) <= 1500:
            raise ValidationError("Common mistake must contain 10–1500 characters")
        if not 10 <= len(self.practice_tip.strip()) <= 1500:
            raise ValidationError("Practice tip must contain 10–1500 characters")
        if self.state == self.State.PUBLISHED and (not self.approved_by_id or not self.approved_at):
            raise ValidationError("Published explanations need academic reviewer approval")
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).values(
                "state", "revision_id", "explanation", "common_mistake", "practice_tip",
                "source_fingerprint", "version"
            ).first()
            if old and old["state"] != self.State.DRAFT:
                immutable = ("revision_id", "explanation", "common_mistake", "practice_tip", "source_fingerprint", "version")
                if any(old[key] != getattr(self, key) for key in immutable):
                    raise ValidationError("Published explanations are immutable; generate a new version")
                if old["state"] == self.State.WITHDRAWN and self.state != self.State.WITHDRAWN:
                    raise ValidationError("Withdrawn explanations cannot be republished")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.revision_id} / v{self.version} / {self.state}"
