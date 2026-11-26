# NiCat v1.2 — updated roadmap after Sprint 11 acceptance

The student contribution workflow (Sprint 11) is working in local testing. The user requested eliminating repetitive Django Admin authoring and approval steps, so a staff workspace was prioritized ahead of binary uploads.

| Sprint | Deliverable | Acceptance |
| --- | --- | --- |
| 11 | Private original-text contributions, two-person rights + academic approvals | Confirmed working by owner; no public indexing |
| **12** | **Dedicated `/staff` hub, source library, Tutor draft review, contribution queue, follow-up queue, source-rights audit** | Staff role negative tests, explicit reviewer actions, existing services retained |
| 13 | Private PDF/TXT upload quarantine, malware scan and safe extraction | Reject unknown MIME, oversized files, scanner failures; no public URLs |
| 14 | Approved contribution source indexing, withdrawal propagation, onboarding and beta UX | Rights-cleared, independently reviewed excerpts only; revocation tests |

## Architecture decisions

- `apps.staff_workspace` is a thin DRF adapter, not a replacement for `contributions.services`, `study_tutor.services`, or `study_coach.services`.
- Staff pages use the existing Next.js JWT BFF with only exact GET/POST routes.
- Academic staff still authenticate with existing user accounts and Django permissions; no independent staff credential store.
- All currently approved student contributions remain private and unavailable to Tutor until the explicit indexing feature in Sprint 14.
- Django Admin stays for one-time role setup, superuser maintenance, and exceptional recovery—not for everyday reviewer queues.
- A curriculum editor, CAT builder, binary uploads and full pagination are future work, not quietly included in this patch.
