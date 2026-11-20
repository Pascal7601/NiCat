# 01 — Product Brief

**Document ID:** NICAT-PB-001 · **Version:** 0.1 · **State:** Proposed

## Vision
NiCat is an independent revision service helping Kenyan university students prepare for CATs, mock exams and end-semester examinations using reliable, source-attributed academic materials. The first release serves MMU's four-year BBIT programme; the data model must allow other programmes and universities later.

## The problem
Study notes and past questions are dispersed across folders and formats. Some historical papers contain errors or outdated regulations; many require written, computational, coding or case-study answers. Generic multiple-choice quiz apps lose marks, rubrics, original exam timing, topic context and sources.

## Stakeholders and roles
- **Student:** browse units, practice, submit exams, review scores and explanations, track progress.
- **Content author:** propose questions and upload/link source metadata; cannot self-publish by default.
- **Academic reviewer:** verify topic, wording, marks, answer key, rubric, copyright status, and approve publication.
- **Platform administrator:** manage academic catalogue, users, moderation and audit access; no unilateral grade edits without a recorded reason.
- **Support/QA (later):** view non-sensitive platform diagnostics; do not view student answers by default.

## Initial user journey
Student creates an account → selects programme/year/semester → selects unit and practice mode → starts an attempt → answers and saves progress → submits → sees objectively graded marks and pending written review → reads explanations and revises weak topics.

## Pilot scope
1. **BIT 216 Data Structures and Algorithms (Y2S1):** topic hierarchy, abstract data types, complexity and algorithm analysis.
2. **BCS 2218 Internet Application Programming (Y2S1):** HTML/CSS/JavaScript/PHP/MySQL questions and written/code responses.
3. **BIT 2413 E-Commerce (Y4S1):** mark-weighted case studies and timed mock CAT.

## In scope for MVP
Accounts, configurable academic catalogue and course versions; reviewed questions and explanations; practice and timed mock exams; autosave/resume; objective scoring; written responses pending human review; result breakdown and history; restricted Django Admin authoring/review; event/audit logging; private-source metadata.

## Not in MVP
Official MMU student records/grades; live proctoring; payments; social groups/leaderboards; running arbitrary student-submitted code; unreviewed AI marking of essays as final; full universal coverage; AI tutor; institution-specific SSO.

## Success criteria for pilot (proposed, to validate)
- A pilot student can finish the full login → DSA practice → submit → results → review flow on desktop/mobile.
- All published pilot questions have checked answers/rubrics and retrievable source provenance.
- A repeated submission never creates a second score or changes a finalized attempt.
- A student cannot access another student's attempts, grades, or hidden answer keys.
- Partial written marking is displayed as **pending**, not silently treated as zero or final.

## Institutional positioning
MMU lists BBIT as a four-year degree, but NiCat is **independent**, not affiliated with or endorsed by the university. Do not use university branding in ways that suggest official status. Official programme page: https://www.mmu.ac.ke/bachelor-of-business-information-technology/.
