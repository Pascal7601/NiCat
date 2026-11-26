# NiCat v1.1 Sprint 9 — Security hardening & controlled MMU beta

**Status:** Additive release-gate implementation. NO production deployment, security certification, legal approval or real-student beta is claimed. A beta is NOT approved just because automated checks pass.

## Release boundary

- Working baseline: v1.0 practice exams, final grades and human-reviewed written marking; Sprint 6 AI suggestions; Sprint 7 source-backed explanations; Sprint 8 reviewer-gated follow-up and deterministic revision recommendations.
- Sprint 8 follow-up generator **only supports mock mode**. Mock content must not be exposed to real students. Therefore a real-student beta can either (a) disable follow-ups until a production-grade, evaluated provider is implemented and budgeted, OR (b) limit the whole rollout to synthetic/test accounts in a private staging environment. Do not claim live AI follow-up availability in a real beta.
- AI content remains separate from final exam marks; academic decisions must be traceable to named reviewers.

## Threat model (first pass)

| Asset | Threat / misuse | Control to verify | Evidence |
|---|---|---|---|
| Student attempts/answers | IDOR: student A guesses student B's UUID | `Attempt.student=request.user` and attempt-question relationship; tests GET/POST | `test_study_coach.py`, `test_study_tutor.py`, manual 2-user check |
| Answer keys / rubric | Early answer leakage | Marking snapshots not exposed before finalization; response schema inspection | Staff/student API negative tests |
| Grades | AI overwrites final academic mark | Reviewer-only marking service; audit of AI suggestion and override | `test_ai_marking.py`, reviewer test |
| Approved excerpts | Copyright misuse / fabricated citations | Rights-cleared SourceDocument, topic matching, reviewer action | Django Admin SourceExcerpt + rights evidence |
| Published tutor answers | Stale/withdrawn source still shown | Dynamic rights/fingerprint check on every read | `test_study_tutor.py`, audit coverage check |
| Follow-up responses | Unreviewed/generated mock answer delivered | Draft privacy, reviewer-only publish and explicit publish guard | `test_study_coach.py` |
| Daily quotas | Concurrent overuse | PostgreSQL row-lock quota; separate DRF throttle | Postgres concurrent test + staging probe |
| Auth cookies & BFF | Theft/CSRF/proxy escape | HttpOnly/Secure/SameSite, CSRF policy, exact-path allowlist | Django checks + frontend tests |
| API and admin | Configuration leaks / unsafe transport | HTTPS, allowlisted hosts, DEBUG=False, no wildcard CORS, protected admin | `check --deploy`, release gate |
| Student personal data | Over-retention / unlawful sharing | Privacy notice, DPA review, data retention and deletion policy | Manual sign-off |

## Hard release gates (all must pass before real-student beta)

1. **Correct environment:** production Django settings, DEBUG=False, HTTPS, secure cookies, explicit hostnames, PostgreSQL, backed-up database; test recovery from a backup.
2. **Migration consistency:** no pending migrations, `makemigrations --check --dry-run` clean, no schema drift. Never use `--fake` to silence failures.
3. **Security:** existing and Sprint 9 tests pass, two-student IDOR probes fail closed, BFF route policy rejects arbitrary paths/methods, Django deploy warnings reviewed and resolved.
4. **Academic content:** every published source is rights-cleared; every beta Tutor explanation has an accountable reviewer and active citations. Target >=90% eligible pilot exam questions have a release-valid explanation (or limit the pilot scope and document the uncovered questions).
5. **Quality evaluation:** manually sample >=40 published answer/explanation claims across DSA, IAP and E-Commerce; >=95% supported by their actual approved source(s). Keep reviewer notes, not raw student answers, in the report. Zero critical unsafe or pre-release leakage.
6. **Mock segregation:** no mock text visible to real students, no externally available mock testing environment, and Sprint 8 live follow-up generation remains disabled until separately implemented and reviewed.
7. **Reliability:** staging-only probe with permission; review p50/p95, error rates, and API availability. Target 95% of relevant AI user actions under 12s (separate first-request and cache figures); do not infer from a synthetic health check.
8. **Privacy and operational readiness:** signed-off privacy notice, permitted data uses, least-privileged academic roles, logging that excludes secrets and student answer content, retention/deletion process, incident response owner, and tested rollback.
9. **Pilot approval:** named project owner and academic/content reviewer sign off. Publish change log and support contact. Do not imply MMU institutional endorsement without authorization.

## Proposed controlled pilot

**Phase A (internal):** 3–5 team members using synthetic accounts and content. Include negative security tests; no real student data.

**Phase B (invited testers):** 10–20 opt-in BBIT testers on a separate, protected beta environment; only the explicitly reviewed functionality is enabled. Do not ask students to upload copyrighted lecture notes. Explain that NiCat is an independent study tool, not the university's official assessment portal.

**Phase C (evaluation):** 7–14 days of usability/quality feedback (proposed schedule, not yet arranged); monitor issue counts, reviewer turnaround, accessibility, source corrections, and anonymous task completion. Stop or roll back on serious exposure or academic integrity issues.

## Manual test matrix

- Student 1 cannot access Student 2's attempt, final result, Tutor explanation, follow-ups, or recommendations.
- Unauthenticated requests receive 401/403 without sensitive data; unknown attempt IDs are not enumerable.
- Student cannot call Tutor draft generation or academic publication actions; staff lacking custom permission also cannot.
- Before final marking, Tutor explanation and follow-up are unavailable even when the frontend button is manipulated.
- Published source becomes restricted/withdrawn: explanation and dependent follow-up must be hidden.
- Placeholder `MOCK TEST DATA` cannot be published via Admin; reviewer edits and approval must leave traceable identity.
- Fourth follow-up is blocked with 429 at limit=3; two concurrent student POSTs cannot bypass the cap on PostgreSQL.
- API does not expose private rubrics, correct keys, tokens, provider prompts, raw student answers, or admin links to student clients.
- Mobile keyboard, low bandwidth, screen reader labels, error messages and timer usability are manually checked.
- Logout/refresh token rotation works; CSRF and Secure cookies are enforced at the real reverse proxy.
- Backups are encrypted, restricted, restored in staging, and deleted according to retention schedule.

## Incident/rollback plan

1. If exposure is suspected, restrict access at the edge and turn off `NICAT_AI_TUTOR_ENABLED`, `NICAT_AI_FOLLOWUPS_ENABLED`, and `NICAT_AI_TUTOR_GENERATION_ENABLED` as needed; do not blindly delete evidence.
2. Revoke affected credentials/tokens and ensure reviewer/admin accounts are secure. Preserve timestamps and sanitized logs (no user answers or secrets in incident chat).
3. Withdraw affected published Tutor content through existing Admin actions; revoke source rights when appropriate.
4. Roll back application image/commit to previous verified revision; do NOT restore an older DB backup over new student submissions. Use a tested forward-compatible migration/recovery strategy.
5. Notify appropriate stakeholders and comply with applicable Kenyan data protection and breach-notification obligations after legal review. Document root cause and re-test before reopening.

## Metrics (targets vs measurements)

- Coverage: target >=90%; automated release-valid coverage in `nicat_beta_audit --with-db`.
- Grounding: >=95% sampled statements supported; **manual evaluation required**.
- Answer/rubric leakage: zero critical leaks in negative security tests; **manual/adversarial testing required**.
- Helpfulness: target >=70% of opt-in testers rate explanations helpful; **survey/feedback collection is not implemented by this patch**.
- Service: p95 below 12s on appropriate user actions; `sprint9_probe.py` is a small HTTP GET probe, not a replacement for full AI latency evaluation.
- Cost: mock costs $0; **real provider spend is not tracked by NiCat Sprint 8**, so financial limits need implementation before a paid-AI release.

## Operational separation

- Django Admin: source rights, excerpt approval, Tutor publication/withdrawal, follow-up academic review, staff/group permissions, quota read-only monitoring.
- Environment variables/settings: provider, AI enable/disable flags, daily quotas, JWT, HTTPS, hosts, DB; **not edited through Django Admin**.
- `nicat_beta_audit`: read-only aggregate release diagnostics; it does not publish content, perform migrations, or grant permissions.
