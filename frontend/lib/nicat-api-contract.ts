/** NiCat v0.3 Next.js integration contract. Keep tokens on the server side. */
export type UUID = string;
export type ISODate = string;
export type DecimalString = string;
export type AttemptStatus = "in_progress" | "grading_pending" | "graded_final" | "expired";
export type QuestionKind = "single_choice" | "written" | "code_text" | "numeric" | "case_study";

export interface ApiPage<T> { count: number; next: string | null; previous: string | null; results: T[] }
export interface UserProfile { id: UUID; email: string; date_joined: ISODate }
export interface TokenPair { access: string; refresh: string; user: UserProfile }
export interface TokenRefresh { access: string; refresh: string }
export interface Programme { id: UUID; name: string; code: string; university_name: string }
export interface Curriculum { id: UUID; label: string; is_officially_verified: boolean; reference_url: string }
export interface UnitPlacement {
  id: UUID; unit_id: UUID; unit_name: string; year_number: number; semester_number: number;
  displayed_code: string; code_verification_status: string;
}
export interface Topic { id: UUID; parent_id: UUID | null; title: string; position: number }
export interface Exam {
  id: UUID; title: string; unit_id: UUID; duration_seconds: number; instructions: string;
}
export interface QuestionOption { id: UUID; text: string }
export interface StudentAnswer { selected_option_id: UUID | null; text_answer: string }
export interface AttemptQuestion {
  id: UUID; position: number; kind: QuestionKind; prompt: string; marks: DecimalString;
  topic: string; provenance: string; options: QuestionOption[]; response: StudentAnswer | null;
}
export interface Attempt {
  id: UUID; status: AttemptStatus; started_at: ISODate; deadline_at: ISODate;
  submitted_at: ISODate | null; questions: AttemptQuestion[];
}
export interface Submission { id: UUID; status: AttemptStatus; result_url: string }
export interface GradeResultItem {
  question_id: UUID; status: "pending_review" | "final";
  awarded: DecimalString | null; possible: DecimalString;
  explanation: string | null; correct_answer: string | null;
}
export interface GradeResult {
  attempt_id: UUID; status: AttemptStatus; scored_marks: DecimalString;
  scored_possible_marks: DecimalString; ungraded_possible_marks: DecimalString;
  final_percentage: DecimalString | null; items: GradeResultItem[];
}
export interface AttemptHistory { id: UUID; status: AttemptStatus; started_at: ISODate }
export interface ApiErrorBody { code?: string; message?: string; detail?: string | unknown }

export class NiCatApiError extends Error {
  constructor(public readonly status: number, public readonly body: ApiErrorBody) {
    super(body.message || (typeof body.detail === "string" ? body.detail : `HTTP ${status}`));
    this.name = "NiCatApiError";
  }
}

/** For server-side Next.js route handlers or server actions. Never expose refresh tokens to the browser. */
export class NiCatApi {
  constructor(private readonly baseURL: string, private readonly accessToken?: string) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body !== undefined) headers.set("Content-Type", "application/json");
    if (this.accessToken) headers.set("Authorization", `Bearer ${this.accessToken}`);
    const response = await fetch(`${this.baseURL.replace(/\/$/, "")}/api/v1${path}`, {
      ...init, headers, cache: "no-store",
    });
    if (response.status === 204) return undefined as T;
    const json: unknown = await response.json().catch(() => ({}));
    if (!response.ok) throw new NiCatApiError(response.status, json as ApiErrorBody);
    return json as T;
  }

  register(email: string, password: string) {
    return this.request<UserProfile>("/auth/register/", {
      method: "POST", body: JSON.stringify({ email, password }),
    });
  }
  login(email: string, password: string) {
    return this.request<TokenPair>("/auth/login/", {
      method: "POST", body: JSON.stringify({ email, password }),
    });
  }
  refresh(refresh: string) {
    return this.request<TokenRefresh>("/auth/refresh/", {
      method: "POST", body: JSON.stringify({ refresh }),
    });
  }
  logout(refresh: string) {
    return this.request<void>("/auth/logout/", {
      method: "POST", body: JSON.stringify({ refresh }),
    });
  }
  me() { return this.request<UserProfile>("/me/"); }
  programmes() { return this.request<ApiPage<Programme>>("/programmes/"); }
  curricula(programmeID: UUID) { return this.request<ApiPage<Curriculum>>(`/programmes/${programmeID}/curricula/`); }
  units(curriculumID: UUID) { return this.request<ApiPage<UnitPlacement>>(`/curricula/${curriculumID}/units/`); }
  topics(unitID: UUID) { return this.request<ApiPage<Topic>>(`/units/${unitID}/topics/`); }
  exams(unitID?: UUID) {
    return this.request<ApiPage<Exam>>(`/exams/${unitID ? `?unit_id=${encodeURIComponent(unitID)}` : ""}`);
  }
  exam(examID: UUID) { return this.request<Exam>(`/exams/${examID}/`); }
  startExam(examID: UUID) {
    return this.request<Attempt>(`/exams/${examID}/attempts/`, { method: "POST" });
  }
  attempt(attemptID: UUID) { return this.request<Attempt>(`/attempts/${attemptID}/`); }
  saveChoice(attemptID: UUID, questionID: UUID, selectedOptionID: UUID | null) {
    return this.request<{ saved_at: ISODate }>(`/attempts/${attemptID}/responses/${questionID}/`, {
      method: "PUT", body: JSON.stringify({ selected_option_id: selectedOptionID }),
    });
  }
  saveWritten(attemptID: UUID, questionID: UUID, textAnswer: string) {
    return this.request<{ saved_at: ISODate }>(`/attempts/${attemptID}/responses/${questionID}/`, {
      method: "PUT", body: JSON.stringify({ text_answer: textAnswer }),
    });
  }
  submit(attemptID: UUID) {
    return this.request<Submission>(`/attempts/${attemptID}/submit/`, { method: "POST" });
  }
  result(attemptID: UUID) { return this.request<GradeResult>(`/attempts/${attemptID}/result/`); }
  history() { return this.request<AttemptHistory[]>("/me/attempts/"); }
}
