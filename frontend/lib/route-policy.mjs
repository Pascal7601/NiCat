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

const AI_SUGGESTION = new RegExp(`^/review/grade-items/${U}/ai-suggestion/$`);

ALLOWED.GET.push(AI_SUGGESTION);
ALLOWED.POST.push(AI_SUGGESTION);

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
