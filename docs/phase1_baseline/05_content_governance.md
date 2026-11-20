# 05 — Academic Content Governance

**Document ID:** NICAT-CNT-001 · **Version:** 0.1 · **State:** Proposed.

## What was actually inspected
We inventoried 54 study-unit folders across Y1S2 to Y4S2 in the provided Google Drive collection. Several contain course outlines, lecture notes, historical CATs, assignments, revision questions, textbooks and presentations; six folder labels have no direct child items. Do not equate file presence with current curriculum verification or publication permission.

### Reviewed sample evidence
| Unit / source | Observed content | Application consequence |
|---|---|---|
| BIT 216 DSA course outline | Arrays, ADTs, stacks, queues, binary trees, BST/heaps, graphs, asymptotic analysis, sorting, searching; prerequisite introduction to programming | Structured topic tree; algorithm questions and explanation rubrics |
| BCS 2218 IAP 2021 revision questions | PHP file modes, HTML tables/forms, JavaScript events, CSS, MySQL, client/server distinction; mixed mark allocations | Mix code-as-text and short/structured answers; preserve marks and diagrams |
| BIT 2413 E-Commerce 2022 CAT | Case studies on MMU LMS, CRM/ERP, competitive forces, BYOD, WLAN and supply chain; 1h30 stated duration | Timed, mark-weighted mock and rubric-based essay marking |
| BIT 2228 Taxation October 2021 CAT | Historical example using year-of-income 2005 tax tables | Temporal validity: never present old figures as current law |
| BCS 2123 programming course outline | C variables/control flow/arrays/functions/pointers/files; CAT 1, CAT 2 and programming labs | Support learning objectives and mixed assessment formats |

## Content workflow
1. **Register source:** record Drive URL/title, type, academic period, uploader, access rights, copyright status and reference file hash when available.
2. **Review original:** verify whether PDFs contain diagrams, tables, answer sheets, footnotes and unusual question numbering. Extracted text alone may be corrupted.
3. **Map unit and topics:** attach canonical unit and curriculum version, keeping original code and year in provenance notes.
4. **Create question draft:** independently author where rights prohibit verbatim republication; preserve literal text for legitimate, approved historical reproductions only.
5. **Set marking data:** marks, answer key or rubric (criteria, accepted variations, worked steps), rationale and reference page/section.
6. **Academic QA:** separate author/reviewer for published content where practical; record reviewer identity and date.
7. **Publish version:** freeze question revision and publication status. Students never see unreviewed drafts.
8. **Monitor issues:** learners flag errors; content owner publishes corrected revision without rewriting old attempt history.

## Findings / exceptions register
- **CNT-001:** Year 1 Semester 1 not present in supplied top-level collection. **Action:** mark missing rather than invent its units.
- **CNT-002:** Six subject folders have zero direct children: Y4S1 Accounting Information System; Y4S2 Computer Security and Cryptography; Human Resource Management; Auditing of Information Systems; Advanced Network Concepts; Data Mining and Business Intelligence. **Action:** keep catalogue entries in `unverified/no-source` state.
- **CNT-003:** BIT 2413 E-Commerce CAT page headers also read BIT2316. **Action:** mark source-code conflict for human verification. The listed individual question marks sum to 35, but the document does not clearly specify the total; do not override it.
- **CNT-004:** BCS 2218 revision PDF text extraction reflows a table/diagram and mixes numbering. **Action:** manually inspect original layout before importing those questions.
- **CNT-005:** BIT 2228 Taxation CAT (Oct 2021) calculates for tax year 2005. **Action:** preserve and label vintage and rates; do not use as contemporary tax guidance.
- **CNT-006:** MMU course codes and unit placement may have changed. **Action:** request official latest curriculum before promoting inventory to verified.
- **CNT-007:** Reference books and third-party course packs have unresolved redistribution rights. **Action:** store restricted-source links/metadata, not public copies.

## Pilot content acceptance criteria
- At least one **reviewed, publishable practice set per pilot unit**; exact number and mix must be agreed with content reviewers.
- Every included question has validated type, marks, topic, provenance, and permitted answer disclosure stage.
- Every objective question has a checked unique key and explanatory rationale; each written response has rubric criteria summing to total marks.
- Two independent checks for equations/code/math-heavy items or disputed answers.
- Zero unresolved `blocking` issues in published question sets.
- Rights status known before exposing literal past-paper content in public product.

## Note on AI use
AI may propose *drafts*, categorization and explanations after source ingestion. Draft outputs must be reviewed and versioned; a model output is not authority and cannot auto-publish. Human grading remains the source of truth for MVP descriptive/case-study scores.
