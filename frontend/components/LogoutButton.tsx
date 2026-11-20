'use client';
import {useRouter} from 'next/navigation';
import {useState} from 'react';
export default function LogoutButton(){const router=useRouter();const [busy,setBusy]=useState(false);return <button className="button ghost" style={{marginTop:18,width:'100%',color:'#182044'}} disabled={busy} onClick={async()=>{setBusy(true);try{await fetch('/api/auth/logout',{method:'POST',headers:{'Content-Type':'application/json'}});}finally{router.replace('/login');router.refresh();}}}>Log out</button>}
