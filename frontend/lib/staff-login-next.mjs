/** Use only known staff destinations. Reject protocol-relative URLs and other redirects. */
export function staffReturnPath(search) {
  const next = new URLSearchParams(search).get('next');
  const staffPages = new Set([
    '/staff',
    '/staff/sources',
    '/staff/tutor',
    '/staff/contributions',
    '/staff/followups',
  ]);
  return staffPages.has(next) ? next : '/dashboard';
}
