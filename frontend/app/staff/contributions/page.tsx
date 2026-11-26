'use client';
import {useCallback,useEffect,useState} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {errorText,idPath,staffGet,staffPost,type ContributionDetail,type ContributionItem} from '@/lib/staff-workspace';

export default function StaffContributions(){
 const [list,setList]=useState<ContributionItem[]>([]),[selected,setSelected]=useState<ContributionDetail|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const refresh=useCallback(async()=>{const data=await staffGet<{items:ContributionItem[]}>('/contributions/');setList(data.items);},[]);
 useEffect(()=>{void refresh().catch(e=>setError(errorText(e)));},[refresh]);
 async function open(id:string){setError('');try{setSelected(await staffGet<ContributionDetail>(`/contributions/${idPath(id)}/`));}catch(e){setError(errorText(e));}}
 async function run(fn:()=>Promise<unknown>,message:string){setBusy(true);setError('');setNotice('');try{await fn();await refresh();if(selected)await open(selected.id);setNotice(message);}catch(e){setError(errorText(e));}finally{setBusy(false);}}
 function update(key:'rights_review_note'|'academic_review_note',value:string){setSelected(cur=>cur?{...cur,[key]:value}:null);}
 return <StaffFrame title="Student contribution reviews" description="Verify permission and accuracy with different reviewers; approval does not publish or index a student's notes.">
  {error&&<p role="alert" style={{color:'var(--danger,crimson)'}}>{error}</p>}{notice&&<p role="status">{notice}</p>}
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(310px,1fr))',gap:18}}>
   <section className="card" style={{padding:20}}><h2>Review queue</h2>{list.length===0?<p className="muted">No submitted materials.</p>:<div style={{display:'grid',gap:9}}>{list.map(c=><button type="button" key={c.id} onClick={()=>void open(c.id)} className="button ghost" style={{textAlign:'left',whiteSpace:'normal'}}>
    <strong>{c.title}</strong> · {c.unit}<p className="muted tiny">{c.state} · rights {c.rights_cleared?'cleared':'pending'} {c.possible_duplicate?'· duplicate flag':''}</p>
   </button>)}</div>}</section>
   <section className="card" style={{padding:20}}><h2>Review details</h2>
    {!selected?<p className="muted">Select a submission to see the content and verification trail.</p>:<>
     <h3>{selected.title}</h3><p className="muted tiny">{selected.unit} · {selected.state} · possible duplicate: {selected.possible_duplicate?'yes':'no'}</p>
     <p className="muted tiny">Student declared original authorship: {selected.author_declaration?'yes':'no'}; public display permission: {selected.allow_display?'yes':'no'}; future Tutor use permission: {selected.allow_ai_use?'yes':'no'}.</p>
     <div style={{whiteSpace:'pre-wrap',background:'var(--surface-secondary,#f4f4f4)',padding:14,borderRadius:10,marginBottom:14,maxHeight:280,overflow:'auto'}}>{selected.body}</div>
     <label style={{display:'grid',gap:6}}>Rights review rationale<textarea value={selected.rights_review_note} onChange={e=>update('rights_review_note',e.target.value)} rows={3} readOnly={!!selected.rights_reviewed_by||selected.state!=='pending_review'}/></label>
     {selected.state==='pending_review'&&!selected.rights_reviewed_by&&<div style={{display:'flex',flexWrap:'wrap',gap:8,margin:'9px 0 18px'}}>
       <button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/`,{field:'rights_review_note',note:selected.rights_review_note}),'Rights rationale saved.')}>Save rights rationale</button>
       <button className="button" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/action/`,{action:'clear_rights'}),'Rights cleared, pending separate academic review.')}>Clear rights</button>
       <button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/action/`,{action:'hold_rights'}),'Rights hold recorded.')}>Place on rights hold</button>
     </div>}
     <label style={{display:'grid',gap:6}}>Academic review rationale<textarea value={selected.academic_review_note} onChange={e=>update('academic_review_note',e.target.value)} rows={3} readOnly={!['pending_review','rights_hold'].includes(selected.state)}/></label>
     {['pending_review','rights_hold'].includes(selected.state)&&<div style={{display:'flex',flexWrap:'wrap',gap:8,margin:'9px 0 18px'}}>
      <button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/`,{field:'academic_review_note',note:selected.academic_review_note}),'Academic rationale saved.')}>Save academic rationale</button>
      <button className="button" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/action/`,{action:'approve'}),'Academically approved (still private).')}>Academic approval</button>
      <button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/action/`,{action:'reject'}),'Submission rejected.')}>Reject</button>
     </div>}
     {selected.state!=='withdrawn'&&<button className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/contributions/${idPath(selected.id)}/action/`,{action:'withdraw'}),'Contribution withdrawn.')}>Withdraw contribution</button>}
     <h3 style={{marginTop:18}}>Decision history</h3>{selected.decisions.length===0?<p className="muted tiny">No recorded decisions yet.</p>:<ol>{selected.decisions.map((d,i)=><li key={`${d.created_at}-${i}`}>{d.action}: {d.rationale}</li>)}</ol>}
    </>}
   </section>
  </div>
 </StaffFrame>;
}
