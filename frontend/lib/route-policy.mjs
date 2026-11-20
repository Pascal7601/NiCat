
/** Explicitly allow only NiCat's supported API routes. */

const U = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}';

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

  PUT: [
    new RegExp(`^/attempts/${U}/responses/${U}/$`),
  ],
};

export function permitted(method, path) {
  return Object.hasOwn(ALLOWED, method) &&
    ALLOWED[method].some((pattern) => pattern.test(path));
}

export function segmentPath(segments) {
  return '/' + segments.map(
    (segment) => encodeURIComponent(segment)
  ).join('/') + '/';
}
