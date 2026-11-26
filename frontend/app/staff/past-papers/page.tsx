"use client";

import {useCallback, useEffect, useState} from "react";
import StaffFrame from "@/components/staff/StaffFrame";
import {clientRequest} from "@/lib/client";

type Paper = {id:string;title:string;unit:string;programme:string;page_count:number;extracted_length:number;can_generate:boolean};
type Topic = {id:string;title:string;unit_id:string};
type PaperList = {items:Paper[];topics:Topic[];unit_ids:Record<string,string>;provider:string};
type PaperQuestion = {id:string;document_id:string;position:number;original_ocr_text:string;corrected_text:string;page_number:number|null;marks:string|null;topic_id:string|null;verified_answer_context:string;flags:string[];state:string;extracted_by_id:string;verified_by_id:string|null};
type ReviewEvent = {action:string;rationale:string;created_at:string};
type Candidate = {id:string;state:string;kind:string;position:number;prompt:string;options:string[];correct_index:number|null;explanation:string;rubric:Array<{criterion:string;marks:number}>;evidence_quote:string;validation_errors:string[];review_note:string};
type VariationJob = {id:string;state:string;failure_code:string;provider:string;kind:string;created_at:string;candidates:Candidate[]};

const ROOT="/api/nicat/";
const get = <T,>(path:string)=>clientRequest<T>(ROOT+path);
const post = <T,>(path:string, body:unknown)=>clientRequest<T>(ROOT+path,{method:"POST",body:JSON.stringify(body)});
const U=(id:string)=>encodeURIComponent(id);
const errorText=(error:unknown)=>error instanceof Error?error.message:"Unexpected request failure";
const reasonOK=(reason:string)=>reason.trim().length>=25;

export default function PastPaperReviewPage(){
  const [papers,setPapers]=useState<Paper[]>([]);
  const [topics,setTopics]=useState<Topic[]>([]);
  const [unitIds,setUnitIds]=useState<Record<string,string>>({});
  const [provider,setProvider]=useState("mock");
  const [documentId,setDocumentId]=useState("");
  const [questions,setQuestions]=useState<PaperQuestion[]>([]);
  const [events,setEvents]=useState<ReviewEvent[]>([]);
  const [questionId,setQuestionId]=useState("");
  const [form,setForm]=useState<PaperQuestion|null>(null);
  const [image,setImage]=useState("");
  const [previewPage,setPreviewPage]=useState(1);
  const [compared,setCompared]=useState(false);
  const [reason,setReason]=useState("");
  const [manualText,setManualText]=useState("");
  const [manualPage,setManualPage]=useState(1);
  const [jobs,setJobs]=useState<VariationJob[]>([]);
  const [variationCount,setVariationCount]=useState(1);
  const [variationKind,setVariationKind]=useState("mcq");
  const [variationDifficulty,setVariationDifficulty]=useState("medium");
  const [editing,setEditing]=useState<Candidate|null>(null);
  const [editOptions,setEditOptions]=useState("");
  const [editRubric,setEditRubric]=useState("[]");
  const [vendorNote,setVendorNote]=useState("");
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");

  const loadPapers=useCallback(async()=>{
    const data=await get<PaperList>("past-papers/");
    setPapers(data.items);setTopics(data.topics);setUnitIds(data.unit_ids);setProvider(data.provider);
  },[]);
  useEffect(()=>{void loadPapers().catch(e=>setError(errorText(e)));},[loadPapers]);
  const paper=papers.find(p=>p.id===documentId);
  const paperTopics=topics.filter(t=>t.unit_id===unitIds[documentId]);

  const loadQuestions=useCallback(async(id:string)=>{
    const data=await get<{items:PaperQuestion[];events:ReviewEvent[]}>(`past-papers/${U(id)}/questions/`);
    setQuestions(data.items);setEvents(data.events);
  },[]);
  const loadJobs=useCallback(async(qid:string)=>{
    const data=await get<{jobs:VariationJob[]}>(`past-paper-questions/${U(qid)}/variations/`);
    setJobs(data.jobs);
  },[]);
  const loadImage=useCallback(async(doc:string,page:number)=>{
    setImage("");
    const data=await get<{image_base64:string;mime:string}>(`past-papers/${U(doc)}/page/${page}/`);
    setImage(`data:${data.mime};base64,${data.image_base64}`);
  },[]);

  async function run(action:()=>Promise<unknown>,success:string,refresh=true){
    setBusy(true);setError("");setNotice("");
    try{
      await action();
      if(refresh&&documentId)await loadQuestions(documentId);
      if(refresh&&questionId)await loadJobs(questionId);
      setNotice(success);
    }catch(e){setError(errorText(e));}
    finally{setBusy(false);}
  }

  async function selectPaper(id:string){
    setDocumentId(id);setQuestionId("");setQuestions([]);setEvents([]);setForm(null);
    setImage("");setJobs([]);setPreviewPage(1);setCompared(false);setError("");setNotice("");
    if(!id)return;
    try{await Promise.all([loadQuestions(id),loadImage(id,1)]);}catch(e){setError(errorText(e));}
  }
  async function selectQuestion(q:PaperQuestion){
    setQuestionId(q.id);setForm({...q});setCompared(false);setReason("");
    setPreviewPage(q.page_number||1);setEditing(null);setJobs([]);
    try{await Promise.all([loadJobs(q.id),loadImage(q.document_id,q.page_number||1)]);}catch(e){setError(errorText(e));}
  }
  async function saveCorrection(){
    if(!form||!form.page_number||!form.topic_id)return;
    await run(()=>post(`past-paper-questions/${U(form.id)}/correct/`,{
      corrected_text:form.corrected_text,page_number:form.page_number,topic_id:form.topic_id,
      marks:form.marks||null,verified_answer_context:form.verified_answer_context,rationale:reason,
    }),"OCR correction saved. Another authorized reviewer must visually verify it.");
    const updated=await get<{items:PaperQuestion[]}>(`past-papers/${U(form.document_id)}/questions/`);
    const newest=updated.items.find(q=>q.id===form.id);
    if(newest)setForm(newest);
    setCompared(false); // Reviewer must compare the saved version again.
  }
  async function decideQuestion(action:"verify"|"reject"){
    if(!form)return;
    await run(()=>post(`past-paper-questions/${U(form.id)}/review/`,{
      action,rationale:reason,compared_with_original:compared,
    }),action==="verify"?"Verified against the original scanned page. Not published.":"Question rejected.");
    const updated=await get<{items:PaperQuestion[]}>(`past-papers/${U(form.document_id)}/questions/`);
    const newest=updated.items.find(q=>q.id===form.id);if(newest)setForm(newest);
  }
  async function createManual(){
    if(!documentId)return;
    await run(()=>post(`past-papers/${U(documentId)}/questions/manual/`,{text:manualText,page_number:manualPage}),
      "Manual question saved as unverified; an independent reviewer must compare it to the PDF.");
    setManualText("");
  }
  async function queueVariation(){
    if(!form)return;
    await run(()=>post(`past-paper-questions/${U(form.id)}/variations/`,{
      count:variationCount,kind:variationKind,difficulty:variationDifficulty,
    }),"Private variation job queued. Run nicat_process_paper_variations, then refresh.");
  }
  async function decideVariation(candidate:Candidate,action:"approve"|"reject"){
    await run(()=>post(`past-paper-variations/${U(candidate.id)}/review/`,{action,rationale:reason}),
      action==="approve"?"Private variation approved; it has NOT been imported into the question bank.":"Variation rejected.");
  }
  async function saveVariationEdit(){
    if(!editing)return;
    try{
      const rubric=JSON.parse(editRubric) as unknown;
      if(!Array.isArray(rubric))throw new Error("Rubric must be a JSON list");
      await run(()=>post(`past-paper-variations/${U(editing.id)}/edit/`,{
        kind:editing.kind,prompt:editing.prompt,explanation:editing.explanation,
        options:editing.kind==="mcq"?editOptions.split("\n").map(s=>s.trim()).filter(Boolean):[],
        correct_index:editing.kind==="mcq"?editing.correct_index:null,
        rubric:editing.kind==="mcq"?[]:rubric,
        evidence_quote:editing.evidence_quote,rationale:reason,
      }),"Candidate corrected. The independent approval step remains required.");
      setEditing(null);
    }catch(e){setError(errorText(e));}
  }
  const active=questions.find(q=>q.id===questionId);

  return <StaffFrame title="Past-paper question verification" description="Compare OCR against the original scanned paper before making practice variations. Never publish raw OCR or mock candidates.">
    {error&&<p role="alert" style={{color:"var(--danger,crimson)"}}>{error}</p>}
    {notice&&<p role="status">{notice}</p>}
    <section className="card" style={{padding:22,marginBottom:16}}>
      <h2>Verified past-paper intake</h2>
      <p className="muted tiny">Only fully reviewed, malware-clean PDF past papers are shown here. This workflow does not publish original questions or AI drafts.</p>
      <label>Approved past paper
        <select className="field" value={documentId} onChange={e=>void selectPaper(e.target.value)}>
          <option value="">Choose a paper</option>
          {papers.map(p=><option key={p.id} value={p.id}>{p.title} · {p.programme} · {p.unit}</option>)}
        </select>
      </label>
      {paper&&<>
        <p className="muted tiny">{paper.page_count} pages · {paper.extracted_length.toLocaleString()} OCR characters · Variation authorization: {paper.can_generate?"declared, subject to independent review":"not granted"}</p>
        <button type="button" className="button ghost" disabled={busy||questions.length>0} onClick={()=>void run(()=>post(`past-papers/${U(documentId)}/questions/`,{}),"Unverified OCR suggestions created.")}>Suggest question boundaries from OCR</button>
      </>}
    </section>
    {paper&&<div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(330px,1fr))",gap:18}}>
      <section className="card" style={{padding:20}}>
        <h2>Original paper preview — private</h2>
        <p className="muted tiny">Always verify the page, question wording, marks and diagrams visually. This image is served only to authorized staff.</p>
        <label>PDF page (1–{paper.page_count})
          <input className="field" type="number" min={1} max={paper.page_count} value={previewPage} onChange={e=>setPreviewPage(Number(e.target.value))}/>
        </label>
        <button className="button ghost" type="button" disabled={busy||previewPage<1||previewPage>paper.page_count} onClick={()=>void run(()=>loadImage(documentId,previewPage),"Page refreshed",false)}>Load original page</button>
        {image?<img alt={`Original exam paper page ${previewPage} for staff verification`} src={image} style={{width:"100%",height:"auto",marginTop:12,border:"1px solid var(--border,#ddd)",borderRadius:8}}/>:<p className="muted">Original page preview not loaded.</p>}
        <label style={{display:"flex",gap:8,alignItems:"flex-start",marginTop:12}}>
          <input type="checkbox" checked={compared} onChange={e=>setCompared(e.target.checked)}/>
          I compared the corrected question to this original PDF page, including marks and any missing diagrams.
        </label>
      </section>
      <section className="card" style={{padding:20}}>
        <h2>Extracted question queue</h2>
        {questions.length===0?<p className="muted">No OCR suggestions yet. Use the button above, or manually transcribe a question below.</p>:questions.map(q=><button type="button" key={q.id} className="button ghost" onClick={()=>void selectQuestion(q)} style={{display:"block",width:"100%",textAlign:"left",whiteSpace:"normal",marginBottom:8,borderColor:q.id===questionId?"var(--primary,#6655e8)":undefined}}>
          <strong>Q{q.position}</strong> · {q.state} · page {q.page_number??"unconfirmed"}
          <p className="muted tiny">{q.corrected_text.slice(0,145)}…</p>
        </button>)}
        <div style={{marginTop:20,borderTop:"1px solid var(--border,#ddd)",paddingTop:16}}>
          <h3>Add a missed question manually</h3>
          <label>Original PDF page<input className="field" type="number" min={1} max={paper.page_count} value={manualPage} onChange={e=>setManualPage(Number(e.target.value))}/></label>
          <label>Manually transcribed question<textarea className="field" rows={4} value={manualText} onChange={e=>setManualText(e.target.value)} placeholder="Transcribe from the original, not guessed OCR..."/></label>
          <button type="button" className="button ghost" disabled={busy||manualText.trim().length<15} onClick={()=>void createManual()}>Add unverified question</button>
        </div>
        {events.length>0&&<><h3 style={{marginTop:20}}>Audit history</h3><ol>{events.slice(0,20).map((e,i)=><li key={`${e.created_at}-${i}`} className="muted tiny">{e.action}: {e.rationale}</li>)}</ol></>}
      </section>
    </div>}
    {form&&paper&&<section className="card" style={{padding:22,marginTop:16}}>
      <h2>Correct and verify question Q{form.position}</h2>
      <p className="muted tiny">OCR text is untrusted. Corrections and visual verification are separate steps, performed by different staff accounts. Current state: {form.state}.</p>
      <details><summary>Original OCR suggestion</summary><pre style={{whiteSpace:"pre-wrap"}}>{form.original_ocr_text||"Manually added question"}</pre></details>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))",gap:12,marginTop:12}}>
        <label>Verified source PDF page<input className="field" type="number" min={1} max={paper.page_count} value={form.page_number??""} disabled={form.state!=="draft"} onChange={e=>setForm({...form,page_number:Number(e.target.value)})}/></label>
        <label>Marks (optional)<input className="field" type="number" step="0.5" min="0.5" max="100" value={form.marks??""} disabled={form.state!=="draft"} onChange={e=>setForm({...form,marks:e.target.value||null})}/></label>
        <label>Topic<select className="field" value={form.topic_id??""} disabled={form.state!=="draft"} onChange={e=>setForm({...form,topic_id:e.target.value})}>
          <option value="">Select verified course topic</option>
          {paperTopics.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}
        </select></label>
      </div>
      {!paperTopics.length&&<p className="muted tiny">No topics configured for this unit yet. A curriculum editor must add verified topics before question verification.</p>}
      <label>Corrected examination question (compare with original PDF)
        <textarea className="field" rows={5} value={form.corrected_text} disabled={form.state!=="draft"} onChange={e=>setForm({...form,corrected_text:e.target.value})}/>
      </label>
      <label>Checked answer/reference context — required for AI variations, not for OCR verification
        <textarea className="field" rows={5} value={form.verified_answer_context} disabled={form.state!=="draft"} onChange={e=>setForm({...form,verified_answer_context:e.target.value})} placeholder="Use a verified marking scheme or lecturer-approved reference. Do not invent an answer from the paper alone."/>
      </label>
      <label>Review rationale (25+ characters)<textarea className="field" rows={3} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Record exactly what you checked or corrected..."/></label>
      {form.state==="draft"&&<div style={{display:"flex",gap:8,flexWrap:"wrap",marginTop:12}}>
        <button type="button" className="button ghost" disabled={busy||!reasonOK(reason)||!form.topic_id||!form.page_number} onClick={()=>void saveCorrection()}>Save OCR correction</button>
        <button type="button" className="button" disabled={busy||!reasonOK(reason)||!compared||!active?.page_number||!active?.topic_id} onClick={()=>void decideQuestion("verify")}>Verify against original PDF</button>
        <button type="button" className="button ghost" disabled={busy||!reasonOK(reason)} onClick={()=>void decideQuestion("reject")}>Reject extraction</button>
      </div>}
      {form.state==="verified"&&<div style={{borderTop:"1px solid var(--border,#ddd)",marginTop:22,paddingTop:14}}>
        <h3>Generate new practice variations</h3>
        <p className="muted tiny">Only from a verified question AND verified answer/reference context (60+ characters). Provider: {provider}. Mock data cannot be approved.</p>
        <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
          <label>Kind<select className="field" value={variationKind} onChange={e=>setVariationKind(e.target.value)}><option value="mcq">MCQ</option><option value="short">Short answer</option><option value="essay">Essay</option></select></label>
          <label>Difficulty<select className="field" value={variationDifficulty} onChange={e=>setVariationDifficulty(e.target.value)}><option value="easy">Beginner</option><option value="medium">Intermediate</option><option value="hard">Advanced</option></select></label>
          <label>Count<select className="field" value={variationCount} onChange={e=>setVariationCount(Number(e.target.value))}>{[1,2,3].map(n=><option key={n} value={n}>{n}</option>)}</select></label>
        </div>
        <button className="button" type="button" disabled={busy||!paper.can_generate||form.verified_answer_context.trim().length<60} onClick={()=>void queueVariation()}>Queue private variations</button>
        {provider!=="mock"&&<div style={{marginTop:16}}>
          <h4>Independent external-provider authorization</h4>
          <p className="muted tiny">Before sending university papers to an external AI provider, an independent rights/vendor reviewer must confirm data-transfer and derivative-use permissions. This is separate from document approval.</p>
          <label>Vendor/data-rights assessment (40+ characters)<textarea rows={3} className="field" value={vendorNote} onChange={e=>setVendorNote(e.target.value)}/></label>
          <button type="button" className="button ghost" disabled={busy||vendorNote.trim().length<40} onClick={()=>void run(()=>post(`past-papers/${U(documentId)}/external-authorization/`,{rationale:vendorNote,revoke:false}),"Vendor authorization recorded. Requester must be a different authorized reviewer.")}>Authorize provider</button>{" "}
          <button type="button" className="button ghost" disabled={busy||vendorNote.trim().length<40} onClick={()=>void run(()=>post(`past-papers/${U(documentId)}/external-authorization/`,{rationale:vendorNote,revoke:true}),"Vendor authorization revoked.")}>Revoke provider authorization</button>
        </div>}
      </div>}
      <div style={{marginTop:18,borderTop:"1px solid var(--border,#ddd)",paddingTop:14}}>
        <h3>Variation history</h3>
        <button type="button" className="button ghost" disabled={busy} onClick={()=>void run(()=>loadJobs(form.id),"Variation jobs refreshed.",false)}>Refresh jobs and candidates</button>
        {jobs.length===0?<p className="muted tiny">No variation jobs yet.</p>:jobs.map(job=><article key={job.id} style={{marginTop:12,border:"1px solid var(--border,#ddd)",borderRadius:8,padding:12}}>
          <strong>{job.kind} · {job.provider} · {job.state}</strong> {job.failure_code&&<span className="muted tiny">({job.failure_code})</span>}
          {job.candidates.map(c=><section key={c.id} style={{borderTop:"1px solid var(--border,#ddd)",marginTop:12,paddingTop:12}}>
            <h4>{c.position}. {c.kind.toUpperCase()} · {c.state}</h4>
            <p style={{whiteSpace:"pre-wrap"}}>{c.prompt}</p>
            {c.options.length>0&&<ol>{c.options.map((opt,i)=><li key={i}>{opt} {i===c.correct_index?"(proposed answer)":""}</li>)}</ol>}
            <p><strong>Explanation:</strong> {c.explanation}</p>
            <blockquote>{c.evidence_quote}</blockquote>
            {c.validation_errors.length>0&&<p className="muted tiny">Validation flags: {c.validation_errors.join(", ")}</p>}
            {c.state==="draft"&&<div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
              {job.provider!=="mock"&&<button type="button" className="button ghost" onClick={()=>{setEditing({...c});setEditOptions(c.options.join("\n"));setEditRubric(JSON.stringify(c.rubric,null,2));}}>Edit candidate</button>}
              <button type="button" className="button ghost" disabled={busy||!reasonOK(reason)} onClick={()=>void decideVariation(c,"reject")}>Reject</button>
              <button type="button" className="button" disabled={busy||!reasonOK(reason)||c.validation_errors.length>0||job.provider==="mock"} onClick={()=>void decideVariation(c,"approve")}>Approve private draft</button>
            </div>}
          </section>)}
        </article>)}
      </div>
    </section>}
    {editing&&<section className="card" style={{padding:22,marginTop:16}}>
      <h2>Correct generated practice variation</h2>
      <label>Question prompt<textarea className="field" rows={4} value={editing.prompt} onChange={e=>setEditing({...editing,prompt:e.target.value})}/></label>
      <label>Answer explanation<textarea className="field" rows={4} value={editing.explanation} onChange={e=>setEditing({...editing,explanation:e.target.value})}/></label>
      <label>Evidence quote from verified answer context<textarea className="field" rows={3} value={editing.evidence_quote} onChange={e=>setEditing({...editing,evidence_quote:e.target.value})}/></label>
      {editing.kind==="mcq"?<><label>Four answer options, one per line<textarea className="field" rows={5} value={editOptions} onChange={e=>setEditOptions(e.target.value)}/></label><label>Correct option (0–3)<input className="field" type="number" min={0} max={3} value={editing.correct_index??0} onChange={e=>setEditing({...editing,correct_index:Number(e.target.value)})}/></label></>:
        <label>Rubric JSON<textarea className="field" rows={5} value={editRubric} onChange={e=>setEditRubric(e.target.value)}/></label>}
      <button type="button" className="button" disabled={busy||!reasonOK(reason)} onClick={()=>void saveVariationEdit()}>Save correction</button>{" "}
      <button type="button" className="button ghost" onClick={()=>setEditing(null)}>Cancel</button>
    </section>}
    <p className="muted tiny" style={{marginTop:18}}>Security: original paper images stay behind staff authentication; no OCR question or mock AI variation is published automatically. Independent rights and academic verification still apply.</p>
  </StaffFrame>;
}
