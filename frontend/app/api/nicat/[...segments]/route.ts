/** Same-origin browser-for-frontend; never send JWTs to browser JavaScript. */
import {NextRequest,NextResponse} from 'next/server';
import {ACCESS_NAME,REFRESH_NAME,clearTokenCookies,setTokenCookies} from '@/lib/cookies';
import {backendFetch,validateOrigin,isUUID} from '@/lib/backend';
import {permitted,segmentPath} from '@/lib/route-policy.mjs';
const NO_STORE={'Cache-Control':'private, no-store, max-age=0','Vary':'Cookie'};
interface Params{params:Promise<{segments:string[]}>}
async function proxy(request:NextRequest,ctx:Params){const {segments}=await ctx.params;const method=request.method;const path=segmentPath(segments);
 if(!permitted(method,path))return NextResponse.json({detail:'Route or method not allowed'},{status:404,headers:NO_STORE});
 if(method!=='GET'&&!validateOrigin(request))return NextResponse.json({detail:'Origin not allowed'},{status:403,headers:NO_STORE});
 if(request.nextUrl.search&&path!=='/exams/')return NextResponse.json({detail:'Query parameters are not supported here'},{status:400,headers:NO_STORE});
 const query=request.nextUrl.searchParams;let suffix='';if(path==='/exams/'&&query.size){if(query.size!==1||!query.has('unit_id')||!isUUID(query.get('unit_id')??''))return NextResponse.json({detail:'Invalid exam filter'},{status:400,headers:NO_STORE});suffix='?unit_id='+encodeURIComponent(query.get('unit_id')??'')}
 const access=request.cookies.get(ACCESS_NAME)?.value;const refresh=request.cookies.get(REFRESH_NAME)?.value;
 if(!access&&!refresh)return NextResponse.json({detail:'Sign in required'},{status:401,headers:NO_STORE});
 let body: string|undefined;
 if(method==='POST'||method==='PUT'){body=await request.text();if(body.length>22000)return NextResponse.json({detail:'Request too large'},{status:413,headers:NO_STORE})}
 async function forward(token:string|undefined){return backendFetch(path+suffix,{method,body},token)}
 try{
  let response=access?await forward(access):null;let rotated:{access:string,refresh?:string}|null=null;
  if((!response||response.status===401)&&refresh){const renewal=await backendFetch('/auth/refresh/',{method:'POST',body:JSON.stringify({refresh})});if(renewal.ok){const tokens=await renewal.json();if(typeof tokens.access==='string'&&typeof tokens.refresh==='string'){rotated={access:tokens.access,refresh:tokens.refresh};response=await forward(rotated.access)}}}
  if(!response||response.status===401){const out=NextResponse.json({detail:'Session expired. Sign in again.'},{status:401,headers:NO_STORE});clearTokenCookies(out);return out}
  const value=response.status===204?null:await response.json().catch(()=>null);
  const out=value===null?new NextResponse(null,{status:response.status,headers:NO_STORE}):NextResponse.json(value,{status:response.status,headers:NO_STORE});
  if(rotated)setTokenCookies(out,rotated.access,rotated.refresh);
  return out;
 }catch{return NextResponse.json({detail:'NiCat API is temporarily unavailable'},{status:502,headers:NO_STORE})}
}
export const GET=proxy;export const POST=proxy;export const PUT=proxy;
