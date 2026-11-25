'use client';
import Link from 'next/link';
import {useEffect,useState,type FormEvent} from 'react';
import {Shell,Heading} from '@/components/Shell';
import {clientRequest,ClientError} from '@/lib/client';

type Programme = {id:string,name:string,university:string};
type Unit = {id:string,title:string};
type DocumentItem = {id:string,title:string,programme_title:string,unit_title:string,suggested_unit_title:string,state:string,scan_state:string,possible_duplicate:boolean,created_at:string};
const labels:Record<string,string> = {
  pending_scan:'Awaiting security scan',needs_mapping:'Unit needs verification',
  pending_review:'Awaiting academic review',rights_hold:'Rights clarification required',
  approved_for_questions:'Approved for future question drafting',rejected:'Rejected',
  withdrawn:'Withdrawn',processing_error:'Processing requires staff attention',
};
export default function DocumentContributePage(){
  const [programmes,setProgrammes]=useState<Programme[]>([]);
  const [units,setUnits]=useState<Unit[]>([]);
  const [programme,setProgramme]=useState('');
  const [unit,setUnit]=useState('');
  const [suggestedUnit,setSuggestedUnit]=useState('');
  const [title,setTitle]=useState('');
  const [file,setFile]=useState<File|null>(null);
  const [rightsBasis,setRightsBasis]=useState('own_work');
  const [rightsEvidence,setRightsEvidence]=useState('');
  const [owner,setOwner]=useState('');
  const [kind,setKind]=useState('original_notes');
  const [year,setYear]=useState('');
  const [semester,setSemester]=useState('');
  const [code,setCode]=useState('');
  const [topics,setTopics]=useState('');
  const [description,setDescription]=useState('');
  const [generate,setGenerate]=useState(false);
  const [display,setDisplay]=useState(false);
  const [tutor,setTutor]=useState(false);
  const [items,setItems]=useState<DocumentItem[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');

  async function loadHistory(){
    const data=await clientRequest<{items:DocumentItem[]}>('/api/nicat/document-intake/');
    setItems(data.items);
  }
  useEffect(()=>{
    let cancelled=false;
    Promise.all([
      clientRequest<{items:Programme[]}>('/api/nicat/document-intake/programmes/'),
      clientRequest<{items:DocumentItem[]}>('/api/nicat/document-intake/'),
    ]).then(([p,h])=>{if(!cancelled){setProgrammes(p.items);setItems(h.items);}})
      .catch(e=>{if(!cancelled)setError(e instanceof ClientError && e.status===401?'Sign in to upload documents.':'Could not load the contribution catalogue.');});
    return ()=>{cancelled=true;};
  },[]);
  useEffect(()=>{
    let cancelled=false;
    setUnits([]);setUnit('');
    if(programme){clientRequest<{items:Unit[]}>(`/api/nicat/document-intake/programmes/${encodeURIComponent(programme)}/units/`)
      .then(data=>{if(!cancelled)setUnits(data.items);})
      .catch(()=>{if(!cancelled)setError('Could not load units for this programme.');});}
    return ()=>{cancelled=true;};
  },[programme]);

  async function submit(e:FormEvent<HTMLFormElement>){
    e.preventDefault();setBusy(true);setError('');setNotice('');
    try{
      if(!file||!programme||!generate)throw new Error('Select a programme and document, then authorize question drafting.');
      const body=new FormData();
      const fields:Record<string,string>={
        programme_id:programme,unit_id:unit,suggested_unit_title:unit?'':suggestedUnit,
        suggested_unit_code:code,year_number:year,semester_number:semester,
        title,description,suggested_topics:topics,document_type:kind,
        rights_basis:rightsBasis,rights_evidence:rightsEvidence,author_or_owner:owner,
        permit_question_generation:String(generate),permit_resource_display:String(display),permit_tutor_use:String(tutor),
      };
      for(const [key,value] of Object.entries(fields))if(value)body.append(key,value);
      body.append('file',file,file.name);
      const response=await fetch('/api/nicat/document-upload',{method:'POST',body,credentials:'same-origin',cache:'no-store'});
      const payload:unknown=await response.json().catch(()=>({}));
      if(!response.ok){const obj=payload && typeof payload==='object'?payload as Record<string,unknown>:{};
        throw new Error(typeof obj.message==='string'?obj.message:typeof obj.detail==='string'?obj.detail:`Upload failed (${response.status})`);}
      setNotice('Received privately. Security scanning, catalogue verification and two independent reviews must finish before question drafting.');
      setFile(null);setTitle('');setSuggestedUnit('');setDescription('');setTopics('');setGenerate(false);setDisplay(false);setTutor(false);
      const fileInput=document.getElementById('nicat-document-file') as HTMLInputElement|null;
      if(fileInput)fileInput.value='';
      await loadHistory();
    }catch(err){setError(err instanceof Error?err.message:'Upload failed');}
    finally{setBusy(false);}
  }
  async function withdraw(id:string){
    if(busy)return;setBusy(true);setError('');
    try{await clientRequest(`/api/nicat/document-intake/${encodeURIComponent(id)}/withdraw/`,{method:'POST'});await loadHistory();setNotice('Document withdrawn.');}
    catch(err){setError(err instanceof Error?err.message:'Could not withdraw');}
    finally{setBusy(false);}
  }
  return <Shell section="dashboard"><Heading eyebrow="NICAT · ACADEMIC CONTRIBUTIONS" title="Contribute study material" subtitle="Help us build source-grounded practice questions for your programme."/>
    <p className="muted">Your original document stays private. Publication and AI Tutor use require separate permission and future academic approval. Do not submit materials you do not have rights to share.</p>
    <section className="card" style={{padding:24,marginTop:20}}>
      <h2>Upload for question generation</h2>
      <form onSubmit={e=>void submit(e)} style={{display:'grid',gap:14}}>
        <label htmlFor="nicat-programme">Programme</label>
        <select id="nicat-programme" required value={programme} onChange={e=>setProgramme(e.target.value)}>
          <option value="">Choose a programme</option>{programmes.map(p=><option key={p.id} value={p.id}>{p.university} · {p.name}</option>)}
        </select>
        <label htmlFor="nicat-unit">Unit (if listed)</label>
        <select id="nicat-unit" value={unit} onChange={e=>setUnit(e.target.value)}>
          <option value="">Unit not listed — request verification</option>{units.map(u=><option key={u.id} value={u.id}>{u.title}</option>)}
        </select>
        {!unit&&<><label htmlFor="nicat-new-unit">Proposed unit title</label><input id="nicat-new-unit" value={suggestedUnit} onChange={e=>setSuggestedUnit(e.target.value)} required minLength={4} maxLength={200} placeholder="e.g. Computer Graphics"/></>}
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(170px,1fr))',gap:12}}>
          <label>Unit code (optional)<input value={code} maxLength={50} onChange={e=>setCode(e.target.value)}/></label>
          <label>Year (optional)<select value={year} onChange={e=>setYear(e.target.value)}><option value="">Not sure</option>{[1,2,3,4,5,6,7,8].map(y=><option key={y} value={y}>{y}</option>)}</select></label>
          <label>Semester (optional)<select value={semester} onChange={e=>setSemester(e.target.value)}><option value="">Not sure</option>{[1,2,3,4].map(s=><option key={s} value={s}>{s}</option>)}</select></label>
        </div>
        <label htmlFor="nicat-document-title">Document title</label>
        <input id="nicat-document-title" required minLength={5} maxLength={180} value={title} onChange={e=>setTitle(e.target.value)} placeholder="Computer Graphics — 2D Transformations"/>
        <label htmlFor="nicat-kind">Document type</label>
        <select id="nicat-kind" value={kind} onChange={e=>setKind(e.target.value)}>
          <option value="original_notes">My own revision notes</option><option value="licensed_notes">Licensed/authorized notes</option>
          <option value="licensed_paper">Past paper with republication permission</option><option value="other_licensed">Other licensed material</option>
        </select>
        <label htmlFor="nicat-topics">Topics (suggestions; staff will verify)</label>
        <input id="nicat-topics" value={topics} maxLength={350} onChange={e=>setTopics(e.target.value)} placeholder="Translation, scaling, rotation"/>
        <label htmlFor="nicat-description">Short description (optional)</label>
        <textarea id="nicat-description" value={description} onChange={e=>setDescription(e.target.value)} maxLength={1000} rows={3}/>
        <label htmlFor="nicat-file">Original PDF or TXT (maximum 8 MB)</label>
        <input id="nicat-document-file" type="file" accept=".pdf,.txt,application/pdf,text/plain" required onChange={e=>setFile(e.target.files?.[0]??null)}/>
        <label htmlFor="nicat-owner">Who owns/authored this material?</label>
        <input id="nicat-owner" value={owner} onChange={e=>setOwner(e.target.value)} minLength={2} maxLength={180} required placeholder="Your name or the rights holder"/>
        <label htmlFor="nicat-rights">Basis for permission</label>
        <select id="nicat-rights" value={rightsBasis} onChange={e=>setRightsBasis(e.target.value)}>
          <option value="own_work">I wrote the notes myself</option>
          <option value="permission">The rights holder granted permission</option>
          <option value="open_license">A license permits this use</option>
        </select>
        {rightsBasis!=='own_work'&&<><label htmlFor="nicat-evidence">Permission evidence / license details</label><textarea id="nicat-evidence" rows={3} minLength={25} maxLength={1000} required value={rightsEvidence} onChange={e=>setRightsEvidence(e.target.value)}/></>}
        <label><input type="checkbox" checked={generate} onChange={e=>setGenerate(e.target.checked)} required/> I authorize NiCat to use this material to draft questions after human review. I understand that uploading does not publish the file.</label>
        <label><input type="checkbox" checked={display} onChange={e=>setDisplay(e.target.checked)}/> Separately, I permit a future verified resource library to display the document.</label>
        <label><input type="checkbox" checked={tutor} onChange={e=>setTutor(e.target.checked)}/> Separately, I permit approved source excerpts to support NiCat Tutor explanations.</label>
        <button type="submit" className="button" disabled={busy||!file||!programme||!generate}>{busy?'Uploading...':'Submit privately for verification'}</button>
      </form>
    </section>
    {error&&<p role="alert" style={{color:'var(--danger,crimson)'}}>{error}</p>}{notice&&<p role="status">{notice}</p>}
    <section className="card" style={{padding:24,marginTop:20}}><h2>My document submissions</h2>
      {!items.length?<p className="muted">No documents submitted yet.</p>:<ul>{items.map(d=><li key={d.id} style={{marginBottom:14}}>
        <strong>{d.title}</strong> — {d.programme_title} · {d.unit_title||d.suggested_unit_title}
        <p className="muted tiny">{labels[d.state]||d.state} · Security: {d.scan_state}{d.possible_duplicate?' · Possible duplicate':''}</p>
        {d.state!=='withdrawn'&&<button type="button" className="button ghost" disabled={busy} onClick={()=>void withdraw(d.id)}>Withdraw</button>}
      </li>)}</ul>}
    </section>
    <p className="muted tiny" style={{marginTop:14}}>You can also <Link href="/contribute">submit original text notes</Link> or <Link href="/dashboard">return to your dashboard</Link>.</p>
  </Shell>;
}
