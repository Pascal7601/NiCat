"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell, Heading, Notice } from "@/components/Shell";
import { clientRequest } from "@/lib/client";
import { isDemo } from "@/lib/preview";

type Recommendation = {
  topic_id: string;
  topic: string;
  percentage: number;
  questions: number;
  awarded_marks: string;
  possible_marks: string;
  priority: "revise" | "maintain";
  approved_sources_available: boolean;
  guidance: string;
};

type ResponseData = {
  attempts_considered: number;
  recommendations: Recommendation[];
};

export default function RevisionPage() {
  const [data, setData] = useState<ResponseData | null>(null);
  const [loading, setLoading] = useState(!isDemo);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isDemo) return;
    let active = true;
    clientRequest<ResponseData>("/api/nicat/study-coach/recommendations/")
      .then((result) => { if (active) setData(result); })
      .catch(() => { if (active) setError("Could not load personalized revision topics."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <Shell section="results">
      <Heading
        eyebrow="PERSONALIZED REVISION"
        title="Your revision priorities"
        subtitle="Topics ranked using your own finalized practice CAT marks."
      />
      <Link href="/results" className="muted tiny">← Back to examination results</Link>
      {isDemo && <Notice>Revision recommendations require your real finalized practice results.</Notice>}
      {loading && <div className="skeleton" aria-label="Loading recommendations" />}
      {error && <p className="error" role="alert">{error}</p>}
      {data && (
        <>
          <p className="muted tiny">Based on up to {data.attempts_considered} of your most recent finalized attempts.</p>
          {data.recommendations.length === 0 ? (
            <div className="empty">No scored, finalized questions are available yet.</div>
          ) : data.recommendations.map((rec) => (
            <section key={rec.topic_id} className="card" style={{ marginTop: 16 }}>
              <div className="row between wrap">
                <h2>{rec.topic}</h2>
                <span className="badge">{rec.priority === "revise" ? "Revision priority" : "Keep practicing"}</span>
              </div>
              <p><strong>{rec.percentage}%</strong> ({rec.awarded_marks} / {rec.possible_marks} marks)</p>
              <p className="muted tiny">Based on {rec.questions} scored questions in finalized CATs</p>
              <p>{rec.guidance}</p>
              <p className="muted tiny">{rec.approved_sources_available
                ? "Approved study excerpts are available for this topic."
                : "No approved Tutor excerpts are currently available for this topic."}</p>
            </section>
          ))}
          <p className="muted tiny" style={{ marginTop: 20 }}>
            These are study suggestions, not official MMU academic judgments. Practice CAT marks remain unchanged.
          </p>
        </>
      )}
    </Shell>
  );
}
