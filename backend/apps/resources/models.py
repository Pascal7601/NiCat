"""Source provenance; source documents are not public downloads."""
from django.db import models
from apps.academics.models import UUIDModel, Unit

class SourceDocument(UUIDModel):
    class Rights(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        RESTRICTED = "restricted", "Restricted"
        ALLOWED = "allowed", "Permission confirmed"
    class Kind(models.TextChoices):
        COURSE_OUTLINE = "course_outline", "Course outline"
        LECTURE_NOTES = "lecture_notes", "Lecture notes"
        PAST_CAT = "past_cat", "Past CAT"
        PAST_EXAM = "past_exam", "Past exam"
        REVISION = "revision", "Revision questions"
        REFERENCE = "reference", "Reference material"
    title = models.CharField(max_length=500)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True)
    source_kind = models.CharField(max_length=40, choices=Kind.choices)
    source_year = models.PositiveSmallIntegerField(null=True, blank=True)
    source_url = models.URLField(max_length=1000, blank=True)
    rights_status = models.CharField(max_length=20, choices=Rights.choices, default=Rights.UNKNOWN)
    notes = models.TextField(blank=True)
    def __str__(self): return self.title

class SourceReference(UUIDModel):
    document = models.ForeignKey(SourceDocument, on_delete=models.PROTECT, related_name="references")
    page_label = models.CharField(max_length=80, blank=True)
    section_label = models.CharField(max_length=200, blank=True)
    excerpt_fingerprint = models.CharField(max_length=128, blank=True)
