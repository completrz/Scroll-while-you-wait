// Prototype Cloudflare Worker. Collection is DISABLED unless ENABLE_INGESTION=true.
// Required secrets: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY.
// Clients must authenticate using Supabase Auth; never ship service-role key.
const reply=(message,status=200)=>new Response(JSON.stringify({message}),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
export default {
 async fetch(req,env){
  if(req.method!=='POST'||new URL(req.url).pathname!=='/ingest')return reply('Not found',404);
  if(env.ENABLE_INGESTION!=='true')return reply('Collection disabled',503);
  if(!env.SUPABASE_URL||!env.SUPABASE_ANON_KEY||!env.SUPABASE_SERVICE_ROLE_KEY)return reply('Not configured',503);
  const token=(req.headers.get('Authorization')||'').replace(/^Bearer /,'');
  if(!token||token.length>4096)return reply('Unauthorized',401);
  const auth=await fetch(env.SUPABASE_URL+'/auth/v1/user',{headers:{apikey:env.SUPABASE_ANON_KEY,Authorization:'Bearer '+token}});
  if(!auth.ok)return reply('Unauthorized',401);
  const user=await auth.json();
  if(!user.id)return reply('Unauthorized',401);
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