"""Audit records are visible to administrators, but never editable."""
from django.contrib import admin

from .models import SourceRightsDecision


@admin.register(SourceRightsDecision)
class SourceRightsDecisionAdmin(admin.ModelAdmin):
    list_display = ("document", "actor", "previous_status", "new_status", "created_at")
    list_filter = ("new_status", "created_at")
    search_fields = ("document__title", "rationale")
    readonly_fields = ("document", "actor", "previous_status", "new_status", "rationale", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
