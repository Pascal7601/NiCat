import { NextResponse } from 'next/server';
export const ACCESS_NAME = 'nicat_at';
export const REFRESH_NAME = 'nicat_rt';
const secure = process.env.NODE_ENV === 'production';
/** Both tokens are HttpOnly, same-site, API-path-only cookies. */
export function setTokenCookies(response: NextResponse, access: string, refresh?: string) {
  response.cookies.set(ACCESS_NAME, access, { httpOnly: true, secure, sameSite:'strict', path:'/api', maxAge:15*60 });
  if (refresh) response.cookies.set(REFRESH_NAME, refresh, { httpOnly: true, secure, sameSite:'strict', path:'/api', maxAge:7*24*3600 });
}
export function clearTokenCookies(response: NextResponse) {
  for (const name of [ACCESS_NAME, REFRESH_NAME]) response.cookies.set(name, '', { httpOnly:true, secure, sameSite:'strict', path:'/api', maxAge:0 });
}
