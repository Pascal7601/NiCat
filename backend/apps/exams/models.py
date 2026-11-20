"""Exam template revisions: publisher-owned configuration, frozen on publish."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from apps.academics.models import UUIDModel, Unit
from apps.questions.models import QuestionRevision

class ExamTemplate(UUIDModel):
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="exam_templates")
    title = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

class ExamVersion(UUIDModel):
    template = models.ForeignKey(ExamTemplate, on_delete=models.PROTECT, related_name="versions")
    number = models.PositiveSmallIntegerField()
    duration_seconds = models.PositiveIntegerField()
    instructions = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    show_explanations_after_submit = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["template", "number"], name="unique_exam_version")]
    def clean(self):
        if self.duration_seconds < 60:
            raise ValidationError("Exam duration must be at least 60 seconds")
    def validate_publication(self):
        if not self.is_published:
            return
        if not type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Save the draft exam version before publishing")
        items = list(self.items.select_related("revision__question__topic"))
        if not items:
            raise ValidationError("Cannot publish an exam without questions")
        revision_ids = [item.revision_id for item in items]
        if len(revision_ids) != len(set(revision_ids)):
            raise ValidationError("The same question revision cannot appear twice in an exam")
        for item in items:
            if item.revision.status != QuestionRevision.Status.PUBLISHED:
                raise ValidationError("Exam contains an unpublished question")
            if item.revision.question.topic.unit_id != self.template.unit_id:
                raise ValidationError("Exam contains a question from another unit")

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk, is_published=True).exists():
            raise ValidationError("Published exam versions are immutable")
        self.full_clean()
        self.validate_publication()
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

class ExamQuestion(UUIDModel):
    version = models.ForeignKey(ExamVersion, on_delete=models.PROTECT, related_name="items")
    revision = models.ForeignKey(QuestionRevision, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()
    class Meta:
        constraints = [models.UniqueConstraint(fields=["version", "position"], name="unique_exam_item_position")]
        ordering = ["position"]
    
    def clean(self):
        # Draft exams may contain unpublished question revisions.
        # ExamVersion.validate_publication() ensures all revisions
        # are published before the exam itself can be published.

        if (
            self.version_id
            and self.revision_id
            and self.version.template.unit_id
            != self.revision.question.topic.unit_id
        ):
            raise ValidationError(
                "Question belongs to a different unit"
            )

    def save(self,*args,**kwargs):
        if self.version.is_published:
            raise ValidationError("Cannot edit published exam questions")
        self.full_clean()
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):
        if self.version.is_published:
            raise ValidationError("Cannot delete published exam questions")
        return super().delete(*args,**kwargs)
