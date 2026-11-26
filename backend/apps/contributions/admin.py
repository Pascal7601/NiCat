"""Two-person editorial controls. Approved != published or Tutor-indexed."""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from .models import Contribution, ContributionDecision
from .services import ContributionConflict, approve_academic, clear_rights, hold_rights, reject, withdraw


def _run(modeladmin, request, queryset, service):
    updated = 0
    for entry in queryset:
        try:
            service(contribution_id=entry.pk, actor=request.user)
            updated += 1
        except (ContributionConflict, PermissionDenied) as exc:
            modeladmin.message_user(request, f"{entry.pk}: {exc}", messages.WARNING)
    if updated:
        modeladmin.message_user(request, f"Updated {updated} submission(s)", messages.SUCCESS)


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ("title", "unit", "student", "state", "possible_duplicate", "rights_reviewed_by", "academic_reviewed_by", "created_at")
    list_filter = ("state", "unit", "possible_duplicate")
    search_fields = ("title", "body", "student__email")
    ordering = ("-created_at",)
    actions = ("clear_selected_rights", "hold_selected_rights", "approve_selected", "reject_selected", "withdraw_selected")

    def get_readonly_fields(self, request, obj=None):
        fields = ["student", "unit", "title", "body", "author_declaration", "allow_display", "allow_ai_use", "content_sha256", "possible_duplicate", "state", "rights_reviewed_by", "rights_reviewed_at", "academic_reviewed_by", "academic_reviewed_at", "created_at", "updated_at"]
        if obj and (obj.rights_reviewed_by_id or obj.state != Contribution.State.PENDING):
            fields.append("rights_review_note")
        elif not request.user.has_perm("contributions.review_contribution_rights"):
            fields.append("rights_review_note")
        if obj and obj.state not in (Contribution.State.PENDING, Contribution.State.RIGHTS_HOLD):
            fields.append("academic_review_note")
        elif not request.user.has_perm("contributions.review_contribution_content"):
            fields.append("academic_review_note")
        return fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Clear rights (requires saved rights rationale)")
    def clear_selected_rights(self, request, queryset):
        _run(self, request, queryset, clear_rights)

    @admin.action(description="Put on rights hold (requires saved rights rationale)")
    def hold_selected_rights(self, request, queryset):
        _run(self, request, queryset, hold_rights)

    @admin.action(description="Academically approve (different reviewer; requires saved rationale)")
    def approve_selected(self, request, queryset):
        _run(self, request, queryset, approve_academic)

    @admin.action(description="Reject (requires saved academic rationale)")
    def reject_selected(self, request, queryset):
        _run(self, request, queryset, reject)

    @admin.action(description="Withdraw contributions")
    def withdraw_selected(self, request, queryset):
        _run(self, request, queryset, withdraw)


@admin.register(ContributionDecision)
class ContributionDecisionAdmin(admin.ModelAdmin):
    list_display = ("contribution", "actor", "action", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("contribution__title", "actor__email")
    readonly_fields = ("contribution", "actor", "action", "rationale", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
