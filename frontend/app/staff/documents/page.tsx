'use client';
import {useCallback,useEffect,useState} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {clientRequest} from '@/lib/client';

type QueueItem={id:string,title:string,programme:string,unit:string,state:string,scan_state:string,possible_duplicate:boolean};
type Unit={id:string,title:string};
type CurriculumVersion={id:string,label:string};
type ReviewEvent={action:string,rationale:string,created_at:string};
type Detail=QueueItem&{
  programme_id:string,description:string,original_filename:string,size_bytes:number,
  suggested_unit_title:string,suggested_unit_code:string,year_number:number|null,semester_number:number|null,
  document_type:string,source_owner:string,rights_basis:string,rights_evidence:string,
  suggested_topics:string,extraction_state:string,rights_cleared:boolean,
  academic_approved:boolean,permit_question_generation:boolean,permit_resource_display:boolean,
  permit_tutor_use:boolean,extracted_preview:string,events:ReviewEvent[]
};
const api='/api/nicat/document-intake/staff/';
export default function StaffDocumentsPage(){
  const [queue,setQueue]=useState<QueueItem[]>([]);
  const [detail,setDetail]=useState<Detail|null>(null);
  const [units,setUnits]=useState<Unit[]>([]);
  const [versions,setVersions]=useState<CurriculumVersion[]>([]);
  const [versionId,setVersionId]=useState('');
  const [verifiedTitle,setVerifiedTitle]=useState('');
  const [year,setYear]=useState('');
  const [semester,setSemester]=useState('');
  const [verified,setVerified]=useState(false);
  const [unitId,setUnitId]=useState('');
  const [rationale,setRationale]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const refresh=useCallback(async()=>{
    const result=await clientRequest<{items:QueueItem[]}>(api);
    setQueue(result.items);
  },[]);
  useEffect(()=>{void refresh().catch(e=>setError(e instanceof Error?e.message:'Unable to load review queue'));},[refresh]);
  async function open(id:string){
    setError('');setNotice('');setRationale('');setUnitId('');setVersions([]);setVersionId('');setVerified(false);
    try{
      const result=await clientRequest<Detail>(`${api}${encodeURIComponent(id)}/`);
      setDetail(result);
      setVerifiedTitle(result.suggested_unit_title || '');
      setYear(result.year_number ? String(result.year_number) : '');
      setSemester(result.semester_number ? String(result.semester_number) : '');
      const u=await clientRequest<{items:Unit[],curriculum_versions?:CurriculumVersion[]}>(`/api/nicat/document-intake/programmes/${encodeURIComponent(result.programme_id)}/units/`);
      setUnits(u.items);setVersions(u.curriculum_versions??[]);
    }catch(e){setError(e instanceof Error?e.message:'Unable to load document review details');}
  }
  async function action(name:'rights_clear'|'rights_hold'|'academic_approve'|'reject'|'map_unit'){
    if(!detail||busy)return;
    setBusy(true);setError('');setNotice('');
    try{
      await clientRequest(`${api}${encodeURIComponent(detail.id)}/review/`,{
        method:'POST',body:JSON.stringify({action:name,rationale, ...(name==='map_unit'?{unit_id:unitId}:{})}),
      });
      await refresh();await open(detail.id);
      setNotice(`Review action recorded: ${name.replaceAll('_',' ')}. Nothing is public or in the exam bank.`);
    }catch(e){setError(e instanceof Error?e.message:'Review action failed');}
    finally{setBusy(false);}
  }
  async function createAndMap(){
    if(!detail||busy||!versionId||!verified||rationale.trim().length<25)return;
    setBusy(true);setError('');setNotice('');
    try{
      const response=await clientRequest<{unit_created:boolean}>(`${api}${encodeURIComponent(detail.id)}/create-unit/`,{
        method:'POST',body:JSON.stringify({
          curriculum_version_id:versionId,title:verifiedTitle.trim(),
          year_number:Number(year),semester_number:Number(semester),
          catalogue_verified:verified,rationale,
        }),
      });
      await refresh();await open(detail.id);
      setNotice(response.unit_created?'Verified unit created and linked.':'Existing catalogue unit linked to this curriculum and document.');
    }catch(e){setError(e instanceof Error?e.message:'Unable to verify and create unit');}
    finally{setBusy(false);}
  }
  return <StaffFrame title="Academic document intake" description="Verify multi-programme uploads before they become eligible to generate draft questions.">
    {error&&<p role="alert" style={{color:'var(--danger,crimson)'}}>{error}</p>}
    {notice&&<p role="status">{notice}</p>}
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(330px,1fr))',gap:18}}>
      <section className="card" style={{padding:20}}>
        <h2>Document review queue</h2>
        {!queue.length?<p className="muted">No document submissions yet.</p>:<div style={{display:'grid',gap:8}}>
          {queue.map(q=><button key={q.id} type="button" className="button ghost" onClick={()=>void open(q.id)} style={{textAlign:'left',whiteSpace:'normal'}}>
            <strong>{q.title}</strong>
            <p className="muted tiny">{q.programme} · {q.unit}</p>
            <p className="muted tiny">{q.state} · scan {q.scan_state}{q.possible_duplicate?' · flagged duplicate':''}</p>
          </button>)}
        </div>}
      </section>
      <section className="card" style={{padding:20}}>
        <h2>Verification details</h2>
        {!detail?<p className="muted">Select a document to see its review history and safe text preview.</p>:<>
          <h3>{detail.title}</h3>
          <p className="muted tiny">{detail.programme} · {detail.unit||'Unit mapping requested'} · {detail.state}</p>
          <p><strong>Original:</strong> {detail.original_filename} ({Math.round(detail.size_bytes/1024)} KB)</p>
          <p><strong>Rights holder:</strong> {detail.source_owner} — {detail.rights_basis}</p>
          <p><strong>Permission evidence:</strong> {detail.rights_evidence||'Claims original authorship; verify independently'}</p>
          <p><strong>Question generation authorized:</strong> {detail.permit_question_generation?'Yes':'No'}</p>
          <p><strong>Public document display authorized:</strong> {detail.permit_resource_display?'Yes':'No'}</p>
          <p><strong>Tutor use authorized:</strong> {detail.permit_tutor_use?'Yes':'No'}</p>
          <p><strong>Security scan:</strong> {detail.scan_state} · extraction {detail.extraction_state}</p>
          {detail.extracted_preview?<div style={{margin:'14px 0'}}><h3>Extracted text preview (not the original file)</h3><div style={{background:'var(--surface-secondary,#f4f4f4)',padding:14,borderRadius:10,maxHeight:280,overflow:'auto',whiteSpace:'pre-wrap'}}>{detail.extracted_preview}</div></div>:<p className="muted">Preview unavailable until file has passed scanning and text extraction.</p>}
          <label style={{display:'grid',gap:6,marginTop:14}}>Reason for review decision (25+ characters)
            <textarea className="field" rows={4} value={rationale} onChange={e=>setRationale(e.target.value)} placeholder="Document the source evidence and academic rationale..."/>
          </label>
          {!detail.unit&&<section className="card" style={{padding:16,margin:'16px 0',display:'grid',gap:12}}>
            <h3>Resolve missing unit</h3>
            <p className="muted tiny"><strong>Student suggested:</strong> {detail.suggested_unit_title || 'Not provided'}
              {detail.suggested_unit_code ? ` · code ${detail.suggested_unit_code}` : ''}
              {detail.year_number ? ` · Year ${detail.year_number}` : ''}
              {detail.semester_number ? ` · Semester ${detail.semester_number}` : ''}</p>
            <label style={{display:'grid',gap:6}}>Option 1: Map to a verified programme unit
              <select className="field" value={unitId} onChange={e=>setUnitId(e.target.value)}>
                <option value="">Select verified unit</option>{units.map(u=><option key={u.id} value={u.id}>{u.title}</option>)}
              </select>
            </label>
            {!units.length&&<p className="muted tiny">No units are mapped to this programme yet. An authorized catalogue editor can create one below.</p>}
            <div style={{borderTop:'1px solid var(--border,#ddd)',paddingTop:14,display:'grid',gap:10}}>
              <h4>Option 2: Verify and add a missing unit</h4>
              <p className="muted tiny">This creates an official catalogue unit (or reuses an exact-name match) and links it to the chosen curriculum version. Only authorized academic catalogue editors can use this action.</p>
              <label style={{display:'grid',gap:6}}>Verified unit title
                <input className="field" value={verifiedTitle} maxLength={200} onChange={e=>setVerifiedTitle(e.target.value)}/>
              </label>
              <label style={{display:'grid',gap:6}}>Curriculum version
                <select className="field" value={versionId} onChange={e=>setVersionId(e.target.value)}>
                  <option value="">Choose curriculum version</option>
                  {versions.map(v=><option key={v.id} value={v.id}>{v.label}</option>)}
                </select>
              </label>
              {!versions.length&&<p className="muted tiny">No curriculum version exists for this programme. An academic administrator must establish one before the unit can be verified.</p>}
              <div style={{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:10}}>
                <label style={{display:'grid',gap:6}}>Year
                  <select className="field" value={year} onChange={e=>setYear(e.target.value)}>
                    <option value="">Choose year</option>
                    {[1,2,3,4,5,6,7,8].map(n=><option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
                <label style={{display:'grid',gap:6}}>Semester
                  <select className="field" value={semester} onChange={e=>setSemester(e.target.value)}>
                    <option value="">Choose semester</option>
                    {[1,2,3,4].map(n=><option key={n} value={n}>{n}</option>)}
                  </select>
                </label>
              </div>
              <label style={{display:'flex',gap:8,alignItems:'flex-start'}}>
                <input type="checkbox" checked={verified} onChange={e=>setVerified(e.target.checked)}/>
                I verified this unit's name, curriculum version and placement against the programme's curriculum.
              </label>
              <button type="button" className="button ghost" disabled={busy||!verified||!versionId||!verifiedTitle.trim()||!year||!semester||rationale.trim().length<25} onClick={()=>void createAndMap()}>Create and map verified unit</button>
            </div>
          </section>}
          <div style={{display:'flex',flexWrap:'wrap',gap:8,marginTop:12}}>
            {!detail.unit&&<button type="button" className="button ghost" disabled={busy||rationale.trim().length<25||!unitId} onClick={()=>void action('map_unit')}>Verify unit mapping</button>}
            {!detail.rights_cleared&&<button type="button" className="button" disabled={busy||rationale.trim().length<25} onClick={()=>void action('rights_clear')}>Clear rights</button>}
            <button type="button" className="button ghost" disabled={busy||rationale.trim().length<25} onClick={()=>void action('rights_hold')}>Rights hold</button>
            <button type="button" className="button" disabled={busy||rationale.trim().length<25} onClick={()=>void action('academic_approve')}>Academic approval</button>
            <button type="button" className="button ghost" disabled={busy||rationale.trim().length<25} onClick={()=>void action('reject')}>Reject</button>
          </div>
          <h3 style={{marginTop:20}}>Review history</h3>
          {!detail.events.length?<p className="muted tiny">No review actions yet.</p>:<ol>{detail.events.map((ev,i)=><li key={`${ev.created_at}-${i}`}>{ev.action}: {ev.rationale}</li>)}</ol>}
        </>}
      </section>
    </div>
    <p className="muted tiny" style={{marginTop:14}}>File originals remain in private storage. This page deliberately does not offer unsafe public file URLs or publish documents to Tutor.</p>
  </StaffFrame>;
}
