"""Auditable, read-only fallback; daily workflow belongs in /staff/generate."""
from django.contrib import admin
from .models import (QuestionGenerationJob, GeneratedQuestionCandidate,
                     QuestionGenerationEvent, ExternalSourceAuthorization)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(QuestionGenerationJob)
class JobAdmin(ReadOnlyAdmin):
    list_display = ('id','document','topic','state','provider','created_at')
    list_filter = ('state','provider')


@admin.register(GeneratedQuestionCandidate)
class CandidateAdmin(ReadOnlyAdmin):
    list_display = ('id','job','kind','state','reviewed_by')
    list_filter = ('state','kind')


@admin.register(QuestionGenerationEvent)
class EventAdmin(ReadOnlyAdmin):
    list_display = ('candidate','actor','action','created_at')


@admin.register(ExternalSourceAuthorization)
class VendorAuthAdmin(ReadOnlyAdmin):
    list_display = ('document','provider','approved_by','revoked_at')
