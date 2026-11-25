'use client';
import {useCallback,useEffect,useState,type FormEvent} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {errorText,idPath,staffGet,staffPost,type TutorDraft} from '@/lib/staff-workspace';

export default function StaffTutor(){
 const [items,setItems]=useState<TutorDraft[]>([]),[selected,setSelected]=useState<TutorDraft|null>(null),[revision,setRevision]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const refresh=useCallback(async()=>{const v=await staffGet<{items:TutorDraft[]}>('/tutor/');setItems(v.items);},[]);
 useEffect(()=>{void refresh().catch(e=>setError(errorText(e)));},[refresh]);
 async function run(fn:()=>Promise<unknown>, message:string){setBusy(true);setError('');setNotice('');try{await fn();await refresh();setNotice(message);setSelected(null);}catch(e){setError(errorText(e));}finally{setBusy(false);}}
 async function generate(e:FormEvent){e.preventDefault();await run(()=>staffPost('/tutor/generate/',{revision_id:revision}),'Tutor draft created (or existing draft returned).');}
 function setField(key:'explanation'|'common_mistake'|'practice_tip',value:string){setSelected(cur=>cur?{...cur,[key]:value}:null);}
 return <StaffFrame title="Tutor explanation review" description="Generate grounded drafts, inspect citations, edit explanations, and explicitly publish reviewer-approved material.">
  {error&&<p role="alert" style={{color:'var(--danger,crimson)'}}>{error}</p>}{notice&&<p role="status">{notice}</p>}
  <section className="card" style={{padding:20}}><h2>Create Tutor draft</h2><p className="muted tiny">Requires a published question revision with approved, rights-cleared source excerpts. A mock response must be replaced before publication.</p>
   <form onSubmit={e=>{void generate(e);}} style={{display:'flex',flexWrap:'wrap',gap:9}}>
    <label style={{flex:'1 1 280px'}}>Question revision UUID<input required value={revision} onChange={e=>setRevision(e.target.value)} placeholder="QuestionRevision UUID"/></label>
    <button className="button" disabled={busy||!revision.trim()}>Generate grounded draft</button>
   </form>
  </section>
  <section className="card" style={{marginTop:18,padding:20}}><h2>Drafts and published explanations</h2>
   {items.length===0?<p className="muted">No explanation records yet.</p>:<div style={{display:'grid',gap:9}}>{items.map(x=><button key={x.id} type="button" className="button ghost" style={{whiteSpace:'normal',textAlign:'left'}} onClick={()=>setSelected({...x})}>{x.topic} · v{x.version} · {x.state} · {x.question.slice(0,110)}</button>)}</div>}
  </section>
  {selected&&<section className="card" style={{marginTop:18,padding:20}}><h2>Review explanation</h2>
   <p><strong>{selected.topic}</strong> · revision {selected.revision_id} · v{selected.version}</p><p className="muted tiny">{selected.question}</p>
   {(['explanation','common_mistake','practice_tip'] as const).map(key=><label key={key} style={{display:'grid',gap:5,margin:'13px 0'}}>{key.replace('_',' ')}<textarea rows={key==='explanation'?8:4} readOnly={selected.state!=='draft'} value={selected[key]} onChange={e=>setField(key,e.target.value)}/></label>)}
   <h3>Approved academic evidence</h3><ul>{selected.citations.map(c=><li key={c.id}><strong>{c.document}</strong> · {c.rights_status} · {c.state}<p className="muted tiny" style={{whiteSpace:'pre-wrap'}}>{c.text}</p></li>)}</ul>
   <div style={{display:'flex',flexWrap:'wrap',gap:10}}>
    {selected.state==='draft'&&<><button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/tutor/${idPath(selected.id)}/`,{explanation:selected.explanation,common_mistake:selected.common_mistake,practice_tip:selected.practice_tip}),'Draft saved. Review and publish separately.')}>Save draft edits</button>
    <button className="button" disabled={busy} onClick={()=>void run(()=>staffPost(`/tutor/${idPath(selected.id)}/action/`,{action:'publish'}),'Explanation published after backend academic checks.')}>Publish reviewed explanation</button></>}
    {selected.state==='published'&&<button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/tutor/${idPath(selected.id)}/action/`,{action:'withdraw'}),'Explanation withdrawn.')}>Withdraw published explanation</button>}
   </div><p className="muted tiny">Save draft edits before publishing. The server rechecks source rights, citation fingerprints and publication permissions.</p>
  </section>}
 </StaffFrame>;
}
