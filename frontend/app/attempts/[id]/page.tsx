"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Clock3 } from "lucide-react";

import { RequestError, useRequest } from "@/components/RequestState";

import { clientRequest, ClientError, route } from "@/lib/client";

import { isDemo } from "@/lib/preview";
import { demoAttempt } from "@/lib/demo";

import type { Attempt, Question, SavedResponse, Submission } from "@/lib/types";

function isAnswered(question: Question): boolean {
    return question.kind === "single_choice"
        ? Boolean(question.response?.selected_option_id)
        : Boolean(question.response?.text_answer?.trim());
}

export default function AttemptPage() {
    const { id } = useParams<{ id: string }>();
    const router = useRouter();

    const { data, error, loading, setData } = useRequest<Attempt>(
        route.attempt(id),
        isDemo ? demoAttempt : undefined,
    );

    const [selected, setSelected] = useState(0);

    const [drafts, setDrafts] = useState<Record<string, string>>({});

    const [busy, setBusy] = useState(false);

    const [actionError, setActionError] = useState<string | null>(null);

    const [now, setNow] = useState<number | null>(null);

    // Prevent overlapping save and submit requests.
    const lock = useRef(false);

    useEffect(() => {
        const tick = () => setNow(Date.now());

        tick();

        const interval = window.setInterval(tick, 1000);

        return () => window.clearInterval(interval);
    }, []);

    const questions = data?.questions ?? [];
    const current = questions[selected];

    const seconds =
        data && now !== null
            ? Math.max(
                  0,
                  Math.floor(
                      (new Date(data.deadline_at).getTime() - now) / 1000,
                  ),
              )
            : null;

    const expired = seconds === 0;

    const time =
        seconds === null
            ? "--:--"
            : `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(
                  seconds % 60,
              ).padStart(2, "0")}`;

    const writtenDraft =
        current?.kind !== "single_choice" && current
            ? (drafts[current.id] ?? current.response?.text_answer ?? "")
            : "";

    const isDirty = Boolean(
        current &&
        current.kind !== "single_choice" &&
        writtenDraft !== (current.response?.text_answer ?? ""),
    );

    const hasUnsavedText = questions.some(
        (question) =>
            question.kind !== "single_choice" &&
            (drafts[question.id] ?? question.response?.text_answer ?? "") !==
                (question.response?.text_answer ?? ""),
    );

    // Warn before closing a tab containing unsaved work.
    useEffect(() => {
        if (!hasUnsavedText) return;

        const warn = (event: BeforeUnloadEvent) => {
            event.preventDefault();
            event.returnValue = "";
        };

        window.addEventListener("beforeunload", warn);

        return () => {
            window.removeEventListener("beforeunload", warn);
        };
    }, [hasUnsavedText]);

    const persist = useCallback(
        async (
            question: Question,
            response: SavedResponse,
        ): Promise<boolean> => {
            if (!data || lock.current) return false;

            if (!isDemo && Date.now() >= new Date(data.deadline_at).getTime()) {
                setActionError(
                    "Time has expired. New answers cannot be saved; " +
                        "you can still submit previously saved answers.",
                );

                return false;
            }

            lock.current = true;
            setBusy(true);
            setActionError(null);

            try {
                if (!isDemo) {
                    await clientRequest<{
                        saved_at: string;
                    }>(route.save(id, question.id), {
                        method: "PUT",
                        body: JSON.stringify(
                            question.kind === "single_choice"
                                ? {
                                      selected_option_id:
                                          response.selected_option_id,
                                  }
                                : {
                                      text_answer: response.text_answer,
                                  },
                        ),
                    });
                }

                setData((previous) =>
                    previous
                        ? {
                              ...previous,
                              questions: previous.questions.map((entry) =>
                                  entry.id === question.id
                                      ? {
                                            ...entry,
                                            response,
                                        }
                                      : entry,
                              ),
                          }
                        : previous,
                );

                return true;
            } catch (cause) {
                setActionError(
                    cause instanceof Error
                        ? cause.message
                        : "Answer could not be saved.",
                );

                return false;
            } finally {
                lock.current = false;
                setBusy(false);
            }
        },
        [data?.id, data?.deadline_at, id, setData],
    );

    // Debounced written-answer autosave.
    useEffect(() => {
        if (
            !current ||
            current.kind === "single_choice" ||
            !isDirty ||
            expired ||
            busy
        ) {
            return;
        }

        const timer = window.setTimeout(() => {
            void persist(current, {
                selected_option_id: null,
                text_answer: writtenDraft,
            });
        }, 1500);

        return () => window.clearTimeout(timer);
    }, [current?.id, writtenDraft, isDirty, expired, busy, persist]);

    const savedCount = questions.filter(isAnswered).length;

    async function changeQuestion(next: number) {
        if (lock.current || next < 0 || next >= questions.length || !current) {
            return;
        }

        if (isDirty && !expired) {
            const ok = await persist(current, {
                selected_option_id: null,
                text_answer: writtenDraft,
            });

            if (!ok) return;
        }

        if (
            isDirty &&
            expired &&
            !window.confirm(
                "This answer was not saved before the deadline. " +
                    "Leave it and continue?",
            )
        ) {
            return;
        }

        setSelected(next);
    }

    async function submit() {
        if (!data || lock.current) return;

        // Save the active written answer before submission.
        if (current && isDirty && !expired) {
            const ok = await persist(current, {
                selected_option_id: null,
                text_answer: writtenDraft,
            });

            if (!ok) return;
        }

        const countAfterSave = questions.filter((question) => {
            if (current && question.id === current.id && isDirty && !expired) {
                return Boolean(writtenDraft.trim());
            }

            return isAnswered(question);
        }).length;

        const remaining = Math.max(0, questions.length - countAfterSave);

        const warning =
            expired && hasUnsavedText
                ? "Time has expired. Unsaved text will " + "NOT be submitted. "
                : "";

        if (
            !window.confirm(
                `${warning}Submit examination now? ` +
                    `${remaining} question(s) have no saved answer. ` +
                    "Submission cannot be undone.",
            )
        ) {
            return;
        }

        lock.current = true;
        setBusy(true);
        setActionError(null);

        try {
            if (isDemo) {
                router.replace("/results/demo-attempt");
                return;
            }

            await clientRequest<Submission>(route.submit(id), {
                method: "POST",
            });

            router.replace(`/results/${id}`);
        } catch (cause) {
            if (cause instanceof ClientError && cause.status === 409) {
                const latest = await clientRequest<Attempt>(
                    route.attempt(id),
                ).catch(() => null);

                if (latest) {
                    setData(latest);

                    if (
                        latest.status === "graded_final" ||
                        latest.status === "grading_pending"
                    ) {
                        router.replace(`/results/${id}`);
                        return;
                    }
                }
            }

            setActionError(
                cause instanceof Error
                    ? cause.message
                    : "Could not submit examination.",
            );
        } finally {
            lock.current = false;
            setBusy(false);
        }
    }

    if (loading) {
        return (
            <main className="exam-layout">
                <div className="skeleton" aria-label="Loading examination" />
            </main>
        );
    }

    if (!data) {
        return (
            <main className="exam-layout">
                <RequestError message={error ?? "Examination not found."} />
                <Link href="/exams">Back to exams</Link>
            </main>
        );
    }

    if (data.status === "expired") {
        return (
            <main className="exam-layout">
                <h1>Examination expired</h1>
                <p>No further responses can be submitted for this attempt.</p>
                <Link className="button" href="/exams">
                    Browse exams
                </Link>
            </main>
        );
    }

    if (data.status !== "in_progress") {
        return (
            <main className="exam-layout">
                <h1>Examination submitted</h1>
                <Link className="button" href={`/results/${id}`}>
                    View results
                </Link>
            </main>
        );
    }

    return (
        <main className="exam-layout">
            <div className="exam-top">
                <Link
                    className="brand"
                    href="/dashboard"
                    onClick={(event) => {
                        if (
                            hasUnsavedText &&
                            !window.confirm(
                                "You have an unsaved written response. " +
                                    "Leave this exam?",
                            )
                        ) {
                            event.preventDefault();
                        }
                    }}
                >
                    <span className="brand-mark">N</span>
                    NiCat
                </Link>

                <div>
                    <strong>{data.exam_title ?? "Practice examination"}</strong>

                    <div className="muted tiny">
                        Independent academic practice
                    </div>
                </div>

                <span className="badge" role="timer">
                    <Clock3 size={15} aria-hidden="true" />
                    {time} remaining
                </span>
            </div>

            {isDemo && (
                <p className="banner-warning">
                    Preview mode — answers are not saved to Django.
                </p>
            )}

            {expired && (
                <p className="banner-warning" role="alert">
                    Time is up. New answers are blocked by Django. Use{" "}
                    <strong>Submit saved answers</strong> to finalize the work
                    already saved.
                </p>
            )}

            <div style={{ margin: "30px 0 0" }}>
                <div className="row between">
                    <strong>
                        Question {selected + 1} of {questions.length}
                    </strong>

                    <span className="muted tiny">{savedCount} saved</span>
                </div>

                <div
                    className="progress"
                    style={{ marginTop: 12 }}
                    role="progressbar"
                    aria-label="Saved answers"
                    aria-valuenow={savedCount}
                    aria-valuemin={0}
                    aria-valuemax={questions.length}
                >
                    <div
                        style={{
                            width: `${
                                questions.length
                                    ? (100 * savedCount) / questions.length
                                    : 0
                            }%`,
                        }}
                    />
                </div>
            </div>

            <div className="exam-grid">
                <div>
                    <section className="card exam-question-card">
                        {current ? (
                            <>
                                <div className="eyebrow">
                                    {current.topic} · {current.marks} marks
                                </div>

                                <h2 className="question-prompt">
                                    {current.prompt}
                                </h2>

                                {current.kind === "single_choice" ? (
                                    <fieldset className="answer-fieldset">
                                        <legend className="muted tiny">
                                            Select one answer
                                        </legend>

                                        {current.options.map((option) => (
                                            <label
                                                className={`option ${
                                                    current.response
                                                        ?.selected_option_id ===
                                                    option.id
                                                        ? "selected"
                                                        : ""
                                                }`}
                                                key={option.id}
                                            >
                                                <input
                                                    type="radio"
                                                    name={`question-${current.id}`}
                                                    value={option.id}
                                                    checked={
                                                        current.response
                                                            ?.selected_option_id ===
                                                        option.id
                                                    }
                                                    disabled={busy || expired}
                                                    onChange={() =>
                                                        void persist(current, {
                                                            selected_option_id:
                                                                option.id,
                                                            text_answer: "",
                                                        })
                                                    }
                                                />

                                                {option.text}
                                            </label>
                                        ))}
                                    </fieldset>
                                ) : (
                                    <div>
                                        <label
                                            className="form-label"
                                            htmlFor="written-answer"
                                        >
                                            Your answer
                                        </label>

                                        <textarea
                                            id="written-answer"
                                            key={current.id}
                                            className="field"
                                            rows={9}
                                            maxLength={20000}
                                            value={writtenDraft}
                                            disabled={busy || expired}
                                            onChange={(event) =>
                                                setDrafts((previous) => ({
                                                    ...previous,
                                                    [current.id]:
                                                        event.target.value,
                                                }))
                                            }
                                        />

                                        <div
                                            className="row between wrap"
                                            style={{ marginTop: 9 }}
                                        >
                                            <span
                                                className="muted tiny"
                                                role="status"
                                            >
                                                {busy
                                                    ? "Saving…"
                                                    : isDirty
                                                      ? "Unsaved changes — automatically saves after 1.5 seconds"
                                                      : "All changes saved"}
                                            </span>

                                            <button
                                                className="button secondary"
                                                type="button"
                                                disabled={
                                                    !isDirty || busy || expired
                                                }
                                                onClick={() =>
                                                    void persist(current, {
                                                        selected_option_id:
                                                            null,
                                                        text_answer:
                                                            writtenDraft,
                                                    })
                                                }
                                            >
                                                Save answer
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            <p>No questions are available for this attempt.</p>
                        )}
                    </section>

                    <RequestError message={actionError ?? error} />

                    <div className="question-actions">
                        <button
                            className="button ghost"
                            disabled={busy || selected === 0}
                            onClick={() => void changeQuestion(selected - 1)}
                        >
                            ← Previous
                        </button>

                        <button
                            className="button"
                            disabled={busy || selected >= questions.length - 1}
                            onClick={() => void changeQuestion(selected + 1)}
                        >
                            Next question →
                        </button>
                    </div>
                </div>

                <aside className="card exam-nav-card">
                    <h3>Question navigator</h3>

                    <p className="muted tiny">
                        Green means the response is saved.
                    </p>

                    <div className="qnav">
                        {questions.map((question, index) => (
                            <button
                                type="button"
                                key={question.id}
                                aria-label={
                                    `Question ${index + 1}` +
                                    (isAnswered(question) ? ", saved" : "")
                                }
                                aria-current={
                                    selected === index ? "step" : undefined
                                }
                                className={`${
                                    selected === index ? "current" : ""
                                } ${isAnswered(question) ? "answered" : ""}`}
                                disabled={busy}
                                onClick={() => void changeQuestion(index)}
                            >
                                {index + 1}
                            </button>
                        ))}
                    </div>

                    <div style={{ marginTop: 28 }}>
                        <p>{questions.length - savedCount} not yet saved</p>

                        <p className="muted tiny">
                            The server enforces the deadline. Submitted answers
                            cannot be edited.
                        </p>

                        <button
                            className="button full"
                            type="button"
                            disabled={busy || questions.length === 0}
                            onClick={() => void submit()}
                        >
                            {busy
                                ? "Processing…"
                                : expired
                                  ? "Submit saved answers"
                                  : "Submit examination"}
                        </button>
                    </div>
                </aside>
            </div>
        </main>
    );
}
