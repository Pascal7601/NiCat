# NiCat Phase 1 owner-approved scope

**Decision date:** 2026-11-20  
**State:** Product owner approved the prior NiCat Phase 1 specification and its recommended defaults, with unresolved external verification tracked as risks.  
**Source:** `docs/phase1_baseline` retains the approved v0.1 proposal unchanged.

## Approved decisions / defaults
1. Launch as an independent BBIT practice service for MMU, not an official exam system.
2. Django 5.2 LTS, DRF, PostgreSQL; Next.js + TypeScript later; single modular backend.
3. Student account required for attempts; public programme list allowed; no student registration number.
4. Secure same-site session cookies with CSRF; prefer one browser origin via proxy.
5. Unlimited practice retakes, each distinct and historically preserved. Server-set time limits; resume before deadline; late submit accepts previously saved answers, not new writes.
6. Show objective keys/explanations after permitted submission; optional withholding on exam versions.
7. Written/code/case responses require human review; no invented final percentage while pending.
8. Questions and exams published only after approved review; snapshot versions remain immutable for attempts.
9. No source documents/past-paper verbatim content publicly redistributed without permissions.
10. Academic archive only historical, unit placements/course codes unverified until official review.
11. Start with DSA, Internet Application Programming, and E-Commerce; one-unit vertical slice first.
12. Local development before cloud hosting; deploy only after privacy, security and backup gates.

## Approval is not external certification
The user can approve product direction, but cannot substitute for MMU curriculum verification, academic reviewers, content rights owner permissions, or legal/privacy sign-off. Keep all these as *blocking publication/launch gates*, not blockers to building general infrastructure.

## Phase 1 status
Product direction: **approved**. Technical baseline: **implementation-ready for non-content infrastructure**. Academic/legal/public-release validations: **pending**. No claim that every Phase 1 acceptance item is objectively complete.
