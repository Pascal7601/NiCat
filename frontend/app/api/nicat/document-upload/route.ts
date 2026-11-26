/** Narrow, authenticated multipart bridge; the existing catchall BFF stays JSON-only. */
import { NextRequest, NextResponse } from 'next/server';
import { ACCESS_NAME, REFRESH_NAME, clearTokenCookies, setTokenCookies } from '@/lib/cookies';
import { BACKEND, backendFetch, validateOrigin } from '@/lib/backend';

export const runtime = 'nodejs';
const NO_STORE = {'Cache-Control':'private, no-store, max-age=0', 'Vary':'Cookie'};
const MAX_FILE = 8 * 1024 * 1024;
const MAX_WIRE = MAX_FILE + 64 * 1024;
const FIELDS = [
  'programme_id','unit_id','suggested_unit_title','suggested_unit_code',
  'year_number','semester_number','title','description','suggested_topics',
  'document_type','rights_basis','rights_evidence','author_or_owner',
  'permit_question_generation','permit_resource_display','permit_tutor_use',
];
const fail = (detail:string,status:number) => NextResponse.json({detail},{status,headers:NO_STORE});

export async function POST(request:NextRequest) {
  if (!validateOrigin(request)) return fail('Origin not allowed',403);
  if (request.nextUrl.search) return fail('Query parameters not allowed',400);
  const length = Number(request.headers.get('content-length'));
  if (!Number.isFinite(length) || length < 1) return fail('Content-Length required',411);
  if (length > MAX_WIRE) return fail('Upload exceeds maximum request size',413);
  const access = request.cookies.get(ACCESS_NAME)?.value;
  const refresh = request.cookies.get(REFRESH_NAME)?.value;
  if (!access && !refresh) return fail('Sign in required',401);
  const type = request.headers.get('content-type') || '';
  if (!type.toLowerCase().startsWith('multipart/form-data;')) return fail('Expected multipart form data',415);

  let form:FormData;
  try { form = await request.formData(); } catch { return fail('Invalid multipart body',400); }
  const uploads = form.getAll('file');
  if (uploads.length !== 1 || !(uploads[0] instanceof File)) return fail('Select exactly one file',400);
  const file = uploads[0] as File;
  if (file.size < 1 || file.size > MAX_FILE) return fail('File is empty or exceeds 8 MB',413);
  if (!/\.(pdf|txt)$/i.test(file.name)) return fail('Only PDF/TXT files are allowed',415);
  if (Array.from(form.keys()).some(key => key !== 'file' && !FIELDS.includes(key))) return fail('Unexpected form field',400);
  const forwarded = new FormData();
  for (const name of FIELDS) {
    const values = form.getAll(name);
    if (values.length > 1 || values.some(v => typeof v !== 'string')) return fail('Invalid metadata',400);
    if (values.length === 1) {
      const value = values[0] as string;
      if (value.length > 1200) return fail('Metadata field too long',400);
      if (value) forwarded.append(name,value);
    }
  }
  forwarded.append('file',file,file.name);

  async function forward(token:string) {
    return fetch(`${BACKEND}/document-intake/`, {
      method:'POST', cache:'no-store',
      headers:{Authorization:`Bearer ${token}`,Accept:'application/json'},
      body:forwarded,
    });
  }
  try {
    let response = access ? await forward(access) : null;
    let rotated: {access:string,refresh:string}|null = null;
    if ((!response || response.status === 401) && refresh) {
      const renewal = await backendFetch('/auth/refresh/',{
        method:'POST', body:JSON.stringify({refresh}),
      });
      if (renewal.ok) {
        const tokens = await renewal.json();
        if (typeof tokens.access === 'string' && typeof tokens.refresh === 'string') {
          rotated = {access:tokens.access,refresh:tokens.refresh};
          response = await forward(rotated.access);
        }
      }
    }
    if (!response || response.status === 401) {
      const out = fail('Session expired. Please sign in again.',401);
      clearTokenCookies(out);
      return out;
    }
    const data = await response.json().catch(() => ({detail:'Backend response unavailable'}));
    const out = NextResponse.json(data,{status:response.status,headers:NO_STORE});
    if (rotated) setTokenCookies(out,rotated.access,rotated.refresh);
    return out;
  } catch {
    return fail('Document service unavailable',502);
  }
}
