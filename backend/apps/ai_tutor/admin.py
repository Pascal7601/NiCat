from django.contrib import admin

from .models import AIMarkingSuggestion


@admin.register(AIMarkingSuggestion)
class AIMarkingSuggestionAdmin(admin.ModelAdmin):
    list_display = ["id", "grade_item", "proposed_marks", "review_status", "created_at"]
    list_filter = ["review_status", "created_at"]
    readonly_fields = [
        "grade_item", "proposed_marks", "breakdown", "feedback", "model_name",
        "answer_sha256", "prompt_version", "generated_by", "created_at",
        "review_status", "reviewed_by", "reviewed_at",
    ]
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
