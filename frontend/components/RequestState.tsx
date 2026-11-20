'use client';
import {useEffect,useState} from 'react';
import {clientRequest} from '@/lib/client';
export function useRequest<T>(path:string|null,preview?:T){const [data,setData]=useState<T|null>(preview??null);const [error,setError]=useState<string|null>(null);const [loading,setLoading]=useState(preview===undefined);useEffect(()=>{if(path===null){setLoading(false);return;}if(preview!==undefined){setData(preview);setLoading(false);return;}let current=true;setLoading(true);clientRequest<T>(path).then(v=>{if(current){setData(v);setError(null)}}).catch((e:unknown)=>{if(current)setError(e instanceof Error?e.message:'Request failed')}).finally(()=>{if(current)setLoading(false)});return()=>{current=false}},[path,preview!==undefined]);return {data,error,loading,setData}}
export function RequestError({message}:{message:string|null}){return message?<div role="alert" className="error">{message}</div>:null}
