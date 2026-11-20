export type UUID = string;
export interface Paged<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}
export interface User {
    id: UUID;
    email: string;
    date_joined: string;
    can_review_written: boolean;
}
export interface Programme {
    id: UUID;
    name: string;
    code: string;
    university_name: string;
}
export interface Exam {
    id: UUID;
    title: string;
    unit_id: UUID;
    duration_seconds: number;
    instructions: string;
}
export type AttemptStatus =
    | "in_progress"
    | "grading_pending"
    | "graded_final"
    | "expired";
export type QuestionKind =
    | "single_choice"
    | "written"
    | "numeric"
    | "code_text"
    | "case_study";
export interface QuestionOption {
    id: UUID;
    text: string;
}
export interface SavedResponse {
    selected_option_id: UUID | null;
    text_answer: string;
}
export interface Question {
    id: UUID;
    position: number;
    kind: QuestionKind;
    prompt: string;
    marks: string;
    topic: string;
    provenance: string;
    options: QuestionOption[];
    response: SavedResponse | null;
}
export interface Attempt {
    id: UUID;
    exam_title?: string;
    status: AttemptStatus;
    started_at: string;
    deadline_at: string;
    submitted_at: string | null;
    questions: Question[];
}
export interface Submission {
    id: UUID;
    status: AttemptStatus;
    result_url: string;
}
export interface GradeItem {
    question_id: UUID;
    status: "pending_review" | "final";
    awarded: string | null;
    possible: string;
    explanation: string | null;
    correct_answer: string | null;
    student_feedback?: string | null;
}
export interface GradeResult {
    attempt_id: UUID;
    status: AttemptStatus;
    scored_marks: string;
    scored_possible_marks: string;
    ungraded_possible_marks: string;
    final_percentage: string | null;
    items: GradeItem[];
}

export interface AttemptHistory {
    id: UUID;
    exam_title?: string;
    status: AttemptStatus;
    started_at: string;
    deadline_at?: string;
    submitted_at?: string | null;
}

export interface PendingWrittenItem {
    grade_item_id: UUID;
    attempt_id: UUID;
    question_id: UUID;
    prompt: string;
    kind: QuestionKind;
    possible_marks: string;
    response: string;
    reviewer_rubric: {
        criterion: string;
        max_marks: string;
    }[];
}

export interface PendingWrittenQueue {
    count: number;
    items: PendingWrittenItem[];
}

export interface MarkWrittenResponse {
    grade_item_id: UUID;
    item_status: "final";
    awarded: string;
    attempt_status: AttemptStatus;
    scored_marks: string;
    scored_possible_marks: string;
    ungraded_possible_marks: string;
    final_percentage: string | null;
}
