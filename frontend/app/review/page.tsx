"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Shell, Heading, Notice } from "@/components/Shell";
import { RequestError } from "@/components/RequestState";
import { clientRequest, route } from "@/lib/client";
import { isDemo } from "@/lib/preview";
import { AIMarkingSuggestionPanel } from "@/components/AIMarkingSuggestionPanel";
import { TutorDraftGenerator } from "@/components/TutorDraftGenerator";

import type {
    MarkWrittenResponse,
    PendingWrittenItem,
    PendingWrittenQueue,
} from "@/lib/types";

type Draft = {
    marks: string;
    student_feedback: string;
    rationale: string;
};

const emptyDraft: Draft = {
    marks: "",
    student_feedback: "",
    rationale: "",
};

export default function ReviewPage() {
    const [queue, setQueue] = useState<PendingWrittenQueue | null>(null);

    const [drafts, setDrafts] = useState<Record<string, Draft>>({});

    const [loading, setLoading] = useState(true);
    const [savingId, setSavingId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const loadQueue = useCallback(async () => {
        if (isDemo) {
            setLoading(false);
            return;
        }

        setLoading(true);

        try {
            const result = await clientRequest<PendingWrittenQueue>(
                route.reviewQueue,
            );

            setQueue(result);
            setError(null);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Could not load the review queue.",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void loadQueue();
    }, [loadQueue]);

    const updateDraft = (id: string, key: keyof Draft, value: string) => {
        setDrafts((prev) => ({
            ...prev,
            [id]: {
                ...(prev[id] ?? emptyDraft),
                [key]: value,
            },
        }));
    };

    const mark = async (item: PendingWrittenItem) => {
        const draft = drafts[item.grade_item_id] ?? emptyDraft;
        const marks = Number(draft.marks);

        if (
            !/^\d+(?:\.\d{1,2})?$/.test(draft.marks) ||
            !Number.isFinite(marks) ||
            marks > Number(item.possible_marks)
        ) {
            setError(
                `Enter a mark between 0 and ${item.possible_marks}, ` +
                    "with at most 2 decimals.",
            );
            return;
        }

        if (
            draft.student_feedback.trim().length < 10 ||
            draft.rationale.trim().length < 10
        ) {
            setError(
                "Student feedback and private reviewer rationale " +
                    "must each be at least 10 characters.",
            );
            return;
        }

        setSavingId(item.grade_item_id);
        setError(null);
        setMessage(null);

        try {
            const result = await clientRequest<MarkWrittenResponse>(
                route.markWritten(item.grade_item_id),
                {
                    method: "POST",
                    body: JSON.stringify({
                        marks_awarded: draft.marks,
                        student_feedback: draft.student_feedback.trim(),
                        rationale: draft.rationale.trim(),
                    }),
                },
            );

            setDrafts((prev) => {
                const copy = { ...prev };
                delete copy[item.grade_item_id];
                return copy;
            });

            setMessage(
                result.attempt_status === "graded_final"
                    ? "All answers are graded. The final result is now available."
                    : "Answer marked. Other answers may still be pending.",
            );

            await loadQueue();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Marking failed.");
        } finally {
            setSavingId(null);
        }
    };

    return (
        <Shell section="review">
            <Heading
                eyebrow="ACADEMIC REVIEW"
                title="Written-answer marking"
                subtitle="Review written answers using marking rubrics and optional AI-assisted suggestions. Final marks are awarded by human reviewers."
            />

            <p className="muted tiny">
                Only authorized staff reviewers can access these answers.
            </p>

            {isDemo && (
                <Notice>
                    Reviewer grading requires the live Django backend.
                </Notice>
            )}

            <RequestError message={error} />
            {!isDemo && <TutorDraftGenerator />}

            {message && (
                <p className="review-success" role="status">
                    {message}
                </p>
            )}

            {!isDemo && (
                <div className="row between wrap" style={{ margin: "22px 0" }}>
                    <h2>
                        Pending answers {queue ? `(${queue.count} shown)` : ""}
                    </h2>

                    <button
                        type="button"
                        className="button secondary"
                        disabled={loading || savingId !== null}
                        onClick={() => void loadQueue()}
                    >
                        Refresh queue
                    </button>
                </div>
            )}

            {loading && !isDemo && (
                <div className="skeleton" aria-label="Loading review queue" />
            )}

            {!loading && !isDemo && queue?.count === 0 && (
                <div className="empty">
                    No pending answers right now.{" "}
                    <Link href="/dashboard">Return to dashboard</Link>
                </div>
            )}

            {!isDemo &&
                queue?.items.map((item) => {
                    const id = item.grade_item_id;
                    const draft = drafts[id] ?? emptyDraft;

                    return (
                        <article className="card review-card" key={id}>
                            <div className="row between wrap">
                                <h2>Written response</h2>
                                <span className="badge">
                                    {item.possible_marks} marks possible
                                </span>
                            </div>

                            <p className="muted tiny">
                                Attempt {item.attempt_id.slice(0, 8)}
                                {" · "}
                                {item.kind.replaceAll("_", " ")}
                            </p>

                            <h3>Question</h3>
                            <p className="review-question">{item.prompt}</p>

                            <h3>Student answer</h3>
                            <div className="review-response">
                                {item.response ||
                                    "No written response supplied"}
                            </div>

                            <h3>Marking rubric</h3>
                            <ul className="review-rubric">
                                {item.reviewer_rubric.map((criterion, i) => (
                                    <li key={`${id}-${i}`}>
                                        {criterion.criterion}{" "}
                                        <strong>
                                            ({criterion.max_marks} marks)
                                        </strong>
                                    </li>
                                ))}
                            </ul>

                            {/* AI-ASSISTED MARKING */}
                            <AIMarkingSuggestionPanel
                                gradeItemId={id}
                                onApplySuggestedMarks={(marks) => {
                                    updateDraft(id, "marks", marks);
                                }}
                            />

                            <div className="review-fields">
                                <label>
                                    <span className="form-label">
                                        Marks awarded (0–{item.possible_marks})
                                    </span>
                                    <input
                                        type="number"
                                        className="field"
                                        min="0"
                                        max={item.possible_marks}
                                        step="0.01"
                                        required
                                        value={draft.marks}
                                        disabled={savingId !== null}
                                        onChange={(e) =>
                                            updateDraft(
                                                id,
                                                "marks",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </label>

                                <label>
                                    <span className="form-label">
                                        Student feedback
                                    </span>
                                    <textarea
                                        className="field"
                                        rows={4}
                                        minLength={10}
                                        maxLength={2000}
                                        required
                                        value={draft.student_feedback}
                                        disabled={savingId !== null}
                                        placeholder="Explain what was correct and what can improve."
                                        onChange={(e) =>
                                            updateDraft(
                                                id,
                                                "student_feedback",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </label>

                                <label>
                                    <span className="form-label">
                                        Private reviewer rationale
                                    </span>
                                    <textarea
                                        className="field"
                                        rows={3}
                                        minLength={10}
                                        maxLength={5000}
                                        required
                                        value={draft.rationale}
                                        disabled={savingId !== null}
                                        placeholder="Record how you applied the rubric."
                                        onChange={(e) =>
                                            updateDraft(
                                                id,
                                                "rationale",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </label>
                            </div>

                            <button
                                type="button"
                                className="button"
                                disabled={savingId !== null}
                                onClick={() => void mark(item)}
                            >
                                {savingId === id
                                    ? "Saving review…"
                                    : "Submit review"}
                            </button>
                        </article>
                    );
                })}

            {!!queue?.count && (
                <p className="muted tiny">
                    The queue displays up to 20 pending answers. Refresh after
                    marking to load the next batch.
                </p>
            )}
        </Shell>
    );
}
