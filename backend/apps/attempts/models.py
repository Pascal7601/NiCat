"""Attempt snapshots are durable and contain private server-only answer keys."""
from django.db import models
from apps.academics.models import UUIDModel
from apps.exams.models import ExamVersion

class Attempt(UUIDModel):
    class State(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        GRADING_PENDING = "grading_pending", "Grading pending"
        GRADED_FINAL = "graded_final", "Graded final"
        EXPIRED = "expired", "Expired"
    student = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="attempts")
    exam_version = models.ForeignKey(ExamVersion, on_delete=models.PROTECT)
    state = models.CharField(max_length=20, choices=State.choices, default=State.IN_PROGRESS)
    started_at = models.DateTimeField()
    deadline_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["student", "started_at"])]

class AttemptQuestion(UUIDModel):
    attempt = models.ForeignKey(Attempt, on_delete=models.PROTECT, related_name="questions")
    revision = models.ForeignKey("questions.QuestionRevision", on_delete=models.PROTECT)
    position = models.PositiveIntegerField()
    public_snapshot = models.JSONField()  # No answer keys or rubric secrets.
    private_key_snapshot = models.JSONField()  # NEVER serialize to student.
    possible_marks = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "position"], name="unique_attempt_question_position")]
        ordering = ["position"]

class StudentResponse(UUIDModel):
    attempt_question = models.OneToOneField(AttemptQuestion, on_delete=models.PROTECT, related_name="response")
    selected_option_id = models.UUIDField(null=True, blank=True)
    text_answer = models.TextField(blank=True)
    saved_at = models.DateTimeField(auto_now=True)

class Grade(UUIDModel):
    attempt = models.OneToOneField(Attempt, on_delete=models.PROTECT, related_name="grade")
    scored_marks = models.DecimalField(max_digits=8, decimal_places=2)
    scored_possible_marks = models.DecimalField(max_digits=8, decimal_places=2)
    ungraded_possible_marks = models.DecimalField(max_digits=8, decimal_places=2)
    final_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

class GradeItem(UUIDModel):
    class Status(models.TextChoices):
        PENDING = "pending_review", "Pending review"
        FINAL = "final", "Final"
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="items")
    attempt_question = models.OneToOneField(AttemptQuestion, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    student_feedback = models.TextField(blank=True, default="")
    possible_marks = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        permissions = [
            ("review_written_answers", "May mark pending written answers"),
            ("correct_final_grades", "May correct final grades with a reason"),
        ]

class GradingEvent(UUIDModel):
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, null=True, blank=True)
    reason = models.TextField()
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
