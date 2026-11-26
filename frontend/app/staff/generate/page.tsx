'use client';

import {useCallback, useEffect, useState, type FormEvent} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {clientRequest} from '@/lib/client';
import styles from './question-generation.module.css';

type Source = {id:string;title:string;unit:string;unit_id:string;programme:string;external_authorized:boolean};
type Topic = {id:string;title:string;unit_id:string};
type SourceList = {items:Source[];topics:Topic[];provider:string};
type Job = {id:string;document:string;document_title:string;topic:string;count:number;kind:string;difficulty:string;provider:string;state:string;failure_code:string;created_at:string};
type Candidate = {id:string;position:number;kind:string;prompt:string;options:string[];correct_index:number|null;explanation:string;rubric:Array<{criterion:string;marks:number}>;evidence_quote:string;validation_errors:string[];state:string;review_note:string;bank_revision_id:string|null};
type JobDetail = Job & {candidates:Candidate[]};
const ROOT='/api/nicat/question-generation/';
const get=<T,>(p:string)=>clientRequest<T>(`${ROOT}${p}`);
const post=<T,>(p:string,data:unknown)=>clientRequest<T>(`${ROOT}${p}`,{method:'POST',body:JSON.stringify(data)});
const errText=(e:unknown)=>e instanceof Error?e.message:'Request failed';

export default function QuestionGenerator(){
  const [sources,setSources]=useState<Source[]>([]);
  const [topics,setTopics]=useState<Topic[]>([]);
  const [provider,setProvider]=useState('mock');
  const [doc,setDoc]=useState('');
  const [topic,setTopic]=useState('');
  const [kind,setKind]=useState('mcq');
  const [difficulty,setDifficulty]=useState('mixed');
  const [count,setCount]=useState('3');
  const [jobs,setJobs]=useState<Job[]>([]);
  const [selected,setSelected]=useState<JobDetail|null>(null);
  const [editing,setEditing]=useState<Candidate|null>(null);
  const [optionsText,setOptionsText]=useState('');
  const [rubricText,setRubricText]=useState('[]');
  const [note,setNote]=useState('');
  const [rightsNote,setRightsNote]=useState('');
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [error,setError]=useState('');

  const reload=useCallback(async()=>{
    const [sourcesResponse,jobResponse]=await Promise.all([
      get<SourceList>('sources/'),get<{items:Job[]}>('jobs/')
    ]);
    setSources(sourcesResponse.items);
    setTopics(sourcesResponse.topics);
    setProvider(sourcesResponse.provider);
    setJobs(jobResponse.items);
  },[]);
  useEffect(()=>{void reload().catch(e=>setError(errText(e)));},[reload]);
  const chosen=sources.find(s=>s.id===doc);
  const availableTopics=topics.filter(t=>t.unit_id===chosen?.unit_id);
  const selectedTopic=availableTopics.some(t=>t.id===topic)?topic:'';

  async function run(op:()=>Promise<unknown>,success:string){
    setBusy(true);setError('');setMessage('');
    try{await op();await reload();setMessage(success);}
    catch(e){setError(errText(e));}
    finally{setBusy(false);}
  }
  async function createJob(e:FormEvent){
    e.preventDefault();
    await run(async()=>{
      const j=await post<Job>('jobs/',{document_id:doc,topic_id:selectedTopic,kind,
                                     difficulty,count:Number(count)});
      setSelected({...j,candidates:[]});
    },'Generation queued. Process it using the restricted Django worker, then refresh its status.');
  }
  async function openJob(id:string){
    setBusy(true);setError('');
    try{setSelected(await get<JobDetail>(`jobs/${encodeURIComponent(id)}/`));setEditing(null);}
    catch(e){setError(errText(e));}
    finally{setBusy(false);}
  }
  async function candidateAction(c:Candidate,action:'approve'|'reject'|'import'){
    await run(()=>post(`candidates/${encodeURIComponent(c.id)}/action/`,{action,note}),
              action==='import'?'Published question revision is now available in Question Bank.':`Candidate ${action === 'reject' ? 'rejected' : 'approved'}.`);
    if(selected)await openJob(selected.id);
  }
  function edit(c:Candidate){
    setEditing({...c});setOptionsText(c.options.join('\n'));
    setRubricText(JSON.stringify(c.rubric,null,2));
    setNote('');
  }
  async function saveCandidate(){
    if(!editing)return;
    try{
      const rubric=JSON.parse(rubricText) as unknown;
      if(!Array.isArray(rubric))throw new Error('Rubric must be a JSON array');
      await run(()=>post(`candidates/${encodeURIComponent(editing.id)}/edit/`,{
        prompt:editing.prompt,kind:editing.kind,
        options:editing.kind==='mcq'?optionsText.split('\n').map(x=>x.trim()).filter(Boolean):[],
        correct_index:editing.kind==='mcq'?editing.correct_index:null,
        explanation:editing.explanation,rubric:editing.kind==='mcq'?[]:rubric,
        evidence_quote:editing.evidence_quote,note,
      }),'Candidate changes saved for review.');
      if(selected)await openJob(selected.id);
    }catch(e){setError(errText(e));}
  }
  return <StaffFrame title="AI question generation" description="Draft source-grounded questions, validate evidence and publish only after academic review.">
    <div className={styles.stack}>
      {error&&<p className={styles.error} role="alert">{error}</p>}
      {message&&<p className={styles.success} role="status">{message}</p>}
      <section className="card" style={{padding:24}}>
        <div className={styles.heading}><div><h2>Generate question candidates</h2><p className="muted tiny">Only scanned, rights-cleared and academically approved uploads are eligible.</p></div><span className={styles.pill}>Provider: {provider}</span></div>
        <form onSubmit={e=>{void createJob(e);}} className={styles.form}>
          <label>Approved academic document
            <select className="field" value={doc} required onChange={e=>{setDoc(e.target.value);setTopic('');}}>
              <option value="">Choose a verified document</option>
              {sources.map(s=><option value={s.id} key={s.id}>{s.title} · {s.programme} · {s.unit}</option>)}
            </select>
          </label>
          <label>Topic
            <select className="field" required value={selectedTopic} onChange={e=>setTopic(e.target.value)}>
              <option value="">Choose a topic in the document&apos;s unit</option>
              {availableTopics.map(t=><option value={t.id} key={t.id}>{t.title}</option>)}
            </select>
          </label>
          <div className={styles.gridThree}>
            <label>Question type<select className="field" value={kind} onChange={e=>setKind(e.target.value)}><option value="mcq">MCQ</option><option value="short">Short answer</option><option value="essay">Essay</option><option value="mixed">Mixed</option></select></label>
            <label>Difficulty<select className="field" value={difficulty} onChange={e=>setDifficulty(e.target.value)}><option value="easy">Beginner</option><option value="medium">Intermediate</option><option value="hard">Advanced</option><option value="mixed">Mixed</option></select></label>
            <label>Questions per job<select className="field" value={count} onChange={e=>setCount(e.target.value)}>{[1,2,3,4,5].map(v=><option key={v} value={v}>{v}</option>)}</select></label>
          </div>
          {chosen&&provider!=='mock'&&<p className="muted tiny">External processing authorization: <strong>{chosen.external_authorized?'Recorded':'Missing'}</strong>. Staff rights clearance for a particular AI vendor is required separately.</p>}
          <div className={styles.actions}><button className="button" disabled={busy||!doc||!selectedTopic}>Queue generation job</button></div>
          <p className="muted tiny">Jobs run outside the web request via <code>nicat_process_question_jobs</code>. Nothing here automatically becomes an exam question.</p>
        </form>
      </section>
      {chosen&&provider!=='mock'&&<section className="card" style={{padding:24}}><h2>External AI data-rights review</h2><p className="muted tiny">A separate authorized staff member must record approval for this specific document before it is submitted to a remote model. This requires a vendor/data-protection assessment and appropriate rights.</p>
        <label>Rights assessment rationale<textarea className="field" rows={3} value={rightsNote} onChange={e=>setRightsNote(e.target.value)}/></label>
        <div className={styles.actions}><button type="button" className="button ghost" disabled={busy||rightsNote.length<40} onClick={()=>void run(()=>post('external-authorizations/',{document_id:doc,rationale:rightsNote,revoke:false}),'External-processing authorization recorded.')}>Authorize for configured provider</button><button type="button" className="button ghost" disabled={busy||rightsNote.length<40} onClick={()=>void run(()=>post('external-authorizations/',{document_id:doc,rationale:rightsNote,revoke:true}),'External-processing authorization revoked.')}>Revoke</button></div>
      </section>}
      <section className="card" style={{padding:24}}><div className={styles.heading}><h2>Generation history</h2><button type="button" className="button ghost" onClick={()=>void reload()} disabled={busy}>Refresh jobs</button></div>
        {jobs.length===0?<p className="muted">No generation jobs yet.</p>:<div className={styles.jobList}>{jobs.map(j=><button className={styles.jobButton} key={j.id} type="button" onClick={()=>void openJob(j.id)}><strong>{j.document_title}</strong><span>{j.topic} · {j.kind} · {j.state} {j.failure_code&&`· ${j.failure_code}`}</span></button>)}</div>}
      </section>
      {selected&&<section className="card" style={{padding:24}}>
        <div className={styles.heading}><h2>Review job candidates</h2><button type="button" className="button ghost" onClick={()=>void openJob(selected.id)} disabled={busy}>Refresh candidates</button></div>
        <p className="muted tiny">{selected.document_title} · {selected.topic} · {selected.provider} · {selected.state}</p>
        {selected.candidates.length===0?<p className="muted">No candidates yet. Run the backend worker and refresh.</p>:selected.candidates.map(c=><article className={styles.candidate} key={c.id}>
          <div className={styles.heading}><h3>{c.position}. {c.kind.toUpperCase()} — {c.state}</h3>{c.validation_errors.length>0&&<span className={styles.pill}>Validation flags: {c.validation_errors.join(', ')}</span>}</div>
          <p style={{whiteSpace:'pre-wrap'}}>{c.prompt}</p>
          {c.options.length>0&&<ol>{c.options.map((v,i)=><li key={i}>{v} {c.correct_index===i?'(proposed correct)':''}</li>)}</ol>}
          <p><strong>Explanation:</strong> {c.explanation}</p>
          {c.rubric.length>0&&<p><strong>Rubric:</strong> {c.rubric.map(r=>`${r.criterion} (${r.marks})`).join(' · ')}</p>}
          <blockquote>{c.evidence_quote}</blockquote>
          <p className="muted tiny">{c.bank_revision_id?`Imported revision: ${c.bank_revision_id}`:'Private candidate. Source rights and independent reviewer checks apply.'}</p>
          <div className={styles.actions}>
            {c.state==='draft'&&<button className="button ghost" type="button" onClick={()=>edit(c)}>Edit candidate</button>}
            {c.state==='draft'&&<button className="button ghost" type="button" disabled={busy||note.trim().length<25} onClick={()=>void candidateAction(c,'reject')}>Reject</button>}
            {c.state==='draft'&&<button className="button" type="button" disabled={busy||note.trim().length<25||c.validation_errors.length>0} onClick={()=>void candidateAction(c,'approve')}>Approve</button>}
            {c.state==='approved'&&<button className="button" type="button" disabled={busy} onClick={()=>void candidateAction(c,'import')}>Import MCQ to Question Bank</button>}
          </div>
        </article>)}
        <label>Academic review rationale (25+ characters)<textarea className="field" rows={3} value={note} onChange={e=>setNote(e.target.value)} placeholder="Document why the candidate is correct and syllabus aligned..."/></label>
      </section>}
      {editing&&<section className="card" style={{padding:24}}><h2>Edit draft candidate</h2><div className={styles.form}>
        <label>Question prompt<textarea rows={4} className="field" value={editing.prompt} onChange={e=>setEditing({...editing,prompt:e.target.value})}/></label>
        <label>Explanation<textarea rows={4} className="field" value={editing.explanation} onChange={e=>setEditing({...editing,explanation:e.target.value})}/></label>
        <label>Evidence quote copied from source<textarea rows={3} className="field" value={editing.evidence_quote} onChange={e=>setEditing({...editing,evidence_quote:e.target.value})}/></label>
        {editing.kind==='mcq'?<><label>Options (one per line)<textarea rows={5} className="field" value={optionsText} onChange={e=>setOptionsText(e.target.value)}/></label><label>Proposed correct option (0–3)<input className="field" type="number" min={0} max={3} value={editing.correct_index??0} onChange={e=>setEditing({...editing,correct_index:Number(e.target.value)})}/></label></>:
        <label>Rubric JSON (list of criterion and marks)<textarea rows={6} className="field" value={rubricText} onChange={e=>setRubricText(e.target.value)}/></label>}
        <div className={styles.actions}><button type="button" className="button" disabled={busy||note.trim().length<25} onClick={()=>void saveCandidate()}>Save revision for review</button><button type="button" className="button ghost" onClick={()=>setEditing(null)}>Cancel</button></div>
        <p className="muted tiny">Mock candidates cannot be edited into real questions. Written rubric import is blocked until mapped to NiCat&apos;s existing grading model.</p>
      </div></section>}
    </div>
  </StaffFrame>;
}
