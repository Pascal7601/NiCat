"use client";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Shell, Heading, Notice } from "@/components/Shell";
import { RequestError, useRequest } from "@/components/RequestState";
import { route } from "@/lib/client";
import { isDemo } from "@/lib/preview";
import { demoResult } from "@/lib/demo";
import type { GradeResult } from "@/lib/types";
export default function ResultDetail() {
    const { id } = useParams<{ id: string }>();
    const { data, error, loading } = useRequest<GradeResult>(
        route.result(id),
        isDemo ? demoResult : undefined,
    );
    return (
        <Shell section="results">
            <Heading
                eyebrow="RESULTS & FEEDBACK"
                title="Your examination result"
                subtitle="Objective scores appear first; descriptive answers require review."
            />
            <Link href="/results" className="muted tiny">
                ← All results
            </Link>
            {isDemo && (
                <Notice>
                    Preview results are illustrative only and not from a real
                    submission.
                </Notice>
            )}
            <RequestError message={error} />
            {loading ? (
                <div className="skeleton" />
            ) : data ? (
                <>
                    <section className="card" style={{ marginTop: 24 }}>
                        <div className="row between wrap">
                            <div>
                                <h2>Practice CAT</h2>
                                <p className="muted">
                                    {data.status === "graded_final"
                                        ? "Finalized result"
                                        : "Review in progress"}
                                </p>
                            </div>
                            <span className="badge">
                                {data.status.replaceAll("_", " ")}
                            </span>
                        </div>
                        <h1>
                            {data.scored_marks} / {data.scored_possible_marks}{" "}
                            <span className="muted tiny">
                                objective/reviewed marks
                            </span>
                        </h1>
                        {data.final_percentage !== null ? (
                            <h2 style={{ color: "var(--green)" }}>
                                {data.final_percentage}% final
                            </h2>
                        ) : (
                            <Notice>
                                {data.ungraded_possible_marks} marks are still
                                awaiting review. A final percentage is not yet
                                available.
                            </Notice>
                        )}
                    </section>
                    <div className="section-heading">
                        <h2>Question review</h2>
                    </div>
                    <div className="card">
                        {data.items.map((item, i) => (
                            <div className="topic-row" key={item.question_id}>
                                <div>
                                    <strong>Question {i + 1}</strong>
                                    <p className="muted tiny">
                                        {item.explanation ??
                                            (item.status === "pending_review"
                                                ? "Awaiting human review"
                                                : "Feedback becomes available after finalization")}
                                    </p>

                                    {item.student_feedback && (
                                        <p className="reviewer-feedback">
                                            <strong>Reviewer feedback:</strong>{" "}
                                            {item.student_feedback}
                                        </p>
                                    )}

                                    {item.correct_answer && (
                                        <p
                                            className="tiny"
                                            style={{ color: "var(--green)" }}
                                        >
                                            Correct: {item.correct_answer}
                                        </p>
                                    )}
                                </div>
                                <span className="badge">
                                    {item.awarded ?? "Pending"} /{" "}
                                    {item.possible}
                                </span>
                            </div>
                        ))}
                    </div>
                </>
            ) : (
                <div className="empty">No result found.</div>
            )}
        </Shell>
    );
}
