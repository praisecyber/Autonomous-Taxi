const $ = id => document.getElementById(id);
let lastMessage = 0, latest = null, graph = null, sessionCsrf = '';
const xy = ([x,y]) => [80 + x*54, 290-y*44];
async function api(path, method='GET', body) {
  const headers = {'Content-Type':'application/json', 'X-Taxi-CSRF':sessionCsrf};
  if ($('token').value) headers.Authorization = `Bearer ${$('token').value}`;
  const response = await fetch(path, {method, headers, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
async function action(fn) {
  try { await fn(); $('feedback').textContent='Command accepted.'; await history(); }
  catch(e) { $('feedback').textContent=e.message; }
}
async function history() {
  const rows = await api('/api/trips');
  $('history').replaceChildren();
  for(const r of rows) {
    const tr=document.createElement('tr');
    for(const text of [r.id.slice(0,8),`${r.origin} → ${r.destination}`,r.status,new Date(r.created_at).toLocaleTimeString()]) {
      const td=document.createElement('td'); td.textContent=text; tr.append(td);
    }
    $('history').append(tr);
  }
  if(!rows.length) { const tr=document.createElement('tr'),td=document.createElement('td'); td.colSpan=4;td.textContent='No missions yet.';tr.append(td);$('history').append(tr); }
}
function draw(s) {
  const changed = latest?.state !== s.state;
  latest=s;lastMessage=Date.now();
  $('connection').textContent='● Live telemetry';
  $('state').textContent=s.state;
  $('reason').textContent=s.reason || (s.trip ? `${s.trip.origin} → ${s.trip.destination}` : 'Ready for a destination');
  $('speed').textContent=`${s.speed_mps.toFixed(2)} m/s`;
  $('age').textContent=`${s.telemetry.sensor_age_s.toFixed(2)} s`;
  $('current-stop').textContent=s.current_stop || 'En route';
  const [x,y]=xy([s.position.x,s.position.y]);$('car').setAttribute('transform',`translate(${x} ${y})`);
  if(graph) $('route-line').setAttribute('points',s.route.map(n=>xy(graph.points[n]).join(',')).join(' '));
  for(const name of ['obstacle','sensor_failed','link_failed']) $(name).checked=s.telemetry[name];
  $('start').disabled=s.state!=='READY' || !s.current_stop;
  $('rearm').disabled=!['FAULT','STOPPED','COMPLETE'].includes(s.state);
  $('reset').disabled=s.state==='ACTIVE';
  if(changed) history().catch(()=>{});
}
$('start').onclick=()=>action(()=>api('/api/trips','POST',{destination:$('destination').value}));
$('stop').onclick=()=>action(()=>api('/api/operator/stop','POST'));
$('rearm').onclick=()=>action(()=>api('/api/operator/rearm','POST'));
$('reset').onclick=()=>action(()=>api('/api/simulation/reset','POST'));
$('refresh').onclick=()=>action(history);
for(const name of ['obstacle','sensor_failed','link_failed']) $(name).onchange=()=>action(()=>api('/api/simulation/hazards','POST',Object.fromEntries(['obstacle','sensor_failed','link_failed'].map(n=>[n,$(n).checked]))));
function connect() {
  const ws=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws/telemetry`);
  ws.onmessage=e=>{try{draw(JSON.parse(e.data));}catch{ $('feedback').textContent='Invalid telemetry'; }};
  ws.onclose=()=>{ $('connection').textContent='○ Disconnected'; $('start').disabled=true;setTimeout(connect,1500); };
  ws.onerror=()=>ws.close();
}
setInterval(()=>{if(!lastMessage||Date.now()-lastMessage>1500){$('connection').textContent='○ Stale telemetry';$('start').disabled=true;$('speed').textContent='— (stale)';}},500);
fetch('/api/auth/me').then(r=>r.ok?r.json():null).then(data=>{
  if(data?.user) { sessionCsrf=data.csrf_token; $('token').value=''; }
  return api('/api/stops');
}).then(data=>{graph=data;
  $('destination').replaceChildren(...Object.entries(data.stops).map(([id,label])=>new Option(`${id} · ${label}`,id)));
  for(const label of document.querySelectorAll('[data-stop]')) {
    const id=label.dataset.stop; label.textContent=`${id} · ${data.stops[id]}`;
  }
  $('destination').value='B';connect();}).catch(e=>{$('feedback').textContent=e.message;});
