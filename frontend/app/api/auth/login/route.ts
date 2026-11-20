import {NextRequest,NextResponse} from 'next/server';
import {backendFetch,backendError,validateOrigin} from '@/lib/backend';
import {setTokenCookies} from '@/lib/cookies';
export async function POST(request:NextRequest){
 if(!validateOrigin(request))return NextResponse.json({detail:'Origin not allowed'},{status:403});
 let input:unknown;try{input=await request.json()}catch{return NextResponse.json({detail:'Invalid request'},{status:400})}
 if(!input||typeof input!=='object'||!('email' in input)||!('password' in input)||typeof input.email!=='string'||typeof input.password!=='string'||input.email.length>254||input.password.length>4096)return NextResponse.json({detail:'Email and password required'},{status:400});
 try{const result=await backendFetch('/auth/login/',{method:'POST',body:JSON.stringify({email:input.email,password:input.password})});if(!result.ok)return NextResponse.json(await backendError(result),{status:result.status});const body=await result.json();if(typeof body.access!=='string'||typeof body.refresh!=='string')return NextResponse.json({detail:'Unexpected authentication response'},{status:502});const out=NextResponse.json({user:body.user??null},{headers:{'Cache-Control':'no-store'}});setTokenCookies(out,body.access,body.refresh);return out;}catch{return NextResponse.json({detail:'Authentication service unavailable'},{status:502})}
}
