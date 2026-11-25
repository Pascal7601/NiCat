# NiCat — Confirmed product decisions and revised roadmap (2026-11-25)

## Identity
NiCat is **first and foremost an AI-powered university exam practice platform**. A modest resource library is optional, supporting the practice workflow rather than becoming the primary product.

## Decisions confirmed
1. Sources: prioritize approved notes/authorized academic documents; use reviewed staff questions as a calibration baseline. Topic-only AI generation produces staff-visible drafts, not auto-published scored CATs.
2. Students can eventually create dynamic practice CATs, alongside published staff CATs.
3. Generate and validate questions **ahead of time** for graded exams. On-demand generation may be added for clearly labeled formative practice after evaluation.
4. Human academic reviewers initially approve all AI-generated scored questions. Automatic validation may expand only for narrowly deterministic question types after adequate benchmarking.

## Revised milestones

| Sprint | Product outcome | Hard release gate |
| --- | --- | --- |
| 11 | Original text contributions | Owner isolation; rights + academic review |
| 12 | Staff workspace with source, Tutor, contribution and follow-up review queues | Role isolation, no bypass of domain services |
| **13** | Multi-programme, source-grounded PDF/TXT intake for future question drafting | Private original preservation; file scanning and extraction; rights and mapping review; no public/AI release |
| **14** | Evidence-backed question generation: jobs, candidates, validated answers/rubrics, source links and academic approval | Unapproved questions never enter scored exams; source withdrawals block dependent drafts |
| **15** | Student-configurable dynamic CAT assembly from approved question revisions | Frozen attempt snapshots; topic/difficulty coverage; no double use or answer leakage |
| **16** | Targeted practice from weak topics, evaluation, cost/quality controls, mobile and pilot hardening | Performance, grounding, privacy, reviewer accuracy and load tests |

These sprints extend the original v1.2 scope. For version discipline, treat Sprints 14–16 as a **v1.2.x question-generation track or early v1.3**, and defer paid credits/M-Pesa until the exam-practice value and real costs are validated.

## Proposed generation invariants for Sprint 14
- Only reviewed document versions with `permit_question_generation=True` and valid verified programme/unit mapping may enter the generation queue.
- One generation job stores exact source file hash, approved extracted passage, course/topic, prompt/model version, generation time, provider/estimated token cost, validation decisions and reviewer.
- AI must produce structured candidate MCQs/written questions with answers, distractor rationales, marking rubric and exact passage references.
- Automated validation detects duplicate questions, multiple defensible options, source mismatch, off-syllabus concepts and unsupported answers.
- Academic approval required before creating/updating authoritative `QuestionRevision` records.
- Withdrawing or revoking a source blocks new generation and invalidates dependent unpublished candidates; already-used exam snapshots are retained for audit, not silently changed.

## Example student outcome
A student chooses MMU, a programme, Computer Graphics, 10 questions, medium difficulty and MCQ/mixed types. NiCat selects **approved and fresh** question revisions, prioritizes unattempted items, creates a frozen practice exam version, grades it reliably and recommends weak topics afterward. New question candidates can be generated offline from a verified Computer Graphics document and added only after independent review.
