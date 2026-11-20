/** Browser talks only to same-origin BFF; JWTs never reach client JavaScript. */
export class ClientError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = 'ClientError'; }
}
export async function clientRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path.startsWith('/api/') ? path : `/api/nicat/${path.replace(/^\//, '')}`, {
    ...options,
    credentials: 'same-origin',
    cache: 'no-store',
    headers: { 'Accept': 'application/json', ...(options.body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null);
    const error = body && typeof body === 'object' ? body as Record<string, unknown> : {};
    const detail = typeof error.message === 'string' ? error.message : typeof error.detail === 'string' ? error.detail : `HTTP ${res.status}`;
    throw new ClientError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
export const isDemo = process.env.NEXT_PUBLIC_NICAT_DEMO_MODE === 'true';
export const route = {
  exams: '/api/nicat/exams/',
  history: '/api/nicat/me/attempts/',
  me: '/api/nicat/me/',
  exam: (id: string) => `/api/nicat/exams/${encodeURIComponent(id)}/`,
  begin: (id: string) => `/api/nicat/exams/${encodeURIComponent(id)}/attempts/`,
  attempt: (id: string) => `/api/nicat/attempts/${encodeURIComponent(id)}/`,
  save: (a: string, q: string) => `/api/nicat/attempts/${encodeURIComponent(a)}/responses/${encodeURIComponent(q)}/`,
  submit: (a: string) => `/api/nicat/attempts/${encodeURIComponent(a)}/submit/`,
  result: (a: string) => `/api/nicat/attempts/${encodeURIComponent(a)}/result/`,
  reviewQueue: '/api/nicat/review/pending/',

  markWritten: (id: string) =>
    `/api/nicat/review/grade-items/${encodeURIComponent(id)}/mark/`,
};
