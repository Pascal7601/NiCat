# 02 — MVP Requirements Catalogue

**Document ID:** NICAT-REQ-001 · **Version:** 0.1 · **State:** Proposed; subject to Phase 1 sign-off.

## Functional requirements

| ID | Priority | Requirement | Acceptance test summary |
|---|---|---|---|
| FR-001 | Must | Email/password accounts and authenticated sessions | Authorized student can sign in/out; unauthorized requests denied |
| FR-002 | Must | Student chooses institution, programme and year/semester | Catalogue filtering returns only mapped units |
| FR-003 | Must | Store a curriculum version independently from course identity | Historical unit placements remain queryable after an update |
| FR-004 | Must | Catalogue exposes unit → topic tree | Pilot topics appear in deterministic ordering |
| FR-005 | Must | Store source metadata, access scope and rights status | Every published source-derived question has a reviewable source record |
| FR-006 | Must | Support MCQ single-answer questions with validated option sets | Exactly one approved correct option; marks positive |
| FR-007 | Must | Support written, code-text, numeric and case-study prompts | Answer type and rubric identified; no unsafe code execution |
| FR-008 | Must | Separate draft, in-review, approved, published and retired content | Student endpoints never return unpublished questions |
| FR-009 | Must | Record an immutable published question revision | Old attempt references a frozen wording and rubric |
| FR-010 | Must | Configure practice sets and timed exam templates | Duration, marking rules, question ordering stored |
| FR-011 | Must | Server owns attempt start/end times | Timer cannot be bypassed by editing browser clock |
| FR-012 | Must | Autosave or explicit save student responses | Refresh/resume retains last acknowledged answer |
| FR-013 | Must | Submit an attempt once using an idempotent endpoint | Repeated requests do not duplicate scores |
| FR-014 | Must | Grade approved objective questions deterministically | Expected marks match reference fixtures |
| FR-015 | Must | Mark written responses as pending until reviewed | Provisional/pending/final statuses shown distinctly |
| FR-016 | Must | Show per-attempt results with earned/possible marks and topic breakdown | Breakdown adds up to stored totals; pending clearly marked |
| FR-017 | Must | Restrict attempts and results to their owner | Cross-user access returns permission denial/non-disclosing 404 |
| FR-018 | Must | Let students review explanations after permitted submission | Hidden keys are not exposed before submission |
| FR-019 | Must | Log publication and grade changes with actor/time/reason | Change event is queryable by privileged reviewer |
| FR-020 | Must | Manage catalogue, questions, exam templates and reviewers via admin | Role permissions validated in admin tests |
| FR-021 | Should | Search/filter available questions by topic, source and difficulty | Search results paginate and obey permissions |
| FR-022 | Should | Support retakes while preserving each attempt and exam version | Prior results do not change on retake |
| FR-023 | Should | Distinguish official-document text, independently authored practice and AI drafts | Provenance label appears for each question |
| FR-024 | Should | Show missed-topic summaries only for sufficiently graded attempts | Pending items do not distort scores |

## Nonfunctional requirements (proposed engineering targets)

| ID | Category | Requirement / initial target |
|---|---|---|
| NFR-001 | Security | Enforce HTTPS in production; secure cookies, CSRF protections where cookie auth is used, server-side authorization and least privilege |
| NFR-002 | Privacy | Data-minimizing collection, privacy notice, retention/deletion workflow, ODPC compliance review before public launch |
| NFR-003 | Availability | Define target uptime and disaster recovery objectives before hosting decision; monitor errors and backups |
| NFR-004 | Performance | Target p95 < 500 ms for common read API endpoints at pilot load, to be validated in load tests |
| NFR-005 | Reliability | DB transactions for attempt finalization and score recording; concurrency/idempotency tests mandatory |
| NFR-006 | Maintainability | Typed interfaces where practical, documented module boundaries, ADRs, small PRs, CI, reproducible dev environment |
| NFR-007 | Testing | Initial overall backend coverage target ≥ 80%; critical grading/permission paths require comprehensive case matrices, not coverage alone |
| NFR-008 | API | Namespace `/api/v1/`, document OpenAPI and standardize errors, cursors/pagination and authentication |
| NFR-009 | Accessibility | Target WCAG 2.2 AA for learner-facing flows; keyboard-friendly exam navigation and readable mobile layout |
| NFR-010 | Auditability | Record source attribution, revision history, answer-key changes and grading events |
| NFR-011 | Localization | Kenya-friendly terminology, Africa/Nairobi presentation, UTC timestamp storage, phone-first responsive UI |
| NFR-012 | Content | Prevent release of unreviewed answers, ambiguous papers, or restricted copyrighted source files |

## User stories and examples

**US-01 — Practice a topic.** As a Y2S1 BBIT student, I can open DSA > Stacks, start a short quiz, submit and see my marks. **Given** published questions, **when** I submit, **then** the server grades each objective answer and saves a permanent attempt.

**US-02 — Written marking pending.** As a Y4S1 student, I can complete the case-study sections of an E-Commerce mock CAT. **When** I submit, **then** the written items appear pending review; the interface must not display a deceptive final percentage.

**US-03 — Fix a question safely.** As a reviewer, I can flag an ambiguous question and publish a corrected revision. Earlier student attempts continue to reference the original snapshot; publication cannot silently recompute historical results.

**US-04 — Protect results.** As a student, attempting another student's result URL reveals no content or metadata.

**US-05 — Source provenance.** As an academic reviewer, I can trace a question to its source title, relevant section/page, document vintage and rights status before approving it.

## Open requirements requiring owner decision
Anonymous read-only browsing; email verification requirement; exam pause/resume rule; number of retries; randomized question sets; official transcripts absent; written-answer scoring workflow/turnaround; language support; hosted vs local deployment.
