# 07 — Architecture Decision Records (Draft)

## ADR-001 — Use a modular monolith
**State:** Proposed → ready for team sign-off. **Decision:** one Django application deployed as a modular monolith with discrete apps and explicit service/domain boundaries. **Why:** simplest consistency for grades, migrations, security, maintenance and small-team development. **Alternative:** microservices rejected for initial scale/operational burden. **Revisit:** measured scale or independent deployment need.

## ADR-002 — Django REST Framework and PostgreSQL
**State:** Agreed direction. **Decision:** Django + DRF + PostgreSQL. Favor Django **5.2 LTS series** at implementation time, picking its then-current patched version and verifying Python/DRF support. **Why:** stable support window and admin/ORM/test ecosystem. **Alternative:** FastAPI not chosen by product owner. **Revisit:** major upgrade after compatibility tests. Source: https://www.djangoproject.com/download/

## ADR-003 — Next.js with TypeScript
**State:** Agreed direction. **Decision:** Next.js, TypeScript, Tailwind CSS; consume typed OpenAPI contracts. **Why:** component reuse, responsive frontend, independent teamwork. **Guardrail:** business rules and grades live in Django; never trust frontend time or scores.

## ADR-004 — Version questions, exam templates and submissions
**State:** Proposed. **Decision:** published question revisions and exam versions immutable; attempts snapshot released question text/ordering/max marks. **Why:** fair marking and stable historical results. **Tradeoff:** more storage and version-management UI.

## ADR-005 — Deliberate human review of descriptive answers
**State:** Proposed. **Decision:** automatic marking limited initially to approved objective questions. Written, code-text, case studies use rubric and manual review; AI scoring is future/non-final. **Why:** avoid misleading marks and grading bias. **Tradeoff:** reviewer effort.

## ADR-006 — No automatic public source-file redistribution
**State:** Proposed. **Decision:** capture metadata and source provenance, but publish only allowed/reviewed question content; no uploaded unlicensed third-party textbooks. **Why:** intellectual property and trust.

## ADR-007 — Auth mode and deployment domain alignment
**State:** Pending. **Option A:** secure session/httpOnly cookies with CSRF, favored for a web-only MVP if API and web deployment domains allow. **Option B:** managed auth/OIDC if future mobile clients or providers require. **Decision needed before implementation** to avoid mixed auth schemes.

## ADR-008 — Keep curriculum independent of archive folders
**State:** Proposed. **Decision:** `CurriculumVersion` + `CurriculumUnit` join; original year/semester/code archived as evidence and not treated as the 2026 official course map. **Why:** historical mismatches and future universities.
