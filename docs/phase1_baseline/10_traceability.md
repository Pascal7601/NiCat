# 10 — Traceability, Review Gate and Verification

## Example requirement-to-test matrix
| Requirement | Planned verification | Responsible workstream |
|---|---|---|
| FR-001, FR-017 | Anonymous request blocked; cross-student attempt access denied | Backend + Security |
| FR-003, FR-004 | Historical curriculum version persists; topic tree correct | Academics + Backend |
| FR-005, FR-023 | Every approved source-derived question has provenance and rights review | Academic/Content |
| FR-006, FR-014 | MCQ options/answers validated; deterministic marks/fixtures | Backend + QA |
| FR-008, FR-009 | Draft questions invisible; published revision immutable | Backend + QA |
| FR-010–FR-013 | Timeouts, autosave, concurrent/idempotent submit | Backend + QA |
| FR-015, FR-016 | Pending written answers don't produce fake final percent | Frontend + Backend |
| FR-018 | Keys/explanations available only after permitted disclosure | Backend + Security |
| FR-019 | Audit after publish/grade change | Backend + QA |
| NFR-002 | Privacy/legal review checklist, data deletion/access flows | Security/Product |
| NFR-006, NFR-008 | Documentation checks, OpenAPI diff and CI | Tech leads |
| NFR-009 | Keyboard, contrast, focus, responsive flow tests | Frontend + QA |

## Phase 1 exit gate (not yet met)
- [ ] Product owner approves scope, main user journey and initial pilot.
- [ ] Academic reviewer validates pilot curriculum mapping, source issues and rubrics.
- [ ] Product/legal signs off publication/rights policies.
- [ ] Backend lead approves conceptual ERD, immutability and authorization rules.
- [ ] Frontend/backend leads agree sample request/response schema, auth and error conventions.
- [ ] QA/security reviews submission, answer-key, IDOR and privacy threat cases.
- [ ] Phase 2 tasks are sized, assigned and linked to requirement IDs.

## Phase 2 entry gate
Create Django/Next.js skeleton only when no **blocking** Phase 1 design questions remain. Nonblocking future decisions stay recorded in ADRs/issue tracker. This is a governance gate, not a promise that all archival materials have been read.
