"""Human academic review of follow-up drafts. No direct publication edits."""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError

from .models import TutorDailyBudget, TutorFollowUp
from .services import CoachConflict, publish_followup, reject_followup, withdraw_followup


@admin.register(TutorFollowUp)
class TutorFollowUpAdmin(admin.ModelAdmin):
    list_display = ["id", "student", "question_preview", "state", "created_at", "reviewed_by"]
    list_filter = ["state", "created_at"]
    search_fields = ["question", "draft_answer", "student__email"]
    readonly_fields = [
        "student", "attempt_question", "explanation", "question", "state",
        "quota_day", "created_at", "reviewed_by", "reviewed_at",
        "published_answer", "source_evidence",
    ]
    fields = [
        "student", "attempt_question", "explanation", "question", "state",
        "source_evidence", "draft_answer", "published_answer", "reviewed_by",
        "reviewed_at", "quota_day", "created_at",
    ]
    actions = ["publish_selected", "reject_selected", "withdraw_selected"]

    def question_preview(self, obj):
        return obj.question[:90]
    question_preview.short_description = "Question"

    def source_evidence(self, obj):
        if not obj or not obj.pk:
            return "No sources yet"
        return "\n".join(
            f"{s.reference.document.title}: {s.text[:250]}"
            for s in obj.citations.select_related("reference__document")
        ) or "No source excerpts attached"
    source_evidence.short_description = "Approved source excerpts"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.state != TutorFollowUp.State.DRAFT:
            readonly.append("draft_answer")
        return readonly

    def _action(self, request, queryset, service):
        count = 0
        for item in queryset:
            try:
                service(followup_id=item.pk, actor=request.user)
                count += 1
            except (CoachConflict, PermissionDenied, ValidationError) as exc:
                self.message_user(request, f"{item.pk}: {exc}", level=messages.WARNING)
        if count:
            self.message_user(request, f"Updated {count} follow-up(s)", level=messages.SUCCESS)

    @admin.action(description="Publish reviewed answers (approved evidence required)")
    def publish_selected(self, request, queryset):
        self._action(request, queryset, publish_followup)

    @admin.action(description="Reject selected unanswered drafts")
    def reject_selected(self, request, queryset):
        self._action(request, queryset, reject_followup)

    @admin.action(description="Withdraw selected published answers")
    def withdraw_selected(self, request, queryset):
        self._action(request, queryset, withdraw_followup)


@admin.register(TutorDailyBudget)
class TutorDailyBudgetAdmin(admin.ModelAdmin):
    list_display = ["day", "requests"]
    readonly_fields = ["day", "requests"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
