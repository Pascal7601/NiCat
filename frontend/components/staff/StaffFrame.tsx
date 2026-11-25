'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { ReactNode } from 'react';
import {
  BookOpenCheck,
  BookMarked,
  ClipboardCheck,
  FileCheck2,
  GraduationCap,
  LayoutDashboard,
  LibraryBig,
  MessageSquareText,
} from 'lucide-react';
import LogoutButton from '@/components/LogoutButton';
import { useStaffPermissions } from '@/components/staff/StaffAccessGate';

const staffLinks = [
  { href: '/staff', label: 'Overview', icon: LayoutDashboard, permission: null },
  { href: '/staff/sources', label: 'Source library', icon: LibraryBig, permission: 'sources' },
  { href: '/staff/tutor', label: 'AI Tutor review', icon: BookOpenCheck, permission: 'tutor' },
  { href: '/staff/contributions', label: 'Contributions', icon: FileCheck2, permission: 'contributions' },
  { href: '/staff/followups', label: 'Follow-up reviews', icon: MessageSquareText, permission: 'followups' },
] as const;

export default function StaffFrame({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const permissions = useStaffPermissions();

  return (
    <div className="app-frame staff-workspace">
      <aside className="sidebar staff-sidebar" aria-label="Academic staff sidebar">
        <Link href="/staff" className="brand">
          <span className="brand-mark">N</span>
          NiCat
        </Link>
        <p className="tagline">Study smarter. Score higher.</p>

        <div className="nav-label">ACADEMIC WORKSPACE</div>
        <nav aria-label="Staff navigation" className="staff-nav">
          {staffLinks.filter(link => !link.permission || permissions?.[link.permission]).map(({ href, label, icon: Icon }) => {
            const selected =
              pathname === href ||
              (href !== '/staff' && pathname.startsWith(`${href}/`));
            return (
              <Link
                key={href}
                href={href}
                className={`nav-link ${selected ? 'selected' : ''}`}
                aria-current={selected ? 'page' : undefined}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="nav-label">EXAM OPERATIONS</div>
        <nav aria-label="Marking" className="staff-nav">
          <Link className="nav-link" href="/review">
            <ClipboardCheck size={18} aria-hidden="true" />
            <span>Written-answer marking</span>
          </Link>
          <Link className="nav-link" href="/dashboard">
            <BookMarked size={18} aria-hidden="true" />
            <span>Student dashboard</span>
          </Link>
        </nav>

        <div className="sidebar-foot">
          <div className="staff-foot-label">
            <GraduationCap size={18} aria-hidden="true" />
            <span>MMU · BBIT</span>
          </div>
          <span className="tiny">Authorized academic workspace</span>
          <LogoutButton />
        </div>
      </aside>

      <main className="main staff-main" id="main-content">
        <header className="topline staff-topline">
          <div>
            <div className="eyebrow">NICAT · STAFF WORKSPACE</div>
            <h1>{title}</h1>
            <p className="subhead">{description}</p>
          </div>
          <span className="profile-icon" aria-hidden="true">ST</span>
        </header>
        <div className="staff-content">{children}</div>
      </main>
    </div>
  );
}
