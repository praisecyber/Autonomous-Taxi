'use strict';
const $=id=>document.getElementById(id), map=Taxi.mountMap('route-map');
let graph=null, latest=null, kind='disconnected', principal=null, csrf='', token='', busy=false, historyKey='';
function allowed(){return principal?.role==='operator';}
function controls(){
  const connected=kind==='live', fresh=connected && Taxi.healthy(latest), can=allowed()&&!busy;
  $('destination').disabled=!graph || !can || !connected;
  $('start').disabled=!(can && fresh && latest.state==='READY' && latest.current_stop && $('destination').value!==latest.current_stop);
  $('rearm').disabled=!(can && fresh && ['FAULT','STOPPED','COMPLETE'].includes(latest.state));
  $('reset').disabled=!(can && fresh && latest.state!=='ACTIVE' && !latest.telemetry.obstacle);
  $('stop').disabled=!can;$('stop-phone').disabled=!can;
  for(const id of ['obstacle','sensor_failed','link_failed'])$(id).disabled=!can || !connected;
  $('refresh').disabled=!principal || busy;
}
async function api(path,method='GET',body){return TaxiApi.request(path,{method,body,csrf,token});}
async function history(){
  if(!principal)return;
  const rows=await api('/api/trips');$('history').replaceChildren();
  for(const r of rows.slice(0,10)){const tr=document.createElement('tr');for(const value of [r.id.length>14?r.id.slice(0,8):r.id,`${r.origin} → ${r.destination}`,r.status,new Date(r.created_at).toLocaleString()]){const td=document.createElement('td');if(value===r.status)td.append(Taxi.badge(r.status));else td.textContent=value;tr.append(td);}$('history').append(tr);}
  if(!rows.length){const tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=4;td.textContent='No stored missions yet.';tr.append(td);$('history').append(tr);}
  Taxi.text('history-note',`Showing ${Math.min(10,rows.length)} of ${rows.length} loaded records · ${new Date().toLocaleTimeString()}.`);
}
async function action(fn,success){
  busy=true;controls();Taxi.message('feedback','Sending request…');
  try{await fn();Taxi.message('feedback',success+(kind==='live'?'':' Telemetry is disconnected; verify the server state.'));await history();}
  catch(error){TaxiApi.showError(error,'feedback');if([401,403].includes(error.status)){principal=null;Taxi.text('access-note','Operator sign-in required. Use Account to sign in again.');}}
  finally{busy=false;controls();}
}
function draw(s){
  latest=s;const [label,tone]=Taxi.state(s.state);Taxi.text('state',label);$('state').dataset.code=s.state;$('state').className=tone==='ready'?'primary-text':'highlight-text';
  Taxi.text('reason',s.reason?.replaceAll('_',' ') || (Taxi.healthy(s)?'Fresh simulated inputs':'Inputs invalid; commands restricted'));
  Taxi.connection('connection',Taxi.healthy(s)?'live':'stale',Taxi.healthy(s)?undefined:'⚠ Connected · Invalid samples');
  Taxi.text('speed',`${s.speed_mps.toFixed(2)} m/s`);Taxi.text('age',`${s.telemetry.sensor_age_s.toFixed(2)} s`);Taxi.text('current-stop',s.current_stop?`${s.current_stop} · ${graph?.stops[s.current_stop] || 'Stop'}`:'Between stops');
  Taxi.text('map-status','Simulated metres · Current snapshot');map.draw(s,graph);
  for(const id of ['obstacle','sensor_failed','link_failed'])$(id).checked=s.telemetry[id];
  const key=`${s.state}:${s.trip?.id}`;if(key!==historyKey && principal){historyKey=key;history().catch(error=>Taxi.message('history-note',error.message,true));}
  controls();
}
Taxi.watchTelemetry(draw,(state,detail)=>{
  kind=state;Taxi.connection('connection',state,detail);
  if(state!=='live'){Taxi.text('state',state==='stale'?'◷ Stale telemetry':'○ Disconnected');$('state').dataset.code=state.toUpperCase();$('state').className='highlight-text';Taxi.text('reason','Current vehicle state is unconfirmed.');for(const id of ['speed','age','current-stop'])Taxi.text(id,'Unavailable');Taxi.text('map-status','Last known position · Not live');map.stale();}
  controls();
});
$('start').onclick=()=>action(()=>api('/api/operator/start','POST',{destination:$('destination').value}),'Simulated trip accepted.');
$('stop').onclick=()=>action(()=>api('/api/operator/stop','POST'),'Simulation stop recorded. This is not a physical emergency stop.');
$('stop-phone').onclick=()=>$('stop').onclick();
$('rearm').onclick=()=>action(()=>api('/api/operator/rearm','POST'),'Explicit rearm accepted.');
$('reset').onclick=()=>action(()=>api('/api/simulation/reset','POST'),'Simulator reset to A.');
$('refresh').onclick=()=>action(async()=>{},'Records refreshed.');
$('destination').onchange=controls;
for(const id of ['obstacle','sensor_failed','link_failed'])$(id).onchange=()=>action(()=>api('/api/simulation/hazards','POST',Object.fromEntries(['obstacle','sensor_failed','link_failed'].map(n=>[n,$(n).checked]))),'Simulated input updated. Faults remain latched until explicit rearm.');
async function authorize(demo=false){
  try{
    const data=await TaxiApi.request('/api/auth/me',demo?{token:$('token').value}:{});principal=data.user;csrf=data.csrf_token;token=demo?$('token').value:'';if(!demo)$('token').value='';
    if(principal.must_change_password){principal=null;token='';$('token').value='';Taxi.text('access-note','Change your temporary password through Account before using operator controls.');controls();return;}
    Taxi.text('access-note',allowed()?`Authorized operator · ${principal.username}`:`${principal.role} account · Operator commands unavailable.`);
    Taxi.message('feedback',allowed()?'Ready for an authorized command when telemetry is fresh.':'Use an operator account for mission controls.');await history();
  }catch(error){principal=null;token='';Taxi.text('access-note','Sign in through Account, or use an enabled local demo token.');if(demo)TaxiApi.showError(error,'feedback');}
  controls();
}
$('token').oninput=()=>{principal=null;token='';Taxi.text('access-note','Select Use demo token to verify access.');controls();};
$('use-token').onclick=()=>authorize(true);
(async()=>{
  try{graph=await TaxiApi.request('/api/stops');$('destination').replaceChildren(...Object.entries(graph.stops).map(([id,label])=>new Option(`${id} · ${label}`,id)));$('destination').value='B';map.labels(graph);await authorize();if(!principal && $('token').value)await authorize(true);controls();}
  catch(error){TaxiApi.showError(error,'feedback');Taxi.text('access-note','Backend unavailable. Reload when connected.');}
})();
