# 08 — Phase 1 Delivery Backlog

**State:** Proposed. Tasks are **Phase 1 analysis/design only**; do not open implementation PRs until the sign-off gate.

| ID | Priority | Work item / primary role | Acceptance evidence | Dependencies |
|---|---|---|---|---|
| P1-01 | P0 | Approve NiCat vision, first release and non-goals — Product | Signed scope/target audience | None |
| P1-02 | P0 | Baseline MMU BBIT archive and missing semesters — Content | Reconciled 54-unit folder inventory, exception list | Drive access |
| P1-03 | P0 | Verify latest institutional course codes/years — Academic | Source + verification date for relevant pilot units | University source |
| P1-04 | P0 | Define content rights and acceptable quotation rules — Product/Legal | Publication matrix and restricted-source policy | P1-02 |
| P1-05 | P0 | Prepare DSA topic hierarchy — Content | Outline-mapped topics with citations | P1-02 |
| P1-06 | P0 | Prepare IAP sample questions with manual PDF layout check — Content | Clean source-to-question draft and marks | P1-02 |
| P1-07 | P0 | Prepare E-Commerce CAT review and case-study rubrics — Content | Reviewed draft and code mismatch flagged | P1-02 |
| P1-08 | P0 | Approve role + permission matrix — Backend/Product | Object-level permissions and staff authority matrix | P1-01 |
| P1-09 | P0 | Approve grading rules and statuses — Backend/Content | Examples and roundtrip test criteria | P1-05–07 |
| P1-10 | P0 | Approve domain model and consistency invariants — Backend | ERD, constraints and version policy | P1-08–09 |
| P1-11 | P0 | Approve MVP user journeys and wireframe requirements — Frontend | Student screens/state matrix | P1-01, P1-09 |
| P1-12 | P0 | Agree API contracts and auth model — Backend/Frontend | Signed OpenAPI contract design and auth ADR | P1-08, P1-10, P1-11 |
| P1-13 | P0 | Create threat model, privacy/compliance checklist — QA/Security | Blocking risks tracked with controls | P1-08, P1-10 |
| P1-14 | P1 | Define test plan, performance targets and CI gates — QA | Test inventory, CI definition, measured thresholds | P1-09, P1-12 |
| P1-15 | P0 | Design review/sign-off and Phase 2 readiness — Product/Tech leads | Approved documents, closed blockers and first sprint plan | All P0 items |

## First focused content batch
Draft **10–15 independently authored, source-mapped questions** per pilot unit as a *working target for review*, not an assertion that the archive already has 30–45 verified questions. Separate original-past-paper candidates from generated questions; do not publish until rubrics and rights are approved.

## Recommended issue labels
`phase:1`, `area:backend`, `area:frontend`, `area:content`, `area:security`, `area:documentation`, `priority:p0`, `status:blocked`, `source:verification-needed`.

## Definition of done for Phase 1
Approved scope and role matrix; approved grade/status rules; pilot topic and draft-question register with sources; unresolved content issues labelled (no blocking errors in approved set); conceptual ERD; draft v1 API contract; security/privacy checklist; QA plan; first Phase 2 implementation issues broken into frontend/backend tasks.
