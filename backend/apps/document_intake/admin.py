from django.contrib import admin
from .models import DocumentSubmission, DocumentReviewEvent


@admin.register(DocumentSubmission)
class DocumentSubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "programme", "unit", "state", "scan_state", "possible_duplicate", "created_at")
    list_filter = ("state", "scan_state", "document_type", "programme")
    search_fields = ("title", "original_filename", "sha256")
    readonly_fields = [field.name for field in DocumentSubmission._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentReviewEvent)
class DocumentReviewEventAdmin(admin.ModelAdmin):
    list_display = ("document", "actor", "action", "created_at")
    readonly_fields = [field.name for field in DocumentReviewEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
