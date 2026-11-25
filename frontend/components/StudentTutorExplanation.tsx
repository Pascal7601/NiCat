'use client';
import {useState} from 'react';
import {ClientError, clientRequest} from '@/lib/client';

export interface ApprovedTutorResult {
  revision_version: number;
  question_topic: string;
  explanation: string;
  common_mistake: string;
  practice_tip: string;
  ai_assisted: true;
  reviewer_approved: true;
  official_university_material: false;
  sources: Array<{excerpt_id: string; title: string; page: string; section: string; evidence: string}>;
}

/** Render only on the finalized results page. Backend always enforces release authorization. */
export default function StudentTutorExplanation({attemptId, questionId, released}: {
  attemptId: string; questionId: string; released: boolean;
}) {
  const [data, setData] = useState<ApprovedTutorResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [opened, setOpened] = useState(false);
  if (!released) return null;
  async function explain() {
    if (opened) {setOpened(false); return;}
    if (data) {setOpened(true); return;}
    setBusy(true);setMessage('');
    try {
      const result = await clientRequest<ApprovedTutorResult>(
        `/api/nicat/study-tutor/attempts/${encodeURIComponent(attemptId)}/questions/${encodeURIComponent(questionId)}/explanation/`
      );
      setData(result);setOpened(true);
    } catch (err) {
      if (err instanceof ClientError && err.status === 404) {
        setMessage('An approved explanation is not available for this question yet.');
      } else if (err instanceof ClientError && err.status === 409) {
        setMessage('This explanation becomes available after all marking is finalized.');
      } else {
        setMessage('Could not load the explanation. Please try again.');
      }
    } finally {setBusy(false);}
  }
  return <div style={{marginTop:12}}>
    <button type="button" className="button ghost" onClick={explain} disabled={busy} aria-expanded={opened}>
      {busy ? 'Loading explanation…' : opened ? 'Hide AI tutor' : 'Explain this answer'}
    </button>
    {message && <p className="muted tiny" role="status">{message}</p>}
    {opened && data && <section className="card" aria-label="Reviewer-approved AI tutor explanation" style={{marginTop:10}}>
      <p className="muted tiny">AI-assisted · Approved by an academic reviewer · Independent revision guidance, not official MMU material · v{data.revision_version}</p>
      <h3>{data.question_topic}</h3>
      <p style={{whiteSpace:'pre-wrap'}}>{data.explanation}</p>
      <h4>Common mistake</h4><p style={{whiteSpace:'pre-wrap'}}>{data.common_mistake}</p>
      <h4>Practice tip</h4><p style={{whiteSpace:'pre-wrap'}}>{data.practice_tip}</p>
      <h4>Approved academic references</h4>
      <ul>{data.sources.map(s=><li key={s.excerpt_id}>
        <strong>{s.title}</strong>{s.page ? ` · page ${s.page}` : ''}{s.section ? ` · ${s.section}` : ''}
        <p className="muted tiny">{s.evidence}</p>
      </li>)}</ul>
    </section>}
  </div>;
}
