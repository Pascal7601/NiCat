# NiCat JWT authentication design (v0.3)

The Django REST API authenticates requests using `Authorization: Bearer <access>`. The Django admin remains cookie/session-authenticated and CSRF-protected, **not** a JWT endpoint.

- Access token: 15 minutes. Refresh token: 7 days.
- Refresh rotation: each successful refresh invalidates the presented refresh token (SimpleJWT blacklist app).
- Logout: requires the caller's access token plus their current refresh token. The submitted refresh token is blacklisted. **Existing access tokens remain valid until expiry.** This is not immediate access-token revocation.
- Password changes invalidate outstanding access tokens via SimpleJWT password-revocation check, subject to verification against the installed package.
- Sign tokens with a production-only `JWT_SIGNING_KEY` independent of Django's secret. HTTPS is mandatory in production.
- Caching and rate limiting: in-memory DRF throttling is only a basic development safeguard. Production needs shared Redis counters plus gateway login rate limiting and abuse monitoring.

## Endpoints

- `POST /api/v1/auth/register/` -> 201 user profile; **does not** auto-login.
- `POST /api/v1/auth/login/` body `{ "email": "...", "password": "..." }` -> `{ "access", "refresh", "user" }`.
- `POST /api/v1/auth/refresh/` body `{ "refresh": "..." }` -> `{ "access", "refresh" }`. The old refresh is invalidated if rotation is enabled.
- `POST /api/v1/auth/logout/` requires bearer access; body `{ "refresh": "..." }` -> 204.
- `GET /api/v1/me/` requires bearer access -> user profile.

## Next.js security boundary

**Recommended:** Next.js BFF (Backend for Frontend): your Next.js server handles login and token refresh, stores refresh tokens in securely scoped `HttpOnly`, `Secure`, `SameSite` cookies and uses a server-side session/refresh flow. Next.js server routes attach access tokens when calling Django. Configure CSRF defenses for every cookie-authenticated state-changing BFF route, not merely Django's bearer-auth endpoints. Do not store JWT refresh tokens in `localStorage`, `sessionStorage`, logs, or analytics.

**API clients:** use the included `frontend-contract/nicat-api.ts` from server-only code. Treat the login response as sensitive and avoid serializing refresh values into React Server Component props or client-rendered HTML.

## Security caveats

- Django's built-in permissions grant reviewer access, but a stolen staff JWT can act with those permissions until expiry.
- Explicit account verification, password reset, account throttling, MFA for reviewers, token pruning, Redis-backed rate limiting and refresh-session management are required before public release.
- Avoid publishing personal data or private answer keys through OpenAPI examples.
