'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import StaffFrame from '@/components/staff/StaffFrame';
import {errorText,staffGet} from '@/lib/staff-workspace';

type Summary={permissions:Record<string,boolean>;counts:Record<string,number>};
const queues=[
 {key:'sources',count:'sources_pending',title:'Source excerpts',href:'/staff/sources',desc:'Manage document rights, references and approved excerpts'},
 {key:'tutor',count:'tutor_drafts',title:'Tutor drafts',href:'/staff/tutor',desc:'Review academic explanations and citations'},
 {key:'contributions',count:'contributions_pending',title:'Student contributions',href:'/staff/contributions',desc:'Distinct rights and academic approvals'},
 {key:'followups',count:'followups_pending',title:'Follow-up questions',href:'/staff/followups',desc:'Publish verified answers to student questions'},
];

export default function StaffHome(){
 const [data,setData]=useState<Summary|null>(null);
 const [error,setError]=useState('');
 useEffect(()=>{let canceled=false;staffGet<Summary>('/overview/').then(v=>{if(!canceled)setData(v);}).catch(e=>{if(!canceled)setError(errorText(e));});return ()=>{canceled=true;};},[]);
 return <StaffFrame title="Academic workspace" description="One place for NiCat's review queues. Permissions are checked again by Django on every action.">
  {error&&<p role="alert" className="card">{error}</p>}
  {!data&&!error&&<p role="status">Loading staff permissions and queues…</p>}
  {data&&<div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(230px,1fr))',gap:14}}>
   {queues.filter(q=>data.permissions[q.key]).map(q=><section className="card" key={q.key} style={{padding:20}}>
    <p className="muted tiny">Pending review</p><h2 style={{fontSize:30,margin:'7px 0'}}>{data.counts[q.count]??0}</h2>
    <h3>{q.title}</h3><p className="muted tiny">{q.desc}</p><Link href={q.href} className="button">Open queue</Link>
   </section>)}
  </div>}
  <section className="card" style={{marginTop:24,padding:20}}><h2>Safety rules</h2>
    <p className="muted">Staff decisions use the same audited Django services as the existing Admin actions. Academic publication remains separate from student submission and source-rights clearance.</p>
  </section>
 </StaffFrame>;
}
