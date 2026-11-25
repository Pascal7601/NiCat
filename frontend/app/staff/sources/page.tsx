'use client';
import {useCallback,useEffect,useState,type FormEvent} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {errorText,idPath,staffGet,staffPost,type SourceDocument,type SourceExcerpt,type SourceReference,type SourceTopic} from '@/lib/staff-workspace';

type Items<T>={items:T[]};
const empty={docTitle:'',docUnit:'',docKind:'lecture_notes',docUrl:'',referenceDoc:'',page:'',section:'',excerptRef:'',excerptTopic:'',excerptText:'',rightsDoc:'',rightsStatus:'allowed',rightsRationale:''};

export default function StaffSources(){
 const [units,setUnits]=useState<Array<{id:string;title:string}>>([]),[documents,setDocuments]=useState<SourceDocument[]>([]),[references,setReferences]=useState<SourceReference[]>([]),[topics,setTopics]=useState<SourceTopic[]>([]),[excerpts,setExcerpts]=useState<SourceExcerpt[]>([]);
 const [form,setForm]=useState(empty),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[selected,setSelected]=useState<SourceExcerpt|null>(null);
 const change=(key:keyof typeof empty,val:string)=>setForm(f=>({...f,[key]:val}));
 const refresh=useCallback(async()=>{
  const [u,d,r,t,e]=await Promise.all([
   staffGet<Items<{id:string;title:string}>>('/sources/units/'),
   staffGet<Items<SourceDocument>>('/sources/documents/'),staffGet<Items<SourceReference>>('/sources/references/'),
   staffGet<Items<SourceTopic>>('/sources/topics/'),staffGet<Items<SourceExcerpt>>('/sources/excerpts/'),
  ]);
  setUnits(u.items);setDocuments(d.items);setReferences(r.items);setTopics(t.items);setExcerpts(e.items);
 },[]);
 useEffect(()=>{void refresh().catch(e=>setError(errorText(e)));},[refresh]);
 const chosenDoc=documents.find(d=>d.id===form.referenceDoc);
 const chosenRef=references.find(r=>r.id===form.excerptRef);
 const excerptDoc=documents.find(d=>d.id===chosenRef?.document_id);
 async function run(task:()=>Promise<unknown>,done:string){setBusy(true);setError('');setNotice('');try{await task();await refresh();setNotice(done);setSelected(null);}catch(e){setError(errorText(e));}finally{setBusy(false);}}
 const on=(evt:FormEvent,task:()=>Promise<unknown>,done:string)=>{evt.preventDefault();void run(task,done);};
 return <StaffFrame title="Academic source library" description="Register sources, record rights decisions, create citations and approve topic-aligned excerpts.">
  {error&&<p role="alert" style={{color:'var(--danger,crimson)'}}>{error}</p>}{notice&&<p role="status">{notice}</p>}
  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(305px,1fr))',gap:16}}>
   <section className="card" style={{padding:20}}><h2>1 · Register source</h2>
    <p className="muted tiny">New sources start with unknown rights. Nothing is automatically approved.</p>
    <form onSubmit={e=>on(e,()=>staffPost('/sources/documents/',{title:form.docTitle,unit_id:form.docUnit,source_kind:form.docKind,source_url:form.docUrl}), 'Source registered; review rights before approving excerpts.')} style={{display:'grid',gap:10}}>
     <label>Title<input required minLength={5} maxLength={500} value={form.docTitle} onChange={e=>change('docTitle',e.target.value)}/></label>
     <label>Unit<select required value={form.docUnit} onChange={e=>change('docUnit',e.target.value)}><option value="">Select unit</option>{units.map(u=><option key={u.id} value={u.id}>{u.title}</option>)}</select></label>
     <label>Type<select value={form.docKind} onChange={e=>change('docKind',e.target.value)}>{['lecture_notes','course_outline','revision','reference','past_cat','past_exam'].map(k=><option key={k}>{k}</option>)}</select></label>
     <label>Source URL (optional)<input type="url" value={form.docUrl} onChange={e=>change('docUrl',e.target.value)}/></label>
     <button className="button" disabled={busy||!form.docUnit}>Register source</button>
    </form>
   </section>
   <section className="card" style={{padding:20}}><h2>2 · Decide rights</h2>
    <p className="muted tiny">Only authorized rights officers can confirm permitted use; evidence is saved in an audit record.</p>
    <form onSubmit={e=>on(e,()=>staffPost(`/sources/documents/${idPath(form.rightsDoc)}/rights/`,{rights_status:form.rightsStatus,rationale:form.rightsRationale}), 'Rights decision recorded.')} style={{display:'grid',gap:10}}>
     <label>Document<select required value={form.rightsDoc} onChange={e=>change('rightsDoc',e.target.value)}><option value="">Select source</option>{documents.map(d=><option key={d.id} value={d.id}>{d.title} [{d.rights_status}]</option>)}</select></label>
     <label>Decision<select value={form.rightsStatus} onChange={e=>change('rightsStatus',e.target.value)}><option value="allowed">Permission confirmed</option><option value="restricted">Restricted</option></select></label>
     <label>Verified rights evidence<textarea rows={4} minLength={30} maxLength={4000} required value={form.rightsRationale} onChange={e=>change('rightsRationale',e.target.value)} placeholder="Document who owns the material, the precise permission granted, and how this was verified."/></label>
     <button className="button" disabled={busy||!form.rightsDoc||form.rightsRationale.trim().length<30}>Record rights decision</button>
    </form>
   </section>
   <section className="card" style={{padding:20}}><h2>3 · Add citation reference</h2>
    <form onSubmit={e=>on(e,()=>staffPost('/sources/references/',{document_id:form.referenceDoc,page_label:form.page,section_label:form.section}), 'Reference saved.')} style={{display:'grid',gap:10}}>
     <label>Document<select required value={form.referenceDoc} onChange={e=>change('referenceDoc',e.target.value)}><option value="">Select source</option>{documents.map(d=><option key={d.id} value={d.id}>{d.title}</option>)}</select></label>
     <label>Page (optional)<input maxLength={80} value={form.page} onChange={e=>change('page',e.target.value)}/></label>
     <label>Section<input maxLength={200} value={form.section} onChange={e=>change('section',e.target.value)}/></label>
     <button className="button" disabled={busy||!chosenDoc}>Create reference</button>
    </form>
   </section>
   <section className="card" style={{padding:20}}><h2>4 · Create excerpt</h2>
    <form onSubmit={e=>on(e,()=>staffPost('/sources/excerpts/',{reference_id:form.excerptRef,topic_id:form.excerptTopic,text:form.excerptText}), 'Excerpt saved as a reviewable draft.')} style={{display:'grid',gap:10}}>
     <label>Reference<select required value={form.excerptRef} onChange={e=>{change('excerptRef',e.target.value);change('excerptTopic','');}}><option value="">Select reference</option>{references.map(r=><option key={r.id} value={r.id}>{r.document}{r.page?` · p. ${r.page}`:''}</option>)}</select></label>
     <label>Topic<select required value={form.excerptTopic} onChange={e=>change('excerptTopic',e.target.value)}><option value="">Select topic in the same unit</option>{topics.filter(t=>t.unit_id===excerptDoc?.unit_id).map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></label>
     <label>Evidence excerpt<textarea required rows={6} minLength={30} maxLength={5000} value={form.excerptText} onChange={e=>change('excerptText',e.target.value)}/></label>
     <button className="button" disabled={busy||!form.excerptRef||!form.excerptTopic}>Save excerpt as draft</button>
    </form>
   </section>
  </div>
  <section className="card" style={{marginTop:20,padding:20}}><h2>Source excerpt review queue</h2>
   <p className="muted tiny">Only rights-cleared, topic-aligned excerpts should be approved. Choosing a record reveals its evidence for inspection.</p>
   {excerpts.length===0?<p className="muted">No excerpts available.</p>:<div style={{display:'grid',gap:10}}>{excerpts.map(x=><button type="button" key={x.id} onClick={()=>setSelected(x)} className="button ghost" style={{textAlign:'left',whiteSpace:'normal'}}>{x.topic} · {x.document} · {x.state} · rights: {x.rights_status}</button>)}</div>}
   {selected&&<div style={{marginTop:18,padding:15,border:'1px solid var(--border,#999)',borderRadius:10}}><h3>{selected.topic}: {selected.document}</h3>
    <p style={{whiteSpace:'pre-wrap'}}>{selected.text}</p><p className="muted tiny">Status: {selected.state} · Rights: {selected.rights_status}</p>
    {selected.state==='draft'&&<button type="button" className="button" disabled={busy} onClick={()=>void run(()=>staffPost(`/sources/excerpts/${idPath(selected.id)}/action/`,{action:'approve'}),'Source excerpt approved.')}>Approve excerpt</button>}
    {selected.state==='approved'&&<button type="button" className="button ghost" disabled={busy} onClick={()=>void run(()=>staffPost(`/sources/excerpts/${idPath(selected.id)}/action/`,{action:'withdraw'}),'Source excerpt withdrawn.')}>Withdraw excerpt</button>}
   </div>}
  </section>
 </StaffFrame>;
}
