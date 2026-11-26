import { clientRequest } from "@/lib/client";

export type SourceDocument = {
    id: string;
    title: string;
    unit_id: string | null;
    unit: string;
    source_kind: string;
    rights_status: string;
    source_url: string;
};
export type SourceReference = {
    id: string;
    document_id: string;
    document: string;
    page: string;
    section: string;
};
export type SourceTopic = { id: string; title: string; unit_id: string };
export type SourceExcerpt = {
    id: string;
    state: string;
    topic_id: string;
    topic: string;
    reference_id: string;
    document_id: string;
    document: string;
    rights_status: string;
    text: string;
    approved_by: string | null;
};
export type TutorDraft = {
    id: string;
    state: string;
    version: number;
    revision_id: string;
    question: string;
    topic: string;
    explanation: string;
    common_mistake: string;
    practice_tip: string;
    model_name: string;
    citations: Array<{
        id: string;
        document: string;
        rights_status: string;
        state: string;
        text: string;
    }>;
};
export type ContributionItem = {
    id: string;
    title: string;
    unit: string;
    state: string;
    possible_duplicate: boolean;
    rights_cleared: boolean;
    created_at: string;
};
export type ContributionDetail = ContributionItem & {
    student_id: string;
    body: string;
    author_declaration: boolean;
    allow_display: boolean;
    allow_ai_use: boolean;
    rights_review_note: string;
    academic_review_note: string;
    rights_reviewed_by: string | null;
    academic_reviewed_by: string | null;
    decisions: Array<{
        action: string;
        rationale: string;
        actor_id: string;
        created_at: string;
    }>;
};
export type FollowUpItem = {
    id: string;
    question: string;
    state: string;
    created_at: string;
};
export type FollowUpDetail = FollowUpItem & {
    student_id: string;
    draft_answer: string;
    published_answer: string;
    citations: Array<{
        id: string;
        document: string;
        state: string;
        rights_status: string;
        text: string;
    }>;
};

export const staffUrl = "/api/nicat/staff";
export const staffGet = <T>(path: string) =>
    clientRequest<T>(`${staffUrl}${path}`);
export const staffPost = <T>(path: string, body: unknown) =>
    clientRequest<T>(`${staffUrl}${path}`, {
        method: "POST",
        body: JSON.stringify(body),
    });
export const idPath = (id: string) => encodeURIComponent(id);
export function errorText(err: unknown): string {
    return err instanceof Error ? err.message : "Request failed. Please retry.";
}
