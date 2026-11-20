"use client";

import Link from "next/link";
import {
    ArrowRight,
    BookOpen,
    Clock3,
    CheckCircle2,
    ClipboardList,
} from "lucide-react";

import { Shell, Heading, Notice } from "@/components/Shell";
import { RequestError, useRequest } from "@/components/RequestState";

import { route } from "@/lib/client";
import { isDemo } from "@/lib/preview";
import { demoExam, demoHistory } from "@/lib/demo";

import type { Paged, Exam, AttemptHistory } from "@/lib/types";

const previewExams: Paged<Exam> = {
    count: 1,
    next: null,
    previous: null,
    results: [demoExam],
};

export default function Dashboard() {
    const exams = useRequest<Paged<Exam>>(
        route.exams,
        isDemo ? previewExams : undefined,
    );

    const history = useRequest<AttemptHistory[]>(
        route.history,
        isDemo ? demoHistory : undefined,
    );

    const available = exams.data?.results ?? [];
    const attempts = history.data ?? [];

    const currentAttempt = attempts.find(
        (item) => item.status === "in_progress",
    );

    const pendingCount = attempts.filter(
        (item) => item.status === "grading_pending",
    ).length;

    const finalizedCount = attempts.filter(
        (item) => item.status === "graded_final",
    ).length;

    const stats = [
        {
            label: "Published exams",
            value:
                exams.loading || exams.error
                    ? "—"
                    : String(exams.data?.count ?? 0),
        },
        {
            label: "Recent attempts",
            value:
                history.loading || history.error
                    ? "—"
                    : String(attempts.length),
        },
        {
            label: "Final results",
            value:
                history.loading || history.error ? "—" : String(finalizedCount),
        },
        {
            label: "Awaiting review",
            value:
                history.loading || history.error ? "—" : String(pendingCount),
        },
    ];

    return (
        <Shell section="dashboard">
            <Heading
                eyebrow="WELCOME TO NICAT"
                title="Your learning dashboard"
                subtitle="Continue a practice session, explore an exam, or review your progress."
            />

            {isDemo && (
                <Notice>
                    Preview mode — figures are illustrative and do not represent
                    saved results.
                </Notice>
            )}

            <RequestError message={exams.error ?? history.error} />

            <section className="hero">
                <div>
                    <h2>
                        {currentAttempt
                            ? "You have an unfinished examination."
                            : "Make the next CAT your best one."}
                    </h2>

                    <p>
                        {currentAttempt
                            ? "Return to your saved attempt before starting another session."
                            : "Build confidence with focused practice and reviewer feedback."}
                    </p>

                    <Link
                        className="button white"
                        href={
                            currentAttempt
                                ? `/attempts/${currentAttempt.id}`
                                : "/exams"
                        }
                    >
                        {currentAttempt
                            ? "Resume examination"
                            : "Browse practice exams"}

                        <ArrowRight size={17} aria-hidden="true" />
                    </Link>
                </div>

                <BookOpen size={76} strokeWidth={1.2} aria-hidden="true" />
            </section>

            <section className="stat-grid" aria-label="Study summary">
                {stats.map((item) => (
                    <article className="card stat" key={item.label}>
                        <div className="label">{item.label}</div>

                        <div
                            className="value"
                            aria-label={`${item.label}: ${item.value}`}
                        >
                            {item.value}
                        </div>

                        <div className="stat-accent" />
                    </article>
                ))}
            </section>

            <p className="muted tiny">
                Attempt totals show your latest 50 sessions, not your lifetime
                activity.
            </p>

            <div className="section-heading">
                <h2>Available examinations</h2>

                <Link href="/exams" className="text-link">
                    Browse all exams →
                </Link>
            </div>

            {exams.loading ? (
                <div
                    className="skeleton"
                    aria-label="Loading published exams"
                />
            ) : available.length === 0 ? (
                <div className="empty">
                    No published exams are currently available. Once a reviewer
                    approves an exam, it will appear here.
                </div>
            ) : (
                <div className="unit-grid">
                    {available.slice(0, 3).map((exam) => (
                        <article className="card unit-card" key={exam.id}>
                            <span className="unit-icon">
                                <ClipboardList size={22} aria-hidden="true" />
                            </span>

                            <h3>{exam.title}</h3>

                            <p>
                                <Clock3 size={14} aria-hidden="true" />{" "}
                                {Math.round(exam.duration_seconds / 60)} minutes
                            </p>

                            <p className="unit-instructions">
                                {exam.instructions}
                            </p>

                            <footer>
                                <Link
                                    href={`/exams/${exam.id}`}
                                    className="text-link"
                                >
                                    View exam
                                    <ArrowRight size={15} aria-hidden="true" />
                                </Link>
                            </footer>
                        </article>
                    ))}
                </div>
            )}

            <div className="section-heading">
                <h2>Your recent activity</h2>

                <Link href="/results" className="text-link">
                    Attempt history →
                </Link>
            </div>

            {history.loading ? (
                <div
                    className="skeleton"
                    aria-label="Loading recent attempts"
                />
            ) : attempts.length === 0 ? (
                <div className="empty">
                    Your practice history will appear here after you start an
                    examination.
                </div>
            ) : (
                <div className="card">
                    {attempts.slice(0, 3).map((attempt) => (
                        <div className="topic-row" key={attempt.id}>
                            <div>
                                <strong>
                                    {attempt.exam_title ??
                                        "Practice examination"}
                                </strong>

                                <p className="muted tiny">
                                    {new Date(
                                        attempt.started_at,
                                    ).toLocaleString("en-KE", {
                                        timeZone: "Africa/Nairobi",
                                    })}
                                </p>
                            </div>

                            <Link
                                className="text-link"
                                href={
                                    attempt.status === "in_progress" ||
                                    attempt.status === "expired"
                                        ? `/attempts/${attempt.id}`
                                        : `/results/${attempt.id}`
                                }
                            >
                                {attempt.status === "in_progress"
                                    ? "Resume"
                                    : attempt.status === "expired"
                                      ? "View status"
                                      : attempt.status === "grading_pending"
                                        ? "Awaiting review"
                                        : "View result"}

                                {attempt.status === "graded_final" && (
                                    <CheckCircle2
                                        size={16}
                                        aria-hidden="true"
                                    />
                                )}
                            </Link>
                        </div>
                    ))}
                </div>
            )}

            <Notice>
                Practice content is based on archived MMU BBIT materials and is
                not presented as the university's currently verified curriculum.
            </Notice>
        </Shell>
    );
}
