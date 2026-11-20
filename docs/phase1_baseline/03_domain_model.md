# 03 — Conceptual Domain Model & Invariants

**Document ID:** NICAT-DOM-001 · **Version:** 0.1 · **State:** Conceptual; not database migrations.

## Contexts and ownership
- `accounts`: users, student profiles and scoped staff roles.
- `academics`: University, Programme, CurriculumVersion, Unit, CurriculumUnit (version-specific placement), Topic.
- `resources`: SourceDocument (title, date, Drive locator, licence/rights, allowed visibility, source type), SourceReference (page/section/excerpt fingerprint).
- `questions`: Question (stable identity), QuestionRevision (immutable when published), Option, RubricCriterion, ReviewEvent.
- `exams`: ExamTemplate, ExamVersion, ExamQuestion (frozen question revision, display order/marks), visibility/retake policy.
- `attempts`: Attempt, AttemptQuestion snapshot, StudentResponse, Grade, GradeItem, GradingEvent.
- `analytics`: read models derived from finalized or appropriately labeled partial grades; avoid owning canonical marks.

## Cardinality overview
University 1—N Programme; Programme 1—N CurriculumVersion; CurriculumVersion 1—N CurriculumUnit; Unit 1—N Topic; Topic 1—N Question; Question 1—N QuestionRevision; SourceDocument 1—N SourceReference; QuestionRevision 0—N SourceReference; ExamTemplate 1—N ExamVersion; ExamVersion 1—N ExamQuestion; ExamVersion 1—N Attempt; Attempt 1—N AttemptQuestion; AttemptQuestion 0—1 StudentResponse; StudentResponse 0—N GradeItem.

## Important data rules
1. **Academic code ≠ primary identity.** Unit codes and placements change. Prefer UUIDs + versioned unique mapping constraints. Preserve original codes as source metadata when conflicting.
2. **Published revisions immutable.** An update creates `QuestionRevision` N+1; never edit answer keys in-place for already published/referenced versions.
3. **Exam snapshots immutable.** A student attempt fixes the exam configuration, question wording, options, keys/rubrics (server-private), maximum marks and order at start time.
4. **Ownership:** All attempt/result access must be filtered and checked against the authenticated owner (or appropriately privileged reviewer).
5. **State machine:** `created → in_progress → submitted → grading_pending | graded_final`; `expired` and `cancelled` only by explicitly defined policy. `submitted` cannot revert to `in_progress`.
6. **Grade statuses:** `not_applicable`, `pending_review`, `provisional`, `final`. Total marks must be qualified by status when any component is ungraded.
7. **Idempotency and consistency:** Atomic submission and a uniqueness/idempotency key prevent duplicate finalization under retries/concurrent requests.
8. **Preserve source identity:** Historical CAT, practice prompt and AI-generated question are different provenance categories. Do not call a generated question an MMU past-paper question.
9. **No direct executable code:** Student code is stored as text in MVP; never run it in the Django process.
10. **Time model:** Persist timestamps as UTC; present Africa/Nairobi times where relevant, using timezone-aware operations.
11. **Result immutability:** Corrections require explicit review and audited adjustment, retaining prior grade history.

## Example draft schema (illustrative; final column names TBD)

| Model | Essential fields |
|---|---|
| `Unit` | UUID, canonical title, canonical code (nullable), active |
| `CurriculumUnit` | curriculum_version_id, unit_id, year_number, semester_number, displayed_code |
| `SourceDocument` | UUID, title, source_kind, source_year, drive_url, visibility, rights_status |
| `QuestionRevision` | question_id, revision, question_type, prompt, max_marks, approved_by, published_at |
| `RubricCriterion` | question_revision_id, criterion, criterion_marks, guidance, sort_order |
| `ExamVersion` | exam_template_id, version, duration_seconds, instructions, published_at |
| `Attempt` | student_id, exam_version_id, state, started_at, deadline_at, submitted_at |
| `StudentResponse` | attempt_question_id, selected_option_id OR text, saved_at |
| `Grade` | attempt_id, awarded_marks, possible_marks, grading_status, finalized_at |

## Worked case: correcting an exam paper
An original E-Commerce CAT is tagged `source_type=past_cat`, `source_year=2022`, `rights_status=not_checked`; the cover text identifies BIT 2413, but some page headers say BIT2316. Preserve the raw discrepancy in `SourceDocument.notes`, map the unit only after reviewer confirmation, and do not silently alter the historic scan.
