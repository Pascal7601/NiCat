/** Explicitly allow only NiCat's supported API routes. */

const U = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

export const ALLOWED = {
    GET: [
        /^\/me\/$/,
        /^\/me\/attempts\/$/,
        /^\/programmes\/$/,
        new RegExp(`^/programmes/${U}/curricula/$`),
        new RegExp(`^/curricula/${U}/units/$`),
        new RegExp(`^/units/${U}/topics/$`),
        /^\/exams\/$/,
        new RegExp(`^/exams/${U}/$`),
        new RegExp(`^/attempts/${U}/$`),
        new RegExp(`^/attempts/${U}/result/$`),

        // Staff review
        /^\/review\/pending\/$/,
    ],

    POST: [
        new RegExp(`^/exams/${U}/attempts/$`),
        new RegExp(`^/attempts/${U}/submit/$`),

        // Staff marking
        new RegExp(`^/review/grade-items/${U}/mark/$`),
    ],

    PUT: [new RegExp(`^/attempts/${U}/responses/${U}/$`)],
};

ALLOWED.GET.push(
    new RegExp(`^/study-coach/attempts/${U}/questions/${U}/followups/$`),
);
ALLOWED.POST.push(
    new RegExp(`^/study-coach/attempts/${U}/questions/${U}/followups/$`),
);
ALLOWED.GET.push(/^\/study-coach\/recommendations\/$/);

ALLOWED.GET.push(
    new RegExp(`^/study-tutor/attempts/${U}/questions/${U}/explanation/$`),
);
ALLOWED.POST.push(new RegExp(`^/study-tutor/revisions/${U}/draft/$`));

ALLOWED.GET.push(/^\/contributions\/$/, /^\/contributions\/units\/$/);

ALLOWED.GET.push(new RegExp(`^/contributions/${U}/$`));

ALLOWED.POST.push(/^\/contributions\/$/);

ALLOWED.POST.push(new RegExp(`^/contributions/${U}/withdraw/$`));
// Sprint 6: narrowly scoped AI-marking endpoints

/*
 * NiCat v1.2 — Sprint 12
 * Staff & Academic Management Workspace
 *
 * These rules allow only the explicitly listed API paths.
 * Django must still authenticate users and enforce staff permissions.
 */

// GET — Staff dashboard and review queues
ALLOWED.GET.push(
    // Staff overview
    /^\/staff\/overview\/$/,

    // Source library
    /^\/staff\/sources\/units\/$/,
    /^\/staff\/sources\/documents\/$/,
    /^\/staff\/sources\/references\/$/,
    /^\/staff\/sources\/topics\/$/,
    /^\/staff\/sources\/excerpts\/$/,
    new RegExp(`^/staff/sources/excerpts/${U}/$`),

    // AI Tutor explanations
    /^\/staff\/tutor\/$/,
    new RegExp(`^/staff/tutor/${U}/$`),

    // Student contributions
    /^\/staff\/contributions\/$/,
    new RegExp(`^/staff/contributions/${U}/$`),

    // Student follow-up reviews
    /^\/staff\/followups\/$/,
    new RegExp(`^/staff/followups/${U}/$`),
);

// POST — Create, update and review actions
ALLOWED.POST.push(
    // Source documents and rights
    /^\/staff\/sources\/documents\/$/,
    new RegExp(`^/staff/sources/documents/${U}/rights/$`),

    // Source references and excerpts
    /^\/staff\/sources\/references\/$/,
    /^\/staff\/sources\/excerpts\/$/,
    new RegExp(`^/staff/sources/excerpts/${U}/$`),
    new RegExp(`^/staff/sources/excerpts/${U}/action/$`),

    // Tutor generation, editing and approval
    /^\/staff\/tutor\/generate\/$/,
    new RegExp(`^/staff/tutor/${U}/$`),
    new RegExp(`^/staff/tutor/${U}/action/$`),

    // Contribution reviews
    new RegExp(`^/staff/contributions/${U}/$`),
    new RegExp(`^/staff/contributions/${U}/action/$`),

    // Follow-up reviews
    new RegExp(`^/staff/followups/${U}/$`),
    new RegExp(`^/staff/followups/${U}/action/$`),
);

ALLOWED.POST.push(/^\/staff\/questions\/search\/$/);

const AI_SUGGESTION = new RegExp(`^/review/grade-items/${U}/ai-suggestion/$`);

ALLOWED.GET.push(AI_SUGGESTION);
ALLOWED.POST.push(AI_SUGGESTION);

// Sprint 13: GET/catalogue/history/staff review are JSON-only.
// Binary POST goes to the dedicated /api/nicat/document-upload/ route.
ALLOWED.GET.push(
    /^\/document-intake\/programmes\/$/,
    new RegExp(`^/document-intake/programmes/${U}/units/$`),
    /^\/document-intake\/$/,
    /^\/document-intake\/staff\/$/,
    new RegExp(`^/document-intake/staff/${U}/$`),
);
ALLOWED.POST.push(
    new RegExp(`^/document-intake/${U}/withdraw/$`),
    new RegExp(`^/document-intake/staff/${U}/review/$`),
);

// Sprint 15: verified past-paper review. Paths only, NO query parameters.
ALLOWED.GET.push(
    /^\/past-papers\/$/,
    new RegExp(`^/past-papers/${U}/questions/$`),
    new RegExp(`^/past-papers/${U}/page/(?:[1-9]|[1-7][0-9]|80)/$`),
    new RegExp(`^/past-paper-questions/${U}/variations/$`),
);
ALLOWED.POST.push(
    new RegExp(`^/past-papers/${U}/questions/$`),
    new RegExp(`^/past-papers/${U}/questions/manual/$`),
    new RegExp(`^/past-papers/${U}/external-authorization/$`),
    new RegExp(`^/past-paper-questions/${U}/correct/$`),
    new RegExp(`^/past-paper-questions/${U}/review/$`),
    new RegExp(`^/past-paper-questions/${U}/variations/$`),
    new RegExp(`^/past-paper-variations/${U}/edit/$`),
    new RegExp(`^/past-paper-variations/${U}/review/$`),
);

// Sprint 14 — only these staff-authenticated JSON API paths.
ALLOWED.GET.push(
    /^\/question-generation\/sources\/$/,
    /^\/question-generation\/jobs\/$/,
    new RegExp(`^/question-generation/jobs/${U}/$`),
);
ALLOWED.POST.push(
    /^\/question-generation\/jobs\/$/,
    new RegExp(`^/question-generation/candidates/${U}/edit/$`),
    new RegExp(`^/question-generation/candidates/${U}/action/$`),
    /^\/question-generation\/external-authorizations\/$/,
);

ALLOWED.POST.push(new RegExp(`^/document-intake/staff/${U}/create-unit/$`));

export function permitted(method, path) {
    return (
        Object.hasOwn(ALLOWED, method) &&
        ALLOWED[method].some((pattern) => pattern.test(path))
    );
}

export function segmentPath(segments) {
    return (
        "/" +
        segments.map((segment) => encodeURIComponent(segment)).join("/") +
        "/"
    );
}
