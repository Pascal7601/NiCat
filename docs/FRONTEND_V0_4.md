# NiCat v0.4 — Student Frontend & Figma Handoff

Status: implementation preview, **not a verified production release**. Extends the v0.3 Django + DRF + SimpleJWT API. No backend domain models were removed or replaced.

## Figma (Soramap)

Editable source: https://www.figma.com/design/ZFkfJTgyrnFm2pkEYXWOJW

Screens: **01 Student Dashboard**, **02 Browse Exams**, **03 DSA Exam Session**, **04 Results & Review**. Visual design: navy sidebar, violet CTA, light study canvas, accessible text, responsive cards. The four screens were created in an authenticated Figma file in the Soramap workspace (Viewer workspace access may limit later editing by this connected identity). NiCat semantic color variables and reusable navigation/stat components are included.

## Scope and screen flows

| Screen | Browser path | Django API | States |
|---|---|---|---|
| Sign in | `/login` | `POST /auth/login/` | invalid credentials, pending, success |
| Register | `/register` | `POST /auth/register/` | invalid, duplicate, success |
| Dashboard | `/dashboard` | `GET /exams/`, `/me/attempts/` | empty, loading, error, populated |
| Practice catalogue | `/exams` | `GET /exams/` | loading, search, empty, results |
| Exam details | `/exams/[id]` | `GET /exams/{id}/` | unavailable, begin, error |
| Attempt | `/attempts/[id]` | `GET /attempts/{id}/`; PUT answer; POST submit | timer, selection, written text, saving, conflict, expired |
| Results history | `/results` | `GET /me/attempts/` | empty, loading, finished, grading pending |
| Result details | `/results/[id]` | `GET /attempts/{id}/result/` | partial reviewed marks, pending, final |

- Django is authoritative for timing, grading, question access, attempts, marking and result ownership. Browser timers are indicative only.
- Questions are served from the attempt snapshot; answer keys are never bundled into the client.
- Until written marking is complete, display **pending review** rather than a misleading total percentage.
- Study-unit summaries on the dashboard come from the historical inventory and are clearly labeled as unverified against the current MMU curriculum.

## Security: JWT browser-for-frontend gateway

Next.js uses Route Handlers as a same-origin browser-for-frontend (BFF). Only the BFF communicates with Django using `Authorization: Bearer <access_token>`. HTTP-only Secure (production) / SameSite=Strict cookies store access and rotating refresh tokens. The browser never receives JWTs as JSON, never stores them in localStorage and never connects to the Django API directly.

- `POST /api/auth/login` obtains a token pair server-side, sets cookies, and returns a profile-only JSON response.
- `POST /api/auth/register` validates request origin and forwards registration.
- `POST /api/auth/logout` tries to blacklist the refresh token (rotating first if the access token expired) and clears local cookies regardless of network failure.
- `/api/nicat/[...segments]` is **allowlisted** by HTTP method and path. Unknown endpoints are not proxied.
- State-changing requests require a configured exact `NICAT_APP_ORIGIN`. Same-site cookies are supplemental protection, not a replacement for origin checks.
- Refresh-on-401 is performed server-side, with rotated tokens re-set in HTTP-only cookies. Invalid sessions are cleared.
- Backend secret keys and raw tokens must not enter Next.js public environment variables, UI logs, analytics or error telemetry.

**Release security work:** obtain a full production security review, add session and token-revocation tests, instrument refresh races and retry behavior, ensure input/rate limits at the reverse proxy, and verify CSRF/origin behavior under the actual deployment domain.

## Run locally (WSL / Docker)

**Backend:** from project root:

```bash
cp .env.example .env
# Replace placeholders in .env: DJANGO_SECRET_KEY, JWT_SIGNING_KEY, DB settings
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
set -a; source .env; set +a
docker compose up -d db
bash scripts/bootstrap-migrations.sh  # inspect ALL generated migrations; not verified here
bash scripts/verify-backend.sh
cd backend
python manage.py seed_dsa_pilot  # DRAFT; reviewer approval before publication
python manage.py runserver
```

**Frontend:** from `frontend/` in another terminal:

```bash
cp .env.example .env.local
npm install
npm run typecheck
npm run test:contract
npm run dev
```

Open `http://localhost:3000`. Ensure `NICAT_APP_ORIGIN=http://localhost:3000` (not 127.0.0.1, unless you configure both origin and browser URL to match).

For *local preview only*, set `NEXT_PUBLIC_NICAT_DEMO_MODE=true` in frontend `.env.local`, then restart Next.js. Preview mode does not write to Django and is explicitly disabled by code in production builds.

The DSA pilot remains **draft** and will not appear in the real catalogue until an authorized academic reviewer publishes it.

## Test and release gates

**Verified in this artifact session:** Python syntax compilation, four standalone grading tests, three frontend proxy allowlist tests, and TypeScript/TSX syntax parsing. Editable Figma frames were created successfully and their IDs returned.

**Not verified:** full Next.js typecheck/build (dependencies not installed), full Django/DRF tests (packages unavailable), PostgreSQL migrations/concurrency tests (no executable), generated OpenAPI reconciliation, end-to-end auth/UI test, deployed production security. Existing `migrations` folders only contain initializers — **there are no reviewed migration operations to commit**.

Do not label PostgreSQL as green until `scripts/verify-backend.sh` runs successfully on actual PostgreSQL. Verify and review migrations in WSL/CI; commit them only after review. Commit the generated frontend lockfile after running `npm install`.

## Developer notes

- `frontend/lib/types.ts`: DTO types that mirror the v0.3 contract.
- `frontend/lib/client.ts`: browser requests only to same-origin BFF endpoints.
- `frontend/lib/backend.ts`: server-only backend host and origin checks.
- `frontend/lib/cookies.ts`: secure HTTP-only token cookie helpers.
- `frontend/lib/route-policy.mjs`: allowlist for authenticated proxy routes.
- `frontend/lib/demo.ts`: clearly separate visual fixtures, not live results.
- `frontend/components/*`: reusable layout, logout and request state.
- `frontend/app/*`: page UI, auth Route Handlers and Django proxy.

## Remaining engineering backlog

1. Install dependencies and generate/review Django migrations; complete a green PostgreSQL CI run.
2. Add tests for BFF access-token expiry, refresh-token rotation, origin validation, and session revocation.
3. Run a complete Next.js typecheck/build with pinned package lock.
4. Validate each UI screen against the Figma file at desktop and mobile widths.
5. Add explicit save button and unsaved-change guard for long written exam responses.
6. Add backend-supported pagination/filtering for extensive exams and result histories.
7. Complete academic review and publication of DSA pilot, then true end-to-end execution.
