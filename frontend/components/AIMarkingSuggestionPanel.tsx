"use client";

import { useState } from "react";
import { clientRequest } from "@/lib/client";

type Criterion = {
  criterion_number: number;
  criterion: string;
  max_marks: string;
  awarded: string;
  reason: string;
};

type Suggestion = {
  grade_item_id: string;
  proposed_marks: string;
  breakdown: Criterion[];
  feedback: string;
  model_name: string;
  review_status: "pending" | "accepted" | "overridden";
  generated_at: string;
  human_review_required: true;
};

type Props = {
  gradeItemId: string;
  onApplySuggestedMarks?: (marks: string) => void;
};

/** Reviewer-only component. Does not submit or change a human grade. */
export function AIMarkingSuggestionPanel({ gradeItemId, onApplySuggestedMarks }: Props) {
  const [suggestion, setSuggestion] = useState<Suggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const result = await clientRequest<Suggestion>(
        `/api/nicat/review/grade-items/${encodeURIComponent(gradeItemId)}/ai-suggestion/`,
        { method: "POST" },
      );
      setSuggestion(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate AI suggestion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="card" aria-label="AI marking suggestion" style={{ marginTop: 12 }}>
      <h3>AI marking assistant</h3>
      <p className="muted tiny">
        Optional draft for the reviewer. Your existing human-marking form still
        determines the final score.
      </p>
      {!suggestion && (
        <button type="button" className="button" disabled={loading} onClick={generate}>
          {loading ? "Evaluating answer…" : "Generate rubric-based suggestion"}
        </button>
      )}
      {error && <p role="alert" className="error">{error}</p>}
      {suggestion && (
        <div aria-live="polite">
          <p><strong>Suggested mark: {suggestion.proposed_marks}</strong> (not final)</p>
          <ol>
            {suggestion.breakdown.map((line) => (
              <li key={line.criterion_number} style={{ marginBottom: 12 }}>
                <strong>{line.criterion}</strong>: {line.awarded} / {line.max_marks}
                <p className="muted tiny">{line.reason}</p>
              </li>
            ))}
          </ol>
          <p><strong>Suggested feedback:</strong> {suggestion.feedback}</p>
          {suggestion.review_status !== "pending" && (
            <p className="muted tiny">Human review: {suggestion.review_status}</p>
          )}
          {onApplySuggestedMarks && (
            <button
              type="button"
              className="button"
              onClick={() => onApplySuggestedMarks(suggestion.proposed_marks)}
            >
              Copy suggested marks into review form
            </button>
          )}
          <p className="muted tiny">You must independently verify the rubric before finalizing.</p>
        </div>
      )}
    </section>
  );
}
