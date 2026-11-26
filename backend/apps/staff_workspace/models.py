"""Append-only rights decisions for the staff workspace. No document uploads."""
import uuid

from django.conf import settings
from django.db import models


class SourceRightsDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey("resources.SourceDocument", on_delete=models.PROTECT, related_name="staff_rights_decisions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="source_rights_decisions")
    previous_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    rationale = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("review_source_rights", "Can make evidence-backed source rights decisions")]

    def __str__(self):
        return f"{self.document_id}: {self.previous_status} -> {self.new_status}"
