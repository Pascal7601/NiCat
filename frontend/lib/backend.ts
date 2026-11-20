/** Server-only request helpers. Backend URL never exposed to client bundles. */
export const BACKEND = (process.env.NICAT_API_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
export async function backendFetch(path: string, options: RequestInit = {}, access?: string) {
  return fetch(`${BACKEND}${path}`, {
    ...options,
    cache: 'no-store',
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(access ? { Authorization: `Bearer ${access}` } : {}), ...options.headers },
  });
}
export async function backendError(res: Response) {
  const body: unknown = await res.json().catch(() => ({}));
  return body && typeof body === 'object' ? body : { detail: `Backend responded ${res.status}` };
}
export function validateOrigin(request: Request) {
  const origin = request.headers.get('origin');
  const trusted = process.env.NICAT_APP_ORIGIN || (process.env.NODE_ENV !== 'production' ? new URL(request.url).origin : '');
  return !!trusted && !!origin && origin === trusted;
}
export const isUUID = (v: string) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
