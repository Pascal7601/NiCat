"use client";

import { useParams } from "next/navigation";
import Link from "next/link";

import { Shell, Heading, Notice } from "@/components/Shell";
import { RequestError, useRequest } from "@/components/RequestState";
import StudentTutorExplanation from "@/components/StudentTutorExplanation";

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

    const isFinalized = data?.status === "graded_final";

    return (
        <Shell section="results">
            <Heading
                eyebrow="RESULTS & FEEDBACK"
                title="Your examination result"
                subtitle="Review your performance, examiner feedback, and approved AI study explanations."
            />

            <Link href="/results" className="muted tiny">
                ← All results
            </Link>

            {isDemo && (
                <Notice>
                    Preview results are illustrative only and are not from a
                    real examination submission.
                </Notice>
            )}

            <RequestError message={error} />

            {loading ? (
                <div className="skeleton" />
            ) : data ? (
                <>
                    {/* EXAMINATION SUMMARY */}
                    <section className="card" style={{ marginTop: 24 }}>
                        <div className="row between wrap">
                            <div>
                                <h2>Practice CAT</h2>

                                <p className="muted">
                                    {isFinalized
                                        ? "Your examination has been graded and finalized."
                                        : "Your examination is awaiting final review."}
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
                                awaiting review. Your final percentage will
                                become available after grading is complete.
                            </Notice>
                        )}
                    </section>

                    {/* AI TUTOR AVAILABILITY */}
                    <section className="card" style={{ marginTop: 20 }}>
                        <h2>NiCat AI Study Tutor</h2>

                        {isDemo ? (
                            <p className="muted">
                                AI study explanations are not available for
                                preview examination results.
                            </p>
                        ) : isFinalized ? (
                            <>
                                <p className="muted">
                                    Your examination is finalized. You can now
                                    access available, academically approved
                                    explanations to help you revise.
                                </p>

                                <p className="muted tiny">
                                    AI explanations are supplementary learning
                                    materials. They do not change your marks or
                                    replace your examiner's feedback.
                                </p>
                            </>
                        ) : (
                            <Notice>
                                AI study explanations are locked until your
                                examination results are finalized.
                            </Notice>
                        )}
                    </section>

                    {/* QUESTION REVIEW */}
                    <div className="section-heading">
                        <h2>Question review</h2>
                    </div>

                    <div className="card">
                        {data.items.length === 0 ? (
                            <p className="muted">
                                No question-level results are available.
                            </p>
                        ) : (
                            data.items.map((item, index) => (
                                <div
                                    className="topic-row"
                                    key={`${item.question_id}-${index}`}
                                >
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <strong>Question {index + 1}</strong>

                                        <p className="muted tiny">
                                            {item.explanation ??
                                                (item.status ===
                                                "pending_review"
                                                    ? "Awaiting human review"
                                                    : "Feedback becomes available after finalization")}
                                        </p>

                                        {/* HUMAN REVIEWER FEEDBACK */}
                                        {item.student_feedback && (
                                            <p className="reviewer-feedback">
                                                <strong>
                                                    Reviewer feedback:
                                                </strong>{" "}
                                                {item.student_feedback}
                                            </p>
                                        )}

                                        {/* APPROVED AI TUTOR EXPLANATION */}
                                        {!isDemo && isFinalized && (
                                            <div style={{ marginTop: 16 }}>
                                                <StudentTutorExplanation
                                                    attemptId={id}
                                                    questionId={
                                                        item.question_id
                                                    }
                                                    released={isFinalized}
                                                />
                                            </div>
                                        )}

                                        {/* CORRECT ANSWER */}
                                        {item.correct_answer && (
                                            <p
                                                className="tiny"
                                                style={{
                                                    color: "var(--green)",
                                                }}
                                            >
                                                Correct: {item.correct_answer}
                                            </p>
                                        )}
                                    </div>

                                    {/* QUESTION SCORE */}
                                    <span className="badge">
                                        {item.awarded ?? "Pending"} /{" "}
                                        {item.possible}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                </>
            ) : (
                !error && <div className="empty">No result found.</div>
            )}
        </Shell>
    );
}
