"""University → programme → versioned curricula → units → topics.

Archive placement is *evidence*; it is not a current 2026 official curriculum.
"""
import uuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    class Meta:
        abstract = True

class University(UUIDModel):
    name = models.CharField(max_length=255, unique=True)
    abbreviation = models.CharField(max_length=30, blank=True)
    verified = models.BooleanField(default=False)
    def __str__(self): return self.name

class Programme(UUIDModel):
    university = models.ForeignKey(University, on_delete=models.PROTECT, related_name="programmes")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["university", "name"], name="unique_university_programme")]
    def __str__(self): return self.name

class CurriculumVersion(UUIDModel):
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="curricula")
    label = models.CharField(max_length=150)
    is_officially_verified = models.BooleanField(default=False)
    reference_url = models.URLField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["programme", "label"], name="unique_programme_curriculum_version")]
    def __str__(self): return f"{self.programme.name}: {self.label}"

class Unit(UUIDModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    def __str__(self): return self.title

class CurriculumUnit(UUIDModel):
    curriculum_version = models.ForeignKey(CurriculumVersion, on_delete=models.PROTECT, related_name="placements")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="placements")
    year_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(8)])
    semester_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    displayed_code = models.CharField(max_length=60, blank=True)
    code_verification_status = models.CharField(max_length=30, default="unverified")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["curriculum_version", "unit"], name="unique_curriculum_unit")]
        ordering = ["year_number", "semester_number", "unit__title"]

class Topic(UUIDModel):
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="topics")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, related_name="children", blank=True, null=True)
    title = models.CharField(max_length=255)
    position = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ["position", "title"]
        constraints = [models.UniqueConstraint(fields=["unit", "parent", "title"], name="unique_topic_with_parent")]
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError("A topic cannot be its own parent")
        if self.parent_id and self.parent.unit_id != self.unit_id:
            raise ValidationError("Parent must be in the same unit")
    def __str__(self): return self.title
