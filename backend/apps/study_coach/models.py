"""Student follow-up questions and strict, database-backed daily quotas.

A draft NEVER becomes a student-visible answer without academic publication.
No grade, question key or raw answer is stored here.
"""
from uuid import uuid4

from django.conf import settings
from django.db import models


class TutorFollowUp(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Awaiting academic review"
        PUBLISHED = "published", "Reviewer-approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="study_followups",
    )
    attempt_question = models.ForeignKey(
        "attempts.AttemptQuestion", on_delete=models.PROTECT,
        related_name="study_followups",
    )
    explanation = models.ForeignKey(
        "study_tutor.TutorExplanation", on_delete=models.PROTECT,
        related_name="followups",
    )
    question = models.CharField(max_length=500)
    draft_answer = models.TextField(blank=True)
    published_answer = models.TextField(blank=True)
    citations = models.ManyToManyField(
        "study_tutor.SourceExcerpt", related_name="study_followups", blank=True,
    )
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    quota_day = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="reviewed_study_followups", null=True, blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["student", "quota_day"], name="coach_student_day_idx")]

    def __str__(self):
        return f"{self.student_id} / {self.attempt_question_id} / {self.state}"


class TutorDailyBudget(models.Model):
    """Atomic local operation-count ceiling; NOT monetary spend accounting."""
    day = models.DateField(primary_key=True)
    requests = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.day}: {self.requests} requests"
