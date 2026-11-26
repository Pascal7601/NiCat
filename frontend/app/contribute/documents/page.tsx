'use client';

import Link from 'next/link';
import { useEffect, useRef, useState, type FormEvent } from 'react';
import {
  AlertCircle,
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  CloudUpload,
  FileCheck2,
  FileText,
  FolderOpen,
  Info,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
  Trash2,
} from 'lucide-react';
import { Shell, Heading } from '@/components/Shell';
import { clientRequest, ClientError } from '@/lib/client';
import styles from './documents.module.css';

type Programme = { id: string; name: string; university: string };
type Unit = { id: string; title: string };
type DocumentItem = {
  id: string;
  title: string;
  programme_title: string;
  unit_title: string;
  suggested_unit_title: string;
  state: string;
  scan_state: string;
  possible_duplicate: boolean;
  created_at: string;
};

const MAX_BYTES = 8 * 1024 * 1024;
const labels: Record<string, string> = {
  pending_scan: 'Awaiting security scan',
  needs_mapping: 'Unit needs verification',
  pending_review: 'Awaiting academic review',
  rights_hold: 'Rights clarification required',
  approved_for_questions: 'Approved for question drafting',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
  processing_error: 'Processing needs staff attention',
};

function statusClass(state: string): string {
  if (state === 'approved_for_questions') return styles.stateApproved;
  if (state === 'rejected' || state === 'processing_error') return styles.stateError;
  if (state === 'rights_hold' || state === 'needs_mapping') return styles.stateWarning;
  if (state === 'withdrawn') return styles.stateNeutral;
  return styles.statePending;
}

function readableSize(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export default function DocumentContributePage() {
  const [programmes, setProgrammes] = useState<Programme[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [programme, setProgramme] = useState('');
  const [unit, setUnit] = useState('');
  const [suggestedUnit, setSuggestedUnit] = useState('');
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [rightsBasis, setRightsBasis] = useState('own_work');
  const [rightsEvidence, setRightsEvidence] = useState('');
  const [owner, setOwner] = useState('');
  const [kind, setKind] = useState('original_notes');
  const [year, setYear] = useState('');
  const [semester, setSemester] = useState('');
  const [code, setCode] = useState('');
  const [topics, setTopics] = useState('');
  const [description, setDescription] = useState('');
  const [generate, setGenerate] = useState(false);
  const [display, setDisplay] = useState(false);
  const [tutor, setTutor] = useState(false);
  const [items, setItems] = useState<DocumentItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function loadHistory() {
    const data = await clientRequest<{ items: DocumentItem[] }>('/api/nicat/document-intake/');
    setItems(data.items);
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      clientRequest<{ items: Programme[] }>('/api/nicat/document-intake/programmes/'),
      clientRequest<{ items: DocumentItem[] }>('/api/nicat/document-intake/'),
    ])
      .then(([programmesResult, history]) => {
        if (!cancelled) {
          setProgrammes(programmesResult.items);
          setItems(history.items);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof ClientError && err.status === 401
              ? 'Sign in to upload documents.'
              : 'Could not load the contribution catalogue. Please try again.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setUnits([]);
    setUnit('');
    if (programme) {
      clientRequest<{ items: Unit[] }>(
        `/api/nicat/document-intake/programmes/${encodeURIComponent(programme)}/units/`,
      )
        .then(data => { if (!cancelled) setUnits(data.items); })
        .catch(() => { if (!cancelled) setError('Could not load units for this programme.'); });
    }
    return () => { cancelled = true; };
  }, [programme]);

  function chooseFile(next: File | null) {
    setError('');
    if (next && next.size > MAX_BYTES) {
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setError('The file is larger than 8 MB. Please select a smaller PDF or TXT document.');
      return;
    }
    if (next && !/\.(pdf|txt)$/i.test(next.name)) {
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setError('Only PDF and TXT files are accepted.');
      return;
    }
    setFile(next);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      if (!file || !programme || !generate) {
        throw new Error('Select a programme and document, then authorize question drafting.');
      }
      const body = new FormData();
      const fields: Record<string, string> = {
        programme_id: programme,
        unit_id: unit,
        suggested_unit_title: unit ? '' : suggestedUnit,
        suggested_unit_code: code,
        year_number: year,
        semester_number: semester,
        title,
        description,
        suggested_topics: topics,
        document_type: kind,
        rights_basis: rightsBasis,
        rights_evidence: rightsEvidence,
        author_or_owner: owner,
        permit_question_generation: String(generate),
        permit_resource_display: String(display),
        permit_tutor_use: String(tutor),
      };
      for (const [key, value] of Object.entries(fields)) {
        if (value) body.append(key, value);
      }
      body.append('file', file, file.name);
      const response = await fetch('/api/nicat/document-upload', {
        method: 'POST', body, credentials: 'same-origin', cache: 'no-store',
      });
      const payload: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        const obj = payload && typeof payload === 'object'
          ? payload as Record<string, unknown> : {};
        throw new Error(
          typeof obj.message === 'string'
            ? obj.message
            : typeof obj.detail === 'string'
              ? obj.detail
              : `Upload failed (${response.status})`,
        );
      }
      setNotice('Document received privately. It must pass security scanning, unit verification, and independent rights and academic review before being used for question drafting.');
      setFile(null);
      setTitle('');
      setSuggestedUnit('');
      setDescription('');
      setTopics('');
      setGenerate(false);
      setDisplay(false);
      setTutor(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  async function withdraw(id: string) {
    if (busy) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await clientRequest(`/api/nicat/document-intake/${encodeURIComponent(id)}/withdraw/`, {
        method: 'POST',
      });
      await loadHistory();
      setNotice('Document withdrawn.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not withdraw document.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell section="dashboard">
      <div className={styles.page}>
        <Heading
          eyebrow="NICAT · ACADEMIC CONTRIBUTIONS"
          title="Contribute documents"
          subtitle="Share authorized study material to help us build better, source-grounded practice questions."
        />

        <div className={styles.hero}>
          <div className={styles.heroCopy}>
            <span className={styles.heroEyebrow}><Sparkles size={15} /> HELP BUILD BETTER CATS</span>
            <h2>Your notes can become tomorrow&apos;s practice questions.</h2>
            <p>Upload original or properly licensed academic material. NiCat keeps the file private while staff verify its safety, rights, and relevance.</p>
            <div className={styles.heroPills}>
              <span><LockKeyhole size={14} /> Private by default</span>
              <span><ShieldCheck size={14} /> Human reviewed</span>
            </div>
          </div>
          <div className={styles.heroVisual} aria-hidden="true">
            <div className={styles.heroFile}><FileText size={29} /><span>Study material</span></div>
            <div className={styles.heroFlow}><ArrowRight size={20} /></div>
            <div className={styles.heroFile}><BookOpenCheck size={29} /><span>Practice questions</span></div>
          </div>
        </div>

        {error && <div className={styles.errorMessage} role="alert"><AlertCircle size={19} /><span>{error}</span></div>}
        {notice && <div className={styles.successMessage} role="status"><CheckCircle2 size={19} /><span>{notice}</span></div>}

        <div className={styles.workspace}>
          <form className={styles.formColumn} onSubmit={event => void submit(event)}>
            <section className={styles.sectionCard}>
              <header className={styles.sectionHeader}>
                <div className={styles.sectionNumber}>01</div>
                <div><h2>Academic details</h2><p>Help us match your document to the right programme and unit.</p></div>
              </header>
              <div className={styles.fields}>
                <div className={styles.field}>
                  <label htmlFor="nicat-programme">Programme <span className={styles.required}>*</span></label>
                  <select id="nicat-programme" required value={programme} onChange={e => setProgramme(e.target.value)} disabled={loading}>
                    <option value="">{loading ? 'Loading programmes…' : 'Choose a programme'}</option>
                    {programmes.map(p => <option key={p.id} value={p.id}>{p.university} · {p.name}</option>)}
                  </select>
                </div>
                <div className={styles.field}>
                  <label htmlFor="nicat-unit">Unit</label>
                  <select id="nicat-unit" value={unit} onChange={e => setUnit(e.target.value)} disabled={!programme}>
                    <option value="">{!programme ? 'Select a programme first' : 'Unit not listed — request verification'}</option>
                    {units.map(u => <option key={u.id} value={u.id}>{u.title}</option>)}
                  </select>
                </div>
                {programme && !unit && (
                  <div className={`${styles.field} ${styles.fullWidth}`}>
                    <label htmlFor="nicat-new-unit">Proposed unit title <span className={styles.required}>*</span></label>
                    <input id="nicat-new-unit" value={suggestedUnit} onChange={e => setSuggestedUnit(e.target.value)} required minLength={4} maxLength={200} placeholder="e.g. Computer Graphics" />
                    <p className={styles.fieldHint}>Our team will verify and map this unit before the document can be approved.</p>
                  </div>
                )}
                <div className={styles.threeColumns}>
                  <div className={styles.field}>
                    <label htmlFor="nicat-unit-code">Unit code <span className={styles.optional}>Optional</span></label>
                    <input id="nicat-unit-code" value={code} maxLength={50} onChange={e => setCode(e.target.value)} placeholder="e.g. BIT 2413" />
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="nicat-year">Year <span className={styles.optional}>Optional</span></label>
                    <select id="nicat-year" value={year} onChange={e => setYear(e.target.value)}>
                      <option value="">Not sure</option>
                      {[1, 2, 3, 4, 5, 6, 7, 8].map(y => <option key={y} value={y}>Year {y}</option>)}
                    </select>
                  </div>
                  <div className={styles.field}>
                    <label htmlFor="nicat-semester">Semester <span className={styles.optional}>Optional</span></label>
                    <select id="nicat-semester" value={semester} onChange={e => setSemester(e.target.value)}>
                      <option value="">Not sure</option>
                      {[1, 2, 3, 4].map(s => <option key={s} value={s}>Semester {s}</option>)}
                    </select>
                  </div>
                </div>
              </div>
            </section>

            <section className={styles.sectionCard}>
              <header className={styles.sectionHeader}>
                <div className={styles.sectionNumber}>02</div>
                <div><h2>About your document</h2><p>Add a clear title and choose the material you are contributing.</p></div>
              </header>
              <div className={styles.fields}>
                <div className={styles.field}>
                  <label htmlFor="nicat-document-title">Document title <span className={styles.required}>*</span></label>
                  <input id="nicat-document-title" required minLength={5} maxLength={180} value={title} onChange={e => setTitle(e.target.value)} placeholder="Computer Graphics — 2D Transformations" />
                </div>
                <div className={styles.field}>
                  <label htmlFor="nicat-kind">Document type <span className={styles.required}>*</span></label>
                  <select id="nicat-kind" value={kind} onChange={e => setKind(e.target.value)}>
                    <option value="original_notes">My own revision notes</option>
                    <option value="licensed_notes">Licensed / authorized notes</option>
                    <option value="licensed_paper">Past paper with republication permission</option>
                    <option value="other_licensed">Other licensed material</option>
                  </select>
                </div>
                <div className={styles.field}>
                  <label htmlFor="nicat-topics">Topics covered <span className={styles.optional}>Optional</span></label>
                  <input id="nicat-topics" value={topics} maxLength={350} onChange={e => setTopics(e.target.value)} placeholder="Translation, scaling, rotation" />
                  <p className={styles.fieldHint}>Suggestions only — reviewers will confirm the topic mapping.</p>
                </div>
                <div className={styles.field}>
                  <label htmlFor="nicat-description">Short description <span className={styles.optional}>Optional</span></label>
                  <textarea id="nicat-description" value={description} onChange={e => setDescription(e.target.value)} maxLength={1000} rows={3} placeholder="What concepts does this document explain?" />
                </div>
                <div className={styles.field}>
                  <label htmlFor="nicat-document-file">Upload your file <span className={styles.required}>*</span></label>
                  <div className={styles.uploadZone}>
                    <div className={styles.uploadIcon}><CloudUpload size={25} /></div>
                    <div className={styles.uploadDetails}>
                      <strong>{file ? file.name : 'Choose a PDF or TXT document'}</strong>
                      <p>{file ? `${readableSize(file.size)} selected` : 'Maximum file size 8 MB · Original is stored privately'}</p>
                    </div>
                    <input
                      id="nicat-document-file"
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.txt,application/pdf,text/plain"
                      required
                      onChange={e => chooseFile(e.target.files?.[0] ?? null)}
                    />
                  </div>
                  <p className={styles.fieldHint}>Files are checked before processing. Do not upload documents containing student IDs, private grades, or unnecessary personal data.</p>
                </div>
              </div>
            </section>

            <section className={styles.sectionCard}>
              <header className={styles.sectionHeader}>
                <div className={styles.sectionNumber}>03</div>
                <div><h2>Ownership &amp; permissions</h2><p>Tell us who owns the document and exactly how NiCat may use it.</p></div>
              </header>
              <div className={styles.fields}>
                <div className={styles.field}>
                  <label htmlFor="nicat-owner">Author or rights holder <span className={styles.required}>*</span></label>
                  <input id="nicat-owner" value={owner} onChange={e => setOwner(e.target.value)} minLength={2} maxLength={180} required placeholder="Your name or the document's rights holder" />
                </div>
                <div className={styles.field}>
                  <label htmlFor="nicat-rights">Basis for permission <span className={styles.required}>*</span></label>
                  <select id="nicat-rights" value={rightsBasis} onChange={e => setRightsBasis(e.target.value)}>
                    <option value="own_work">I wrote the notes myself</option>
                    <option value="permission">The rights holder granted permission</option>
                    <option value="open_license">An open license permits this use</option>
                  </select>
                </div>
                {rightsBasis !== 'own_work' && (
                  <div className={styles.field}>
                    <label htmlFor="nicat-evidence">Permission evidence or license details <span className={styles.required}>*</span></label>
                    <textarea id="nicat-evidence" rows={3} minLength={25} maxLength={1000} required value={rightsEvidence} onChange={e => setRightsEvidence(e.target.value)} placeholder="Describe the permission or license, and where reviewers can verify it." />
                  </div>
                )}
              </div>

              <div className={styles.permissionList}>
                <label className={`${styles.permissionItem} ${styles.permissionRequired}`} htmlFor="nicat-permit-questions">
                  <input id="nicat-permit-questions" type="checkbox" checked={generate} onChange={e => setGenerate(e.target.checked)} required />
                  <span><strong>Allow question generation <span className={styles.required}>*</span></strong><small>After human review, NiCat may use the document to draft practice questions. Uploading does not publish the file.</small></span>
                </label>
                <label className={styles.permissionItem} htmlFor="nicat-permit-display">
                  <input id="nicat-permit-display" type="checkbox" checked={display} onChange={e => setDisplay(e.target.checked)} />
                  <span><strong>Allow resource library display <span className={styles.optional}>Optional</span></strong><small>Separately permit future publication of the verified document for student viewing.</small></span>
                </label>
                <label className={styles.permissionItem} htmlFor="nicat-permit-tutor">
                  <input id="nicat-permit-tutor" type="checkbox" checked={tutor} onChange={e => setTutor(e.target.checked)} />
                  <span><strong>Allow AI Tutor citations <span className={styles.optional}>Optional</span></strong><small>Separately permit approved excerpts to support Tutor explanations.</small></span>
                </label>
              </div>
              <div className={styles.submitArea}>
                <div className={styles.submitReassurance}><LockKeyhole size={17} /> Private intake · Reviewed before question drafting</div>
                <button type="submit" className={`button ${styles.submitButton}`} disabled={busy || !file || !programme || !generate}>
                  {busy ? 'Uploading document…' : 'Submit for verification'}
                  {!busy && <ArrowRight size={17} />}
                </button>
              </div>
            </section>
          </form>

          <aside className={styles.helpColumn} aria-label="How document verification works">
            <div className={styles.helpCard}>
              <div className={styles.helpTitle}><ClipboardCheck size={19} /><h2>What happens next?</h2></div>
              <ol className={styles.timeline}>
                <li><span>1</span><div><strong>Private upload</strong><p>We receive your original file and keep it out of the public library.</p></div></li>
                <li><span>2</span><div><strong>Safety checks</strong><p>The file is screened and its text is extracted for review.</p></div></li>
                <li><span>3</span><div><strong>Academic verification</strong><p>Separate rights and academic reviewers assess your material.</p></div></li>
                <li><span>4</span><div><strong>Question drafting eligibility</strong><p>Approved documents may be used for question-generation drafts in a future sprint.</p></div></li>
              </ol>
            </div>
            <div className={styles.privacyCard}>
              <div className={styles.helpTitle}><ShieldCheck size={19} /><h2>Your document stays protected</h2></div>
              <p>Permission to generate questions does <strong>not</strong> make your PDF publicly downloadable. Publication and Tutor use are separate decisions.</p>
              <div className={styles.privacyRule}><Info size={17} /><span>Being the uploader does not automatically establish copyright ownership.</span></div>
            </div>
          </aside>
        </div>

        <section className={styles.historySection} aria-labelledby="nicat-history-heading">
          <header className={styles.historyHeader}>
            <div className={styles.historyTitle}><div className={styles.historyIcon}><FolderOpen size={22} /></div><div><h2 id="nicat-history-heading">My document submissions</h2><p>Track the review status of your uploaded materials.</p></div></div>
            <span className={styles.historyCount}>{items.length} {items.length === 1 ? 'document' : 'documents'}</span>
          </header>
          {items.length === 0 ? (
            <div className={styles.emptyState}>
              <FileCheck2 size={30} />
              <h3>No documents yet</h3>
              <p>Once you submit a document, its verification progress will appear here.</p>
            </div>
          ) : (
            <ul className={styles.historyList}>
              {items.map(d => (
                <li key={d.id} className={styles.historyItem}>
                  <div className={styles.fileBadge}><FileText size={20} /></div>
                  <div className={styles.fileContent}>
                    <strong>{d.title}</strong>
                    <p>{d.programme_title} <span aria-hidden="true">·</span> {d.unit_title || d.suggested_unit_title || 'Unit pending mapping'}</p>
                    <div className={styles.statusRow}>
                      <span className={`${styles.statusBadge} ${statusClass(d.state)}`}>{labels[d.state] || d.state}</span>
                      <span className={styles.scanText}>Security: {d.scan_state.replaceAll('_', ' ')}</span>
                      {d.possible_duplicate && <span className={styles.duplicateText}><AlertCircle size={13} /> Possible duplicate</span>}
                    </div>
                  </div>
                  {d.state !== 'withdrawn' && (
                    <button className={styles.withdrawButton} type="button" disabled={busy} onClick={() => void withdraw(d.id)} aria-label={`Withdraw ${d.title}`}>
                      <Trash2 size={15} /> Withdraw
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
        <div className={styles.footerLinks}>
          <Link href="/contribute"><FileText size={15} /> Submit text notes</Link>
          <Link href="/dashboard">Back to dashboard <ArrowRight size={15} /></Link>
        </div>
      </div>
    </Shell>
  );
}
