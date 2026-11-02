// Prototype Cloudflare Worker. Collection is DISABLED unless ENABLE_INGESTION=true.
// Required secrets: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY.
// Clients must authenticate using Supabase Auth; never ship service-role key.
const reply=(message,status=200)=>new Response(JSON.stringify({message}),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
export default {
 async fetch(req,env){
  const endpoint=new URL(req.url).pathname;
  if(!['/ingest','/consent','/withdraw'].includes(endpoint))return reply('Not found',404);
  if(endpoint==='/withdraw' ? req.method!=='DELETE' : req.method!=='POST')return reply('Method not allowed',405);
  if(env.ENABLE_INGESTION!=='true')return reply('Collection disabled',503);
  if(!env.SUPABASE_URL||!env.SUPABASE_ANON_KEY||!env.SUPABASE_SERVICE_ROLE_KEY)return reply('Not configured',503);
  const token=(req.headers.get('Authorization')||'').replace(/^Bearer /,'');
  if(!token||token.length>4096)return reply('Unauthorized',401);
  const auth=await fetch(env.SUPABASE_URL+'/auth/v1/user',{headers:{apikey:env.SUPABASE_ANON_KEY,Authorization:'Bearer '+token}});
  if(!auth.ok)return reply('Unauthorized',401);
  const user=await auth.json();
  if(!user.id)return reply('Unauthorized',401);
  const dbHeaders={apikey:env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization:'Bearer '+env.SUPABASE_SERVICE_ROLE_KEY,'Content-Type':'application/json'};
  if(endpoint==='/withdraw'){
    const withdrawn=await fetch(env.SUPABASE_URL+'/rest/v1/research_consent?participant_id=eq.'+encodeURIComponent(user.id),
      {method:'PATCH',headers:{...dbHeaders,Prefer:'return=minimal'},body:JSON.stringify({withdrawn_at:new Date().toISOString()})});
    if(!withdrawn.ok)return reply('Withdrawal failed',502);
    const deleted=await fetch(env.SUPABASE_URL+'/rest/v1/research_events?participant_id=eq.'+encodeURIComponent(user.id),
      {method:'DELETE',headers:{...dbHeaders,Prefer:'return=minimal'}});
    return deleted.ok?reply('Consent withdrawn and events deleted'):reply('Withdrawal recorded; deletion needs retry',502);
  }
  if(endpoint==='/consent'){
    let body;try{body=await req.json()}catch{return reply('Invalid JSON',400)}
    if(body?.consent!==true||body?.policyVersion!=='v1')return reply('Explicit consent required',403);
    const stored=await fetch(env.SUPABASE_URL+'/rest/v1/research_consent?on_conflict=participant_id',
      {method:'POST',headers:{...dbHeaders,Prefer:'resolution=merge-duplicates,return=minimal'},
       body:JSON.stringify({participant_id:user.id,policy_version:'v1',consented_at:new Date().toISOString(),withdrawn_at:null})});
    return stored.ok?reply('Consent registered'):reply('Consent storage failed',502);
  }
  const permission=await fetch(env.SUPABASE_URL+'/rest/v1/research_consent?participant_id=eq.'+
    encodeURIComponent(user.id)+'&withdrawn_at=is.null&select=participant_id&limit=1',
    {headers:dbHeaders});
  if(!permission.ok)return reply('Consent unavailable',503);
  const active=await permission.json();
  if(!active.length)return reply('No active server-side consent',403);
  if(Number(req.headers.get('content-length')||0)>25000)return reply('Too large',413);
  let input;try{input=await req.json()}catch{return reply('Invalid JSON',400)}
  if(!input||input.consented!==true||!Array.isArray(input.events)||input.events.length>20)return reply('Consent required',403);
  const rows=[];
  for(const e of input.events){
   if(!e||!['treatment','control','observational'].includes(e.condition)||
     typeof e.ai_platform!=='string'||e.ai_platform.length>40||
     !Number.isInteger(e.response_duration_ms)||e.response_duration_ms<0||e.response_duration_ms>3600000||
     typeof e.returned!=='boolean'||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(e.recorded_day||''))
     return reply('Invalid event',400);
   const latency=e.return_latency_ms;
   if((latency!==null&&(!Number.isInteger(latency)||latency<0||latency>86400000))||
       e.returned!==(latency!==null))return reply('Invalid latency',400);
   rows.push({participant_id:user.id,session_id:e.session_id,ai_platform:e.ai_platform,
     video_source:e.video_source||null,condition:e.condition,
     response_duration_ms:e.response_duration_ms,playback_duration_ms:e.playback_duration_ms??null,
     return_latency_ms:latency,returned:e.returned,recorded_day:e.recorded_day});
  }
  const stored=await fetch(env.SUPABASE_URL+'/rest/v1/research_events',{method:'POST',
    headers:{apikey:env.SUPABASE_SERVICE_ROLE_KEY,Authorization:'Bearer '+env.SUPABASE_SERVICE_ROLE_KEY,'Content-Type':'application/json',Prefer:'return=minimal'},body:JSON.stringify(rows)});
  return stored.ok?reply('Accepted',202):reply('Storage error',502);
 }
};