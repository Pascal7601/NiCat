"""Private, reviewer-only AI essay scoring proposals. Never included in student APIs."""
from django.conf import settings
from django.db import models

from apps.academics.models import UUIDModel


class AIMarkingSuggestion(UUIDModel):
    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Awaiting human marking"
        ACCEPTED = "accepted", "Reviewer chose same mark"
        OVERRIDDEN = "overridden", "Reviewer chose different mark"

    grade_item = models.OneToOneField(
        "attempts.GradeItem", on_delete=models.PROTECT, related_name="ai_suggestion"
    )
    proposed_marks = models.DecimalField(max_digits=6, decimal_places=2)
    breakdown = models.JSONField(default=list)
    feedback = models.TextField()
    model_name = models.CharField(max_length=100)
    answer_sha256 = models.CharField(max_length=64)
    prompt_version = models.CharField(max_length=30, default="essay-review-v1")
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ai_suggestions_requested"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    review_status = models.CharField(
        max_length=16, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="ai_suggestions_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI marking proposal (not a final grade)"
