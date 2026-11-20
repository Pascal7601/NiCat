import {NextRequest,NextResponse} from 'next/server';
import {backendFetch,validateOrigin} from '@/lib/backend';
import {clearTokenCookies,ACCESS_NAME,REFRESH_NAME} from '@/lib/cookies';
/** Best-effort server revocation, including the common expired-access-token case. */
export async function POST(request:NextRequest){
  if(!validateOrigin(request))return NextResponse.json({detail:'Origin not allowed'},{status:403});
  let refresh=request.cookies.get(REFRESH_NAME)?.value;
  let access=request.cookies.get(ACCESS_NAME)?.value;
  if(refresh){
    try{
      let result=access?await backendFetch('/auth/logout/',{method:'POST',body:JSON.stringify({refresh})},access):null;
      if(!result||result.status===401){
        // Rotation blacklists the old token; blacklist the new one immediately.
        const rotated=await backendFetch('/auth/refresh/',{method:'POST',body:JSON.stringify({refresh})});
        if(rotated.ok){const pair=await rotated.json();if(typeof pair.access==='string'&&typeof pair.refresh==='string'){
          access=pair.access;refresh=pair.refresh;
          result=await backendFetch('/auth/logout/',{method:'POST',body:JSON.stringify({refresh})},access);
        }}
      }
      void result;
    }catch{/* Clear all local tokens even if remote revocation is unavailable. */}
  }
  const out=new NextResponse(null,{status:204,headers:{'Cache-Control':'no-store'}});
  clearTokenCookies(out);return out;
}
