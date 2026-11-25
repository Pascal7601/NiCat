'use client';
import {useCallback,useEffect,useState} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {errorText,idPath,staffGet,staffPost,type FollowUpDetail,type FollowUpItem} from '@/lib/staff-workspace';

export default function StaffFollowups(){
 const [items,setItems]=useState<FollowUpItem[]>([]),[selected,setSelected]=useState<FollowUpDetail|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const refresh=useCallback(async()=>{const v=await staffGet<{items:FollowUpItem[]}>('/followups/');setItems(v.items);},[]);
 useEffect(()=>{void refresh().catch(e=>setError(errorText(e)));},[refresh]);
 async function open(id:string){try{setSelected(await staffGet<FollowUpDetail>(`/followups/${idPath(id)}/`));}catch(e){setError(errorText(e));}}
 async function run(fn:()=>Promise<unknown>,message:string){setBusy(true);setError('');setNotice('');try{await fn();await refresh();if(selected)await open(selected.id);setNotice(message);}catch(e){setError(errorText(e));}finally{setBusy(false);}}
 return <StaffFrame title="Student follow-up review" description="Draft answers stay private until an academic reviewer publishes a citation-supported response.">
  {error&&<p role="alert" style={{color:'var(--danger,crimson)'}}>{error}</p>}{notice&&<p role="status">{notice}</p>}
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(310px,1fr))',gap:18}}>
   <section className="card" style={{padding:20}}><h2>Follow-up queue</h2>{items.length===0?<p className="muted">No follow-up records.</p>:<div style={{display:'grid',gap:9}}>{items.map(item=><button className="button ghost" type="button" key={item.id} onClick={()=>void open(item.id)} style={{whiteSpace:'normal',textAlign:'left'}}>{item.question.slice(0,180)}<p className="muted tiny">{item.state}</p></button>)}</div>}</section>
   <section className="card" style={{padding:20}}><h2>Reviewer response</h2>{!selected?<p className="muted">Select a student question.</p>:<>
    <h3>{selected.question}</h3><p className="muted tiny">State: {selected.state}</p>
    <label style={{display:'grid',gap:5}}>Reviewed response<textarea value={selected.draft_answer} readOnly={selected.state!=='draft'} rows={9} onChange={e=>setSelected(c=>c?{...c,draft_answer:e.target.value}:null)} /></label>
    <h3>Source excerpts (fixed by approved Tutor explanation)</h3><ul>{selected.citations.map(c=><li key={c.id}><strong>{c.document}</strong> · {c.rights_status} · {c.state}<p className="muted tiny">{c.text}</p></li>)}</ul>
    <div style={{display:'flex',flexWrap:'wrap',gap:9}}>
     {selected.state==='draft'&&<><button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/followups/${idPath(selected.id)}/`,{draft_answer:selected.draft_answer}),'Review answer saved.')}>Save answer</button>
     <button className="button" disabled={busy} onClick={()=>void run(()=>staffPost(`/followups/${idPath(selected.id)}/action/`,{action:'publish'}),'Reviewed follow-up published.')}>Publish verified answer</button>
     <button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/followups/${idPath(selected.id)}/action/`,{action:'reject'}),'Follow-up rejected.')}>Reject</button></>}
     {selected.state==='published'&&<button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/followups/${idPath(selected.id)}/action/`,{action:'withdraw'}),'Published answer withdrawn.')}>Withdraw</button>}
    </div><p className="muted tiny">Save before publishing. NiCat blocks mock text, revoked citations, and non-finalized attempts.</p>
   </>}</section>
  </div>
 </StaffFrame>;
}
