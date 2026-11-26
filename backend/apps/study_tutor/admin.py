"""Human approval remains mandatory before anything appears to a student."""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from .models import SourceExcerpt, TutorExplanation
from .services import (
    TutorConflict, approve_excerpt, publish_explanation, withdraw_excerpt, withdraw_explanation,
)


def _run_action(modeladmin, request, queryset, service):
    count = 0
    for record in queryset:
        try:
            service(actor=request.user, **{
                "excerpt_id" if isinstance(record, SourceExcerpt) else "explanation_id": record.pk
            })
            count += 1
        except (TutorConflict, PermissionDenied, ValidationError) as exc:
            modeladmin.message_user(request, f"{record.pk}: {exc}", level=messages.WARNING)
    if count:
        modeladmin.message_user(request, f"Updated {count} record(s)", level=messages.SUCCESS)


@admin.register(SourceExcerpt)
class SourceExcerptAdmin(admin.ModelAdmin):
    list_display = ["id", "topic", "reference", "state", "approved_by", "approved_at"]
    list_filter = ["state", "topic__unit"]
    search_fields = ["text", "reference__document__title", "topic__title"]
    readonly_fields = ["state", "approved_by", "approved_at", "created_at"]
    actions = ["approve_selected", "withdraw_selected"]

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.state != SourceExcerpt.State.DRAFT:
            fields += ["reference", "topic", "text"]
        return fields

    @admin.action(description="Approve selected excerpts (rights checked)")
    def approve_selected(self, request, queryset):
        _run_action(self, request, queryset, approve_excerpt)

    @admin.action(description="Withdraw selected approved excerpts")
    def withdraw_selected(self, request, queryset):
        _run_action(self, request, queryset, withdraw_excerpt)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TutorExplanation)
class TutorExplanationAdmin(admin.ModelAdmin):
    list_display = ["revision", "version", "state", "model_name", "created_at", "approved_by"]
    list_filter = ["state", "created_at"]
    search_fields = ["revision__prompt", "explanation"]
    readonly_fields = [
        "revision", "version", "state", "model_name", "prompt_version", "generated_by",
        "source_fingerprint", "created_at", "approved_by", "approved_at",
    ]
    filter_horizontal = ["citations"]
    actions = ["publish_selected", "withdraw_selected"]

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.state != TutorExplanation.State.DRAFT:
            fields += ["explanation", "common_mistake", "practice_tip", "citations"]
        return fields

    def has_add_permission(self, request):
        return False  # Drafts must be generated from verified source excerpts.

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Publish selected drafts after academic review")
    def publish_selected(self, request, queryset):
        _run_action(self, request, queryset, publish_explanation)

    @admin.action(description="Withdraw selected published explanations")
    def withdraw_selected(self, request, queryset):
        _run_action(self, request, queryset, withdraw_explanation)
