'use client';

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import QuestionBrowser, { type PublishedQuestion } from '@/components/staff/QuestionBrowser';
import { errorText, idPath, staffGet, staffPost, type TutorDraft } from '@/lib/staff-workspace';

export default function StaffTutor() {
  const [items, setItems] = useState<TutorDraft[]>([]);
  const [selected, setSelected] = useState<TutorDraft | null>(null);
  const [question, setQuestion] = useState<PublishedQuestion | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const refresh = useCallback(async () => {
    const result = await staffGet<{ items: TutorDraft[] }>('/tutor/');
    setItems(result.items);
    return result.items;
  }, []);

  useEffect(() => { void refresh().catch(err => setError(errorText(err))); }, [refresh]);

  async function run(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await fn();
      await refresh();
      setNotice(message);
      setSelected(null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question || busy) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      // The user chooses a prompt; only this internal API call uses its UUID.
      const response = await staffPost<{ id: string }>('/tutor/generate/', {
        revision_id: question.id,
      });
      const refreshed = await refresh();
      const newDraft = refreshed.find(item => item.id === response.id);
      setSelected(newDraft ?? null);
      setNotice(newDraft
        ? 'Draft is ready for your academic review. Check its sources and edit the text before publishing.'
        : 'Draft generated. Check the queue below or refresh to find it.');
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  function setField(key: 'explanation' | 'common_mistake' | 'practice_tip', value: string) {
    setSelected(current => current ? { ...current, [key]: value } : null);
  }

  return (
    <StaffFrame title="Tutor explanation review" description="Select a published question by unit or topic, generate a source-grounded draft, and approve the explanation after academic review.">
      {error && <p role="alert" className="error">{error}</p>}
      {notice && <p role="status" className="card" style={{ padding: 14 }}>{notice}</p>}

      <QuestionBrowser selectedId={question?.id} onSelect={setQuestion} />

      <section className="card" style={{ marginTop: 18, padding: 20 }}>
        <h2>Create Tutor draft</h2>
        <p className="muted tiny">Only a published question with approved, rights-cleared topic sources is eligible. The backend checks source relevance again before generating.</p>
        {!question ? (
          <p className="muted">Choose a question from the browser above to continue.</p>
        ) : (
          <form onSubmit={e => { void generate(e); }} style={{ display: 'grid', gap: 12 }}>
            <div style={{ background: 'var(--soft)', borderRadius: 10, padding: 14 }}>
              <p className="muted tiny">{question.unit} · {question.topic} · {question.kind.replaceAll('_', ' ')} · v{question.version}</p>
              <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{question.prompt}</p>
              <p className="muted tiny">{question.approved_excerpt_count} approved topic excerpt(s); generation may still be blocked if none matches the question.</p>
            </div>
            <button className="button" disabled={busy || question.approved_excerpt_count === 0} type="submit">
              {busy ? 'Generating draft…' : 'Generate grounded draft'}
            </button>
          </form>
        )}
      </section>

      <section className="card" style={{ marginTop: 18, padding: 20 }}>
        <h2>Drafts and published explanations</h2>
        {!items.length ? (
          <p className="muted">No explanation records yet. Search above for a published question to start a draft.</p>
        ) : (
          <div style={{ display: 'grid', gap: 9 }}>
            {items.map(item => <button key={item.id} type="button" className="button ghost" style={{ whiteSpace: 'normal', textAlign: 'left' }} onClick={() => setSelected({ ...item })}>
              {item.topic} · v{item.version} · {item.state} · {item.question.slice(0, 110)}
            </button>)}
          </div>
        )}
      </section>

      {selected && <section className="card" style={{ marginTop: 18, padding: 20 }} aria-label="Review Tutor explanation">
        <h2>Review explanation</h2>
        <p><strong>{selected.topic}</strong> · v{selected.version} · {selected.state}</p>
        <p className="muted tiny">{selected.question}</p>
        {(['explanation', 'common_mistake', 'practice_tip'] as const).map(key => (
          <label key={key} style={{ display: 'grid', gap: 5, margin: '13px 0' }}>
            {key.replaceAll('_', ' ')}
            <textarea className="field" rows={key === 'explanation' ? 8 : 4} readOnly={selected.state !== 'draft'} value={selected[key]} onChange={e => setField(key, e.target.value)} />
          </label>
        ))}
        <h3>Approved academic evidence</h3>
        <ul>{selected.citations.map(c => <li key={c.id}>
          <strong>{c.document}</strong> · {c.rights_status} · {c.state}
          <p className="muted tiny" style={{ whiteSpace: 'pre-wrap' }}>{c.text}</p>
        </li>)}</ul>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          {selected.state === 'draft' && <>
            <button className="button ghost" disabled={busy} onClick={() => void run(
              () => staffPost(`/tutor/${idPath(selected.id)}/`, {
                explanation: selected.explanation,
                common_mistake: selected.common_mistake,
                practice_tip: selected.practice_tip,
              }), 'Draft saved. Publication still requires a separate review action.')}>
              Save draft edits
            </button>
            <button className="button" disabled={busy} onClick={() => void run(
              () => staffPost(`/tutor/${idPath(selected.id)}/action/`, { action: 'publish' }),
              'Explanation published after backend academic checks.')}>
              Publish reviewed explanation
            </button>
          </>}
          {selected.state === 'published' && <button className="button ghost" disabled={busy} onClick={() => void run(
            () => staffPost(`/tutor/${idPath(selected.id)}/action/`, { action: 'withdraw' }),
            'Published explanation withdrawn.')}>
            Withdraw published explanation
          </button>}
        </div>
        <p className="muted tiny">Save edits before publishing. The backend rechecks evidence, rights, source fingerprints and reviewer authorization.</p>
      </section>}
    </StaffFrame>
  );
}
