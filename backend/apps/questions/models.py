"""Source-backed question revisions, with immutable published versions."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.academics.models import UUIDModel, Topic
from apps.resources.models import SourceReference

class Question(UUIDModel):
    topic = models.ForeignKey(Topic, on_delete=models.PROTECT, related_name="questions")
    is_active = models.BooleanField(default=True)

class QuestionRevision(UUIDModel):
    class Kind(models.TextChoices):
        SINGLE_CHOICE = "single_choice", "Single choice"
        WRITTEN = "written", "Written"
        CODE_TEXT = "code_text", "Code as text"
        NUMERIC = "numeric", "Numeric"
        CASE_STUDY = "case_study", "Case study"
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In review"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"
    class Provenance(models.TextChoices):
        ORIGINAL = "original_practice", "Independently authored"
        PAST_PAPER = "past_paper", "Historic past-paper question"
        AI_DRAFT = "ai_draft", "AI-assisted draft"
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="revisions")
    number = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    provenance = models.CharField(max_length=25, choices=Provenance.choices)
    prompt = models.TextField()
    max_marks = models.DecimalField(max_digits=6, decimal_places=2)
    explanation = models.TextField(blank=True)
    source_reference = models.ForeignKey(SourceReference, on_delete=models.PROTECT, null=True, blank=True)
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["question", "number"], name="unique_question_revision")]
    def clean(self):
        if self.max_marks is not None and self.max_marks <= 0:
            raise ValidationError("Question marks must be positive")
        if self.status == self.Status.PUBLISHED and not self.reviewed_by_id:
            raise ValidationError("Published questions require a reviewer")
        if self.provenance == self.Provenance.PAST_PAPER and not self.source_reference_id:
            raise ValidationError("Historical-paper questions require source evidence")
        if (self.status == self.Status.PUBLISHED and self.provenance == self.Provenance.PAST_PAPER
                and self.source_reference_id
                and self.source_reference.document.rights_status != "allowed"):
            raise ValidationError("Publication permission is required for verbatim historical content")

    def validate_publication(self):
        if self.status != self.Status.PUBLISHED or not self.pk:
            return
        if self.kind == self.Kind.SINGLE_CHOICE:
            options = list(self.options.all())
            if len(options) < 2 or sum(1 for option in options if option.is_correct) != 1:
                raise ValidationError("Published MCQ needs at least two options and one correct answer")
        else:
            from decimal import Decimal
            criteria = list(self.rubric.all())
            if not criteria or sum((c.max_marks for c in criteria), Decimal("0")) != self.max_marks:
                raise ValidationError("Published written questions require a rubric summing to total marks")

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk, status=self.Status.PUBLISHED).exists():
            raise ValidationError("Published revisions are immutable: create a new revision")
        self.full_clean()
        self.validate_publication()
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

class ChoiceOption(UUIDModel):
    revision = models.ForeignKey(QuestionRevision, on_delete=models.PROTECT, related_name="options")
    text = models.TextField()
    position = models.PositiveSmallIntegerField()
    is_correct = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["revision", "position"], name="unique_option_position")]
    def save(self, *args, **kwargs):
        if self.revision.status == QuestionRevision.Status.PUBLISHED:
            raise ValidationError("Published answer options are immutable")
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        if self.revision.status == QuestionRevision.Status.PUBLISHED:
            raise ValidationError("Published answer options are immutable")
        return super().delete(*args, **kwargs)

class RubricCriterion(UUIDModel):
    revision = models.ForeignKey(QuestionRevision, on_delete=models.PROTECT, related_name="rubric")
    description = models.TextField()
    max_marks = models.DecimalField(max_digits=6, decimal_places=2)
    position = models.PositiveSmallIntegerField()
    def clean(self):
        if self.max_marks is not None and self.max_marks <= 0:
            raise ValidationError("Rubric criterion marks must be positive")
    def save(self, *args, **kwargs):
        if self.revision.status == QuestionRevision.Status.PUBLISHED:
            raise ValidationError("Published rubrics are immutable")
        self.full_clean()
        super().save(*args, **kwargs)
    def delete(self, *args, **kwargs):
        if self.revision.status == QuestionRevision.Status.PUBLISHED:
            raise ValidationError("Published rubrics are immutable")
        return super().delete(*args, **kwargs)
