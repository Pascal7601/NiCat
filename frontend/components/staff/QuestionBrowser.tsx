'use client';

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { errorText, staffPost } from '@/lib/staff-workspace';
import styles from './QuestionBrowser.module.css';

export type PublishedQuestion = {
  id: string;
  question_id: string;
  prompt: string;
  kind: string;
  version: number;
  max_marks: string;
  unit_id: string;
  unit: string;
  topic_id: string;
  topic: string;
  approved_excerpt_count: number;
  tutor_state: string | null;
};

type FilterOption = { id: string; title: string };
type Programme = { id: string; name: string; university: string };
type TopicOption = FilterOption & { unit_id: string };
type QuestionSearchResult = {
  items: PublishedQuestion[];
  programmes: Programme[];
  units: FilterOption[];
  topics: TopicOption[];
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
};
type Filters = { search: string; programme_id: string; unit_id: string; topic_id: string };
const EMPTY: Filters = { search: '', programme_id: '', unit_id: '', topic_id: '' };
const PAGE_SIZE = 20;

/** Shared read-only question discovery. Only caller can request Tutor draft generation. */
export default function QuestionBrowser({
  onSelect,
  selectedId,
}: {
  onSelect?: (question: PublishedQuestion | null) => void;
  selectedId?: string;
}) {
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [data, setData] = useState<QuestionSearchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const requestNumber = useRef(0);

  const load = useCallback(async (next: Filters, offset = 0) => {
    const id = ++requestNumber.current;
    setBusy(true);
    setError('');
    try {
      const result = await staffPost<QuestionSearchResult>('/questions/search/', {
        ...next,
        programme_id: next.programme_id || null,
        unit_id: next.unit_id || null,
        topic_id: next.topic_id || null,
        offset,
        limit: PAGE_SIZE,
      });
      if (requestNumber.current === id) setData(result);
    } catch (exc) {
      if (requestNumber.current === id) setError(errorText(exc));
    } finally {
      if (requestNumber.current === id) setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load(EMPTY);
    return () => { requestNumber.current += 1; };
  }, [load]);

  function updateFilters(next: Filters) {
    setFilters(next);
    onSelect?.(null);
    void load(next);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSelect?.(null);
    void load(filters);
  }

  return (
    <section className={`card ${styles.browser}`} aria-label="Published question browser">
      <div className={styles.heading}>
        <div>
          <h2>Find a published question</h2>
          <p className="muted tiny">Search by unit, topic or question text. IDs are handled internally.</p>
        </div>
        {data && <span className={styles.total}>{data.total} matching</span>}
      </div>

      <form onSubmit={submit} className={styles.filters}>
        <label>
          <span className="form-label">Programme</span>
          <select className="field" value={filters.programme_id} onChange={e => updateFilters({ ...filters, programme_id: e.target.value, unit_id: '', topic_id: '' })}>
            <option value="">All programmes</option>
            {(data?.programmes ?? []).map(p => <option key={p.id} value={p.id}>{p.name} · {p.university}</option>)}
          </select>
        </label>
        <label>
          <span className="form-label">Unit</span>
          <select className="field" value={filters.unit_id} onChange={e => updateFilters({ ...filters, unit_id: e.target.value, topic_id: '' })}>
            <option value="">All units</option>
            {(data?.units ?? []).map(u => <option key={u.id} value={u.id}>{u.title}</option>)}
          </select>
        </label>
        <label>
          <span className="form-label">Topic</span>
          <select className="field" value={filters.topic_id} onChange={e => updateFilters({ ...filters, topic_id: e.target.value })}>
            <option value="">All topics</option>
            {(data?.topics ?? []).map(t => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
        </label>
        <label className={styles.searchField}>
          <span className="form-label">Question or keyword</span>
          <input className="field" maxLength={120} placeholder="Search published questions…" value={filters.search} onChange={e => setFilters(previous => ({ ...previous, search: e.target.value }))} />
        </label>
        <button className="button" type="submit" disabled={busy}>Search questions</button>
      </form>

      {error && <p className="error" role="alert">{error}</p>}
      {busy && <p className="muted" role="status">Loading published questions…</p>}
      {!busy && data?.items.length === 0 && <p className="muted" role="status">No published questions match these filters. Staff must publish and validate questions before they appear here.</p>}

      <div className={styles.results} role="list">
        {(data?.items ?? []).map(question => (
          <div role="listitem" key={question.id} className={`${styles.question} ${selectedId === question.id ? styles.selected : ''}`}>
            <div className={styles.meta}>
              <span>{question.unit} · {question.topic}</span>
              <span>{question.kind.replaceAll('_', ' ')} · v{question.version} · {question.max_marks} marks</span>
            </div>
            <p className={styles.prompt}>{question.prompt}</p>
            <div className={styles.bottom}>
              <span className="muted tiny">
                {question.approved_excerpt_count > 0
                  ? `${question.approved_excerpt_count} approved topic excerpt(s) — match verified when generating`
                  : 'No approved topic sources yet'}
                {question.tutor_state ? ` · Tutor: ${question.tutor_state}` : ''}
              </span>
              {onSelect && <button type="button" className={`button ${selectedId === question.id ? '' : 'ghost'}`} aria-pressed={selectedId === question.id} disabled={busy || question.approved_excerpt_count === 0} onClick={() => onSelect(question)}>
                {selectedId === question.id ? 'Selected' : 'Choose question'}
              </button>}
            </div>
          </div>
        ))}
      </div>
      {data && (data.total > PAGE_SIZE || data.offset > 0) && <div className={styles.pagination}>
        <button type="button" className="button ghost" disabled={busy || data.offset === 0} onClick={() => { onSelect?.(null); void load(filters, Math.max(0, data.offset - PAGE_SIZE)); }}>Previous</button>
        <span className="muted tiny">{data.total === 0 ? 0 : data.offset + 1}–{Math.min(data.total, data.offset + data.items.length)} of {data.total}</span>
        <button type="button" className="button ghost" disabled={busy || !data.has_more} onClick={() => { onSelect?.(null); void load(filters, data.offset + PAGE_SIZE); }}>Next</button>
      </div>}
    </section>
  );
}
