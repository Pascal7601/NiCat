"use client";

import Link from "next/link";

import { Shell, Heading, Notice } from "@/components/Shell";

import { RequestError, useRequest } from "@/components/RequestState";

import { route } from "@/lib/client";
import { isDemo } from "@/lib/preview";
import { demoHistory } from "@/lib/demo";

import type { AttemptHistory } from "@/lib/types";

const labels = {
    in_progress: "In progress",
    grading_pending: "Awaiting written review",
    graded_final: "Result finalized",
    expired: "Expired",
};

export default function Results() {
    const { data, error, loading } = useRequest<AttemptHistory[]>(
        route.history,
        isDemo ? demoHistory : undefined,
    );

    return (
        <Shell section="results">
            <Heading
                eyebrow="RESULTS & FEEDBACK"
                title="Your examination history"
                subtitle="Resume unfinished attempts and review submitted results."
            />

            {isDemo && (
                <Notice>
                    Preview results are illustrative and not linked to a Django
                    account.
                </Notice>
            )}

            <RequestError message={error} />

            {loading ? (
                <div className="skeleton" aria-label="Loading history" />
            ) : !data?.length ? (
                <div className="empty">
                    {error ? (
                        "History could not be loaded."
                    ) : (
                        <>
                            No practice attempts yet.{" "}
                            <Link href="/exams" className="text-link">
                                Browse exams
                            </Link>{" "}
                            to begin.
                        </>
                    )}
                </div>
            ) : (
                <div className="activity-list">
                    {data.map((attempt) => {
                        const resumable = attempt.status === "in_progress";

                        const submitted =
                            attempt.status === "grading_pending" ||
                            attempt.status === "graded_final";

                        const destination = submitted
                            ? `/results/${attempt.id}`
                            : `/attempts/${attempt.id}`;

                        return (
                            <Link
                                key={attempt.id}
                                href={destination}
                                className="card activity-row"
                            >
                                <div>
                                    <strong>
                                        {attempt.exam_title ??
                                            "Practice examination"}
                                    </strong>

                                    <p className="muted tiny">
                                        Started{" "}
                                        {new Date(
                                            attempt.started_at,
                                        ).toLocaleString("en-KE", {
                                            timeZone: "Africa/Nairobi",
                                        })}
                                    </p>
                                </div>

                                <div className="activity-state">
                                    <span className="badge">
                                        {labels[attempt.status]}
                                    </span>

                                    <strong className="text-link">
                                        {resumable
                                            ? "Resume →"
                                            : submitted
                                              ? "View results →"
                                              : "View status →"}
                                    </strong>
                                </div>
                            </Link>
                        );
                    })}
                </div>
            )}

            <p className="muted tiny">
                The history displays the most recent 50 attempts.
            </p>
        </Shell>
    );
}
