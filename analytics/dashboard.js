const $ = id => document.getElementById(id);
const fmt = ms => ms == null ? '—' : ms < 1000 ? Math.round(ms) + ' ms' : (ms/1000).toFixed(1) + 's';
const difference = (current, previous) => previous === null || previous === 0 || current === null ? null : 100 * (current - previous) / previous;
const median = x => {const a=[...x].sort((a,b)=>a-b);return a.length ? (a[Math.floor((a.length-1)/2)]+a[Math.floor(a.length/2)])/2 : null;};
function draw(rows) {
 const completed=rows.filter(r=>r.completedAt);
 const returned=completed.filter(r=>r.returnLatencyMs != null);
 const latencies=returned.map(r=>r.returnLatencyMs);
 $('sessions').textContent=String(completed.length);
 $('wait').textContent=fmt(completed.reduce((a,r)=>a+r.durationMs,0));
 $('return').textContent=fmt(median(latencies));
 $('fast').textContent=returned.length ? Math.round(latencies.filter(x=>x<=10000).length/returned.length*100)+'%' : '—';
 $('coverage').textContent=returned.length+' of '+completed.length+' completions had an observed return';
 const treatment=returned.filter(r=>r.condition==='treatment');
 const control=returned.filter(r=>r.condition==='control');
 $('experiment').textContent=(treatment.length+control.length) ?
   'Experimental observed returns — video on: '+treatment.length+
   ' (median '+fmt(median(treatment.map(r=>r.returnLatencyMs)))+
   '), video off: '+control.length+' (median '+fmt(median(control.map(r=>r.returnLatencyMs)))+
   '). This is descriptive, not proof of an effect.' :
   'No A/B experiment observations yet. The experiment is optional.';

 const recentEnd=Date.now(), week=7*86400000;
 const current=completed.filter(r=>r.completedAt>=recentEnd-week && r.returnLatencyMs!=null).map(r=>r.returnLatencyMs);
 const previous=completed.filter(r=>r.completedAt>=recentEnd-2*week && r.completedAt<recentEnd-week && r.returnLatencyMs!=null).map(r=>r.returnLatencyMs);
 const currMed=median(current), prevMed=median(previous), change=difference(currMed,prevMed);
 $('week').textContent=change===null||current.length<5||previous.length<5?'Not enough observed returns in both weeks':(change>0?'+':'')+change.toFixed(1)+'% median return-time change vs previous 7 days ('+current.length+' vs '+previous.length+' observed returns)';

 const byDay=new Map();
 completed.forEach(r=>{const d=new Date(r.completedAt).toLocaleDateString();const v=byDay.get(d)||[];if(r.returnLatencyMs!=null)v.push(r.returnLatencyMs);byDay.set(d,v);});
 $('history').replaceChildren(...[...byDay].reverse().slice(0,30).map(([day,values])=>{
  const tr=document.createElement('tr');const a=document.createElement('td');const b=document.createElement('td');const c=document.createElement('td');
  a.textContent=day;b.textContent=String(values.length);c.textContent=fmt(median(values));tr.append(a,b,c);return tr;
 }));
 $('empty').hidden=rows.length>0;
}
async function refresh(){const {analyticsSessions=[]}=await chrome.storage.local.get('analyticsSessions');const days=Number($('period').value);const cutoff=Date.now()-days*86400000;draw(analyticsSessions.filter(r=>r.startedAt>=cutoff));}
$('period').addEventListener('change',refresh);
$('export').addEventListener('click',async()=>{
 const {analyticsSessions=[]}=await chrome.storage.local.get('analyticsSessions');
 const cols=['id','platform','startedAt','completedAt','durationMs','returnLatencyMs','videoEnabled','condition'];
 const escape=x=>'"'+String(x??'').replaceAll('"','""')+'"';
 const csv=[cols.join(','),...analyticsSessions.map(r=>cols.map(k=>escape(r[k])).join(','))].join('\n');
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));a.download='reels-personal-analytics.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),3000);
});
$('clear').addEventListener('click',async()=>{if(confirm('Delete all local productivity analytics?')){await chrome.storage.local.remove('analyticsSessions');refresh();}});
refresh();