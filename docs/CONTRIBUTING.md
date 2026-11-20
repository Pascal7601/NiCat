# Contributing to NiCat

- Work from a requirement or `P2-xx` issue; make a small branch/PR.
- For every change: include tests, data migration (if required), API schema/docs, risk analysis, reviewer and rollback note.
- No business rules in DRF serializer/view beyond validation or orchestration; core grading must live in `attempts.services` / `attempts.grading`.
- Do not change published questions, attempt snapshots or finalized grades in place.
- Run `ruff check backend`, `pytest`, `python manage.py check`, OpenAPI schema validator and migration drift checks when available.
- Only academic reviewers can approve content, and source permission must be recorded before past papers are reproduced.
- Secrets, students' emails/answers and copyrighted source documents must not appear in logs, Git, fixtures or support screenshots.
