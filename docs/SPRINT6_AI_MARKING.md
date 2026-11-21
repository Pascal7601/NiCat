# NiCat v1.1 — Sprint 6 (AI-assisted marking foundation)

## Scope and safety

- AI creates **private, rubric-scored draft suggestions** for a submitted written answer.
- Only a staff member holding the existing `attempts.review_written_answers` permission may request or read suggestions.
- **Human marking is unchanged.** `GradeItem.marks_awarded`, attempt state, grades, and student results are never modified by AI.
- Human marking later records whether it agreed with the AI score, or overrode it.
- AI is **disabled by default**. Do not enable with real student answers until privacy notice, provider terms and consent/lawful-basis decisions are approved.
- Existing question/answer/rubric **snapshots** provide the AI grading context; do not replace them with generated keys.
- No unreviewed response is shown to a student; student-facing explanations/RAG are later tasks.

## Files changed

- `backend/apps/ai_tutor/`: Django app, reviewer-only endpoint, OpenAI adapter, rubric validator, proposal record, initial migration and admin read-only registration
- `backend/config/settings/base.py`: disabled-by-default feature flag, model/key configuration and throttling
- `backend/config/urls.py`: versioned endpoint registration
- `backend/apps/attempts/review_services.py`: audit the human decision vs proposed mark
- `frontend/lib/route-policy.mjs`: narrow BFF allowlist extension
- `frontend/components/AIMarkingSuggestionPanel.tsx`: reviewer-only UI panel; explicitly does not finalize a grade
- `backend/tests/test_ai_marking.py` and `frontend/tests/route-policy.test.mjs`: regression tests

## Reviewer API

`POST /api/v1/review/grade-items/{grade_item_uuid}/ai-suggestion/` generates once and caches the result.
`GET /api/v1/review/grade-items/{grade_item_uuid}/ai-suggestion/` reads the existing suggestion (404 if absent).

Only for eligible pending written responses. This route is also allowed through Next.js BFF as `/api/nicat/review/grade-items/{id}/ai-suggestion/`. HTTP 503 means AI is unavailable or its output failed validation. HTTP 409 means no pending written answer remains. HTTP 403 means the caller lacks reviewer permission. HTTP 404 means disabled, missing, or not generated.

Example response:

```json
{
  "grade_item_id": "<uuid>",
  "proposed_marks": "4.00",
  "breakdown": [{
    "criterion_number": 1,
    "criterion": "Explain first in first out",
    "max_marks": "5.00",
    "awarded": "4.00",
    "reason": "Identifies FIFO correctly but lacks a concrete example"
  }],
  "feedback": "Good explanation. Include an example.",
  "model_name": "your-model-id",
  "review_status": "pending",
  "generated_at": "<iso-date>",
  "human_review_required": true
}
```

## Installation on your current NiCat repository

1. Compare the provided patch to the **current** repository. This Sprint 6 patch is based on the earlier v0.4 code snapshot, not a fresh copy of your latest local v1.0 branch.
2. Review changes and reconcile any modifications to files also edited in Sprints 2–5.
3. Install dependencies: `pip install -r requirements.txt`
4. Ensure `DJANGO_SETTINGS_MODULE=config.settings.local`, then run `python backend/manage.py makemigrations --check --dry-run` to check the supplied AI migration against your installed Django and existing app migrations.
5. On a disposable PostgreSQL database, run `python backend/manage.py migrate`, followed by your regression suite.
6. Configure `NICAT_AI_MARKING_ENABLED=true`, `OPENAI_API_KEY=<server-only-key>` and `NICAT_AI_MODEL=<model-supporting-structured-output>` only for a controlled, approved AI pilot. Keep settings disabled elsewhere.
7. In the existing reviewer queue UI, import `AIMarkingSuggestionPanel` from `@/components/AIMarkingSuggestionPanel` and place `<AIMarkingSuggestionPanel gradeItemId={item.grade_item_id} />` next to the existing written-answer form. The reviewer must still enter a score and a human rationale to finalize.
8. Rebuild Next.js (`npm run build`) after changing environment variables. Keep `OPENAI_API_KEY` **out of frontend configuration** and out of source control.

### Run tests

```bash
pytest -q backend/tests/test_ai_marking.py backend/tests/test_reviewer_workflow.py
bash scripts/verify-backend.sh
cd frontend
npm run typecheck
npm run test:contract
npm run build
```

## Next sprints

- **Sprint 7:** Reviewer-approved, versioned explanations; source registry and rights checks; student-safe retrieval only after finalization; no citations invented by AI.
- **Sprint 8:** Follow-up tutor, topic-specific retrieval, quotas, caching, accuracy/cost evaluation.
- **Sprint 9:** Controlled beta and release hardening.
- Student uploads are **v1.2**, and credits/M-Pesa are **v1.3**.

## Evaluation before wider use

Compare AI proposals with independent human marks, including alternative phrasings and incomplete answers. Track mean absolute mark error, disagreement rate, rubric coverage, false-positive overmarking, response cost, latency, and user consent. Disable AI at the feature flag on anomalies; never silently promote AI to final-marker status.
