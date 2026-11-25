"use client";

import { useCallback, useEffect, useState } from "react";
import { ClientError, clientRequest } from "@/lib/client";

type Source = {
  excerpt_id: string;
  title: string;
  page: string;
  section: string;
  evidence: string;
};

type FollowUp = {
  id: string;
  question: string;
  status: "draft" | "published" | "rejected" | "withdrawn" | "unavailable";
  created_at: string;
  answer: string | null;
  sources: Source[];
};

type History = {
  remaining_today: number;
  daily_limit: number;
  items: FollowUp[];
};

type Created = { id: string; status: "draft"; review_required: true; message: string; remaining_today: number };

export default function StudentTutorFollowUps({ attemptId, questionId }: {
  attemptId: string;
  questionId: string;
}) {
  const endpoint = `/api/nicat/study-coach/attempts/${encodeURIComponent(attemptId)}/questions/${encodeURIComponent(questionId)}/followups/`;
  const [history, setHistory] = useState<History | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    try {
      const result = await clientRequest<History>(endpoint);
      setHistory(result);
      setError("");
    } catch (err) {
      setError(err instanceof ClientError && err.status === 404
        ? "Follow-up questions are not enabled for this examination."
        : "Could not load follow-up history.");
    }
  }, [endpoint]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function submit() {
    const trimmed = question.trim();
    if (trimmed.length < 12 || trimmed.length > 500) {
      setError("Enter a question between 12 and 500 characters.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await clientRequest<Created>(endpoint, {
        method: "POST",
        body: JSON.stringify({ question: trimmed }),
      });
      setQuestion("");
      setNotice(created.message);
      await refresh();
    } catch (err) {
      if (err instanceof ClientError && err.status === 429) {
        setError("Daily follow-up limit reached. Try again tomorrow.");
      } else if (err instanceof ClientError && err.status === 409) {
        setError("Follow-ups are unavailable until an approved explanation is released.");
      } else {
        setError("Could not submit your follow-up question.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={{ marginTop: 20 }} aria-label="Ask a follow-up about this answer">
      <h4>Ask a follow-up question</h4>
      <p className="muted tiny">
        Questions are reviewed by an academic reviewer. This is not a live chatbot,
        and submitted questions do not change your examination result.
      </p>
      {history && (
        <p className="muted tiny">
          {history.remaining_today} of {history.daily_limit} questions remaining today
        </p>
      )}
      <label htmlFor={`followup-${questionId}`} className="form-label">Your question</label>
      <textarea
        id={`followup-${questionId}`}
        rows={3}
        className="field"
        maxLength={500}
        placeholder="For example: Why must binary search operate on sorted data?"
        value={question}
        disabled={busy || (history !== null && history.remaining_today <= 0)}
        onChange={(event) => setQuestion(event.target.value)}
      />
      <div style={{ marginTop: 8 }} className="row wrap">
        <button
          type="button"
          className="button"
          onClick={() => void submit()}
          disabled={busy || (history !== null && history.remaining_today <= 0)}
        >
          {busy ? "Submitting..." : "Submit for academic review"}
        </button>
        <button type="button" className="button secondary" onClick={() => void refresh()} disabled={busy}>
          Refresh responses
        </button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="muted tiny" role="status">{notice}</p>}
      {history?.items.map((item) => (
        <div className="card" style={{ marginTop: 12 }} key={item.id}>
          <strong>{item.question}</strong>
          <p className="muted tiny">Status: {item.status.replaceAll("_", " ")}</p>
          {item.status === "published" && item.answer ? (
            <>
              <p style={{ whiteSpace: "pre-wrap" }}>{item.answer}</p>
              <strong>Approved sources</strong>
              <ul>
                {item.sources.map((s) => (
                  <li key={s.excerpt_id}>
                    {s.title}{s.page ? `, page ${s.page}` : ""}{s.section ? `, ${s.section}` : ""}
                    <p className="muted tiny">{s.evidence}</p>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="muted tiny">
              {item.status === "draft"
                ? "An academic reviewer has not approved an answer yet."
                : "No approved answer is available for this question."}
            </p>
          )}
        </div>
      ))}
    </section>
  );
}
