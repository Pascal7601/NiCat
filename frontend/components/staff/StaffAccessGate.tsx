'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { ClientError } from '@/lib/client';
import { staffGet } from '@/lib/staff-workspace';

type GateStatus = 'checking' | 'allowed' | 'forbidden' | 'disabled' | 'error';

export type StaffPermissions = {
  sources: boolean;
  tutor: boolean;
  contributions: boolean;
  followups: boolean;
};

const StaffPermissionsContext = createContext<StaffPermissions | null>(null);
export function useStaffPermissions() {
  return useContext(StaffPermissionsContext);
}

/**
 * Login/navigation guard only. Every staff API must still enforce IsAuthenticated,
 * is_staff, and object/action permissions in Django. The HttpOnly auth cookies are
 * scoped to /api, so /staff cannot read them server-side.
 */
export default function StaffAccessGate({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [status, setStatus] = useState<GateStatus>('checking');
  const [verifiedPath, setVerifiedPath] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<StaffPermissions | null>(null);

  useEffect(() => {
    let mounted = true;
    setStatus('checking');

    staffGet<{ permissions: StaffPermissions }>('/overview/')
      .then((result) => {
        if (mounted) {
          setPermissions(result.permissions);
          setVerifiedPath(pathname);
          setStatus('allowed');
        }
      })
      .catch((error: unknown) => {
        if (!mounted) return;
        if (error instanceof ClientError && error.status === 401) {
          // Only a known, local staff path is sent as the post-login destination.
          const safePath = /^\/staff(?:\/(?:sources|tutor|contributions|followups))?$/.test(pathname)
            ? pathname
            : '/staff';
          router.replace(`/login?next=${encodeURIComponent(safePath)}`);
          return;
        }
        if (error instanceof ClientError && error.status === 403) {
          setStatus('forbidden');
        } else if (error instanceof ClientError && error.status === 404) {
          setStatus('disabled');
        } else {
          setStatus('error');
        }
      });

    return () => { mounted = false; };
  }, [pathname, router]);

  if (status === 'allowed' && verifiedPath === pathname) {
    return (
      <StaffPermissionsContext.Provider value={permissions}>
        {children}
      </StaffPermissionsContext.Provider>
    );
  }

  if (status === 'checking' || (status === 'allowed' && verifiedPath !== pathname)) {
    return (
      <main className="auth-shell" role="status" aria-live="polite">
        <div className="auth-box card">
          <p className="eyebrow">NiCat · Academic workspace</p>
          <h1>Checking staff access…</h1>
          <p className="subhead">Verifying your NiCat session and staff permissions.</p>
        </div>
      </main>
    );
  }

  const heading = status === 'forbidden'
    ? 'Staff access required'
    : status === 'disabled'
      ? 'Staff workspace unavailable'
      : 'Unable to verify access';
  const message = status === 'forbidden'
    ? 'You are signed in, but your account does not have staff workspace permissions.'
    : status === 'disabled'
      ? 'The staff workspace is disabled or unavailable on this server.'
      : 'We could not check your access. Check that the Django API is running, then try again.';

  return (
    <main className="auth-shell">
      <section className="auth-box card" role="alert">
        <p className="eyebrow">NiCat · Academic workspace</p>
        <h1>{heading}</h1>
        <p className="subhead">{message}</p>
        <Link href="/dashboard" className="button ghost">Return to student dashboard</Link>
      </section>
    </main>
  );
}
