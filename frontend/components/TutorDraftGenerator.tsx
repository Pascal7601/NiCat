"use client";

import { useState } from "react";
import { clientRequest } from "@/lib/client";

type TutorDraftResponse = {
    id: string;
    status: "draft";
    version: number;
    review_required: boolean;
    admin_review_path: string;
};

export function TutorDraftGenerator() {
    const [revisionId, setRevisionId] = useState("");
    const [draft, setDraft] = useState<TutorDraftResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function generateDraft() {
        const id = revisionId.trim();

        if (
            !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
                id,
            )
        ) {
            setError("Enter a valid question revision UUID.");
            return;
        }

        setLoading(true);
        setError(null);
        setDraft(null);

        try {
            const result = await clientRequest<TutorDraftResponse>(
                `/api/nicat/study-tutor/revisions/${encodeURIComponent(id)}/draft/`,
                {
                    method: "POST",
                },
            );

            setDraft(result);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to generate the Tutor explanation.",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <section
            className="card"
            style={{ marginTop: 24, marginBottom: 24 }}
            aria-label="AI Tutor draft generator"
        >
            <h2>NiCat AI Tutor — Draft Generator</h2>

            <p className="muted">
                Generate a revision explanation using approved academic source
                excerpts.
            </p>

            <p className="muted tiny">
                The generated explanation is a draft. It must be reviewed and
                published by an authorized academic reviewer before students can
                access it.
            </p>

            <div style={{ marginTop: 16 }}>
                <label htmlFor="tutor-revision-id" className="form-label">
                    Question revision ID
                </label>

                <input
                    id="tutor-revision-id"
                    type="text"
                    className="field"
                    placeholder="Enter question revision UUID"
                    value={revisionId}
                    disabled={loading}
                    onChange={(event) => {
                        setRevisionId(event.target.value);
                        setDraft(null);
                        setError(null);
                    }}
                />
            </div>

            <button
                type="button"
                className="button"
                style={{ marginTop: 16 }}
                disabled={loading || !revisionId.trim()}
                onClick={() => void generateDraft()}
            >
                {loading
                    ? "Generating explanation..."
                    : "Generate AI Tutor draft"}
            </button>

            {error && (
                <p role="alert" className="error" style={{ marginTop: 12 }}>
                    {error}
                </p>
            )}

            {draft && (
                <div style={{ marginTop: 20 }}>
                    <h3>Draft created</h3>

                    <p>
                        <strong>Draft ID:</strong> {draft.id}
                    </p>

                    <p>
                        <strong>Version:</strong> {draft.version}
                    </p>

                    <p>
                        <strong>Status:</strong> {draft.status}
                    </p>

                    <p className="muted tiny">
                        Human academic review is required before publication.
                    </p>

                    <p>
                        <strong>Django Admin path:</strong>
                    </p>

                    <code style={{ overflowWrap: "anywhere" }}>
                        {draft.admin_review_path}
                    </code>

                    <p className="muted tiny">
                        Open this path on your Django backend at localhost:8000
                        to review and publish the draft.
                    </p>
                </div>
            )}
        </section>
    );
}
