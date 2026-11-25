'use client';
import Link from 'next/link';
import type {ReactNode} from 'react';

const links = [
  {href:'/staff',label:'Overview'},
  {href:'/staff/sources',label:'Source library'},
  {href:'/staff/tutor',label:'Tutor explanations'},
  {href:'/staff/contributions',label:'Student contributions'},
  {href:'/staff/followups',label:'Follow-up reviews'},
  {href:'/review',label:'Written-answer marking'},
];

export default function StaffFrame({title,description,children}:{title:string;description:string;children:ReactNode}){
  return <main className="container" style={{maxWidth:1150,margin:'0 auto',padding:'24px 16px 72px'}}>
    <header style={{marginBottom:22}}>
      <p className="muted tiny">NiCat · Academic staff workspace</p>
      <h1>{title}</h1>
      <p className="muted">{description}</p>
    </header>
    <nav aria-label="Staff workspace" style={{display:'flex',flexWrap:'wrap',gap:9,marginBottom:22}}>
      {links.map(link=><Link key={link.href} href={link.href} className="button ghost" style={{textDecoration:'none'}}>{link.label}</Link>)}
    </nav>
    {children}
  </main>;
}
