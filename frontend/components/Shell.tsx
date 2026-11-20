import Link from "next/link";
import ReviewerNavLink from "./ReviewerNavLink";
import {
    BookOpen,
    ChartNoAxesColumnIncreasing,
    LayoutDashboard,
    LogOut,
    GraduationCap,
} from "lucide-react";
import LogoutButton from "./LogoutButton";
export function Shell({
    section,
    children,
}: {
    section: "dashboard" | "exams" | "results" | "review";
    children: React.ReactNode;
}) {
    const links = [
        {
            id: "dashboard",
            href: "/dashboard",
            label: "Dashboard",
            icon: LayoutDashboard,
        },
        { id: "exams", href: "/exams", label: "Browse exams", icon: BookOpen },
        {
            id: "results",
            href: "/results",
            label: "My results",
            icon: ChartNoAxesColumnIncreasing,
        },
    ] as const;
    return (
        <div className="app-frame">
            <aside className="sidebar">
                <Link href="/dashboard" className="brand">
                    <span className="brand-mark">N</span> NiCat
                </Link>
                <p className="tagline">Study smarter. Score higher.</p>
                <div className="nav-label">WORKSPACE</div>
                <nav aria-label="Main navigation">
                    {links.map(({ id, href, label, icon: Icon }) => (
                        <Link
                            key={id}
                            className={`nav-link ${section === id ? "selected" : ""}`}
                            aria-current={section === id ? "page" : undefined}
                            href={href}
                        >
                            <Icon size={18} />
                            {label}
                        </Link>
                    ))}
                    <ReviewerNavLink selected={section === "review"} />
                </nav>
                <div className="sidebar-foot">
                    <GraduationCap size={18} /> MMU · BBIT
                    <br />
                    <span className="tiny">Independent practice platform</span>
                    <LogoutButton />
                </div>
            </aside>
            <main className="main">{children}</main>
        </div>
    );
}
export function Heading({
    eyebrow,
    title,
    subtitle,
}: {
    eyebrow: string;
    title: string;
    subtitle: string;
}) {
    return (
        <>
            <div className="topline">
                <div>
                    <div className="eyebrow">{eyebrow}</div>
                    <h1>{title}</h1>
                    <p className="subhead">{subtitle}</p>
                </div>
                <span className="profile-icon" aria-hidden>
                    NC
                </span>
            </div>
        </>
    );
}
export function Notice({ children }: { children: React.ReactNode }) {
    return (
        <div className="banner-warning" role="note">
            {children}
        </div>
    );
}
