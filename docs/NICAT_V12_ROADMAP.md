# NiCat v1.2 — Controlled contributions & academic workflow

**Decision:** The Nov 21 product design assigns **v1.2 to controlled student contributions** (rights declaration, quarantine, duplicate checks, human review and eventually approved source indexing). This implementation prioritizes that scope. A better staff reviewer dashboard and contributor onboarding support it; **credits, payments and M-Pesa are reserved for v1.3**.

## Sprints and exit gates

| Sprint | Deliverable | Exit gate |
|---|---|---|
| 11 — Original-text submissions | Private, JSON-only student notes submission; explicit authorship/use permissions; own history/withdrawal; dedup flag; two-person academic/rights review; append-only decisions | Tests for ownership, rights, duplicate, no auto-index; reviewer walkthrough |
| 12 — Private binary uploads | Private object storage / quarantine; approved PDF/TXT types only; magic/MIME checks; size limit; malware scan before extraction; no public URLs; safe BFF multipart proxy | EICAR/scanner-failure simulations, disallowed extensions, oversize, no public access, no processing if scanner unavailable |
| 13 — Approved academic indexing | Rights-evidenced SourceDocument mapping; safe extraction, topic alignment, academic review of snippets; SourceExcerpt approval integration; provenance + withdrawals invalidating Tutor content | Unauthorized files never indexed; revocation hides dependent content; source/unit alignment tests |
| 14 — Staff reviewer workspace & onboarding | Staff queue with filters, audit trail and saved rationales; contributors see status/help; accessibility and mobile checks | Two-person approvals; staff role negative tests; pilot metrics and takedown rehearsal |

**Current package (Sprint 11):** text only; nothing is ever automatically published or exposed to the Tutor. The `approved` status means internally eligible for a later explicit publication/indexing workflow; it is NOT public.

## Student story

A student signs in, opens `/contribute`, selects DSA, and submits **their own 100–6,000-character revision notes**. They must separately confirm original authorship, permit review/eventual display, and may optionally authorize future AI-assisted use. NiCat stores a private `pending_review` record and flags exact repeat text. The student can see only their own status and can withdraw at any stage. No notes or their content appear in public exams, Tutor or search indexes.

## Reviewer story

The rights reviewer verifies authorship/rights and saves a rationale (at least 15 characters); they run **Clear rights** in Django Admin. A *different* academic reviewer verifies accuracy and relevance, saves a rationale, and runs **Academically approve**. The decision history records actors, rationale and timestamps. An approved submission is **still not public or indexed**. Flagged duplicates cannot be approved automatically; reject or investigate them manually. A rights hold or rejection is supported. In Sprint 12+, scanned uploads and stronger duplicate handling are added before any indexed publication.

## Non-goals

- Binary files or OCR, PDF/DOCX processing, antivirus claims, public contributions feed.
- Auto-conversion to `SourceDocument` or `SourceExcerpt`, AI training, instant Tutor answers.
- Access to other students' submissions, automatic grades or contribution credits.
- Legal proof of ownership just because a student ticked a checkbox; reviewers still verify.
