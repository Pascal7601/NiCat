"""Staff-specific operations with explicit RBAC and append-only rights decisions.

Approval/publication operations for other domains MUST call their original services.
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.resources.models import SourceDocument
from .models import SourceRightsDecision


class StaffConflict(Exception):
    pass


def require_staff(user, *permissions):
    if not user.is_authenticated or not user.is_active or not user.is_staff:
        raise PermissionDenied("Active staff account required")
    if permissions and not all(user.has_perm(name) for name in permissions):
        raise PermissionDenied("This staff role is not authorized for the operation")


@transaction.atomic
def decide_rights(*, document_id, actor, rights_status, rationale):
    require_staff(actor, "staff_workspace.review_source_rights", "resources.change_sourcedocument")
    rationale = rationale.strip()
    if len(rationale) < 30:
        raise StaffConflict("Provide at least 30 characters of verified rights evidence")
    if rights_status not in (SourceDocument.Rights.ALLOWED, SourceDocument.Rights.RESTRICTED):
        raise StaffConflict("Choose an explicit allowed or restricted decision")
    document = SourceDocument.objects.select_for_update().get(pk=document_id)
    old = document.rights_status
    if old == rights_status:
        raise StaffConflict("Rights status is already set to this decision")
    document.rights_status = rights_status
    document.full_clean()
    document.save(update_fields=["rights_status"])
    SourceRightsDecision.objects.create(
        document=document, actor=actor, previous_status=old,
        new_status=rights_status, rationale=rationale,
    )
    return document
