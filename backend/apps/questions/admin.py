"""Conservative admin permissions; never expose bulk-delete of answer keys."""
from django.contrib import admin
from .models import Question, QuestionRevision, ChoiceOption, RubricCriterion

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "topic", "is_active")
    list_filter = ("is_active",)

@admin.register(QuestionRevision)
class QuestionRevisionAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "number", "kind", "status", "reviewed_by")
    list_filter = ("status", "kind", "provenance")
    readonly_fields = ("published_at",)
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (not obj or obj.status != "published")
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ChoiceOption)
class ChoiceOptionAdmin(admin.ModelAdmin):
    list_display = ("revision", "position", "is_correct")
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (not obj or obj.revision.status != "published")
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(RubricCriterion)
class RubricCriterionAdmin(admin.ModelAdmin):
    list_display = ("revision", "position", "max_marks")
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (not obj or obj.revision.status != "published")
    def has_delete_permission(self, request, obj=None):
        return False
