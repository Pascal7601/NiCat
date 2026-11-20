"""Disallow editing published version through Django admin."""
from django.contrib import admin
from .models import ExamTemplate, ExamVersion, ExamQuestion

@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "is_active")

@admin.register(ExamVersion)
class ExamVersionAdmin(admin.ModelAdmin):
    list_display = ("template", "number", "is_published", "duration_seconds")
    readonly_fields = ("published_at",)
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (not obj or not obj.is_published)
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ("version", "revision", "position")
    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (not obj or not obj.version.is_published)
    def has_delete_permission(self, request, obj=None):
        return False
