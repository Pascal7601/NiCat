# DSA Pilot v1 — traceable academic starter

**Unit:** Data Structures and Algorithms (archival course reference BIT 216, BBIT Year 2 Semester 1). The historical source is not proof of the currently approved MMU course code or curriculum.

**Exam:** 12 independently authored practice questions, 20 marks total, 30-minute time limit. Ten single-choice questions (1 mark each), two rubric-reviewed written questions (5 marks each). The questions are **not copied past CATs** and should not be described as official MMU examination items.

**Content sources:**

- MMU course outline: https://drive.google.com/file/d/1UOBSxfeqO276TcWdrUyO_nehz1msX5vK/view
- Searching lecture: https://drive.google.com/file/d/1pqrg6yT8xMcg13gs3fW2lIddzMJDmiX2/view
- Sorting lecture: https://drive.google.com/file/d/14QCM4-gdxwMDIyTTkjBKCN-PtwumTvsw/view
- Trees lecture: https://drive.google.com/file/d/10eaKDt7WhI_zSPxSJcu3Z38QNIunq-rt/view
- Algorithms lecture: https://drive.google.com/file/d/1OpaJDdYF0lW1tiY1nW5oI6xcb4Wchc64/view

Each database question carries a `SourceReference` with a source document and section. Source documents are **restricted**: NiCat must not distribute lecture scans or reproduce copyrighted pages without permission. Pilot practice questions are originally authored, not excerpts from those source files.

## Loading into a migrated development database

1. Create a reviewer using Django admin (`python manage.py createsuperuser`).
2. `python manage.py seed_dsa_pilot` creates 12 **draft** questions and an unpublished exam; it is safe to repeat without creating duplicates.
3. Have a qualified staff content reviewer verify the wording, answer keys, rubrics, and coverage against the source notes and confirm publication rights for any material reused. Correct mistakes in the dataset and remove/reseed the draft before approval, rather than silently changing published questions.
4. `python manage.py seed_dsa_pilot --publish --reviewer-email reviewer@example.com` publishes the examined draft. Requires an active staff user with question-review permission. **Do not use this flag before real review.**
5. Log in through the JWT endpoint; list `GET /api/v1/exams/?unit_id=<id>`, start, save, submit, and inspect result.

The chosen marking policy is **0 or 1 for MCQ** and **0 to 5 based on individual rubric criteria for written answers** (reviewer manually awards totals). A blank written answer scores 0 immediately; submitted written answers enter the review queue. The final percentage remains null until all marked answers have been finalized.

## Idempotency and question immutability

- Published question revisions and exam versions cannot be edited via normal model-save paths.
- Seed uses deterministic UUIDs for individual pilot questions; repeated seeding reports existing data instead of duplicating it.
- The current design is protected in application code; direct SQL can bypass model guards. Database constraints/triggers and a full content-revision workflow are pending hardening before launch.
