'use strict';
const $=id=>document.getElementById(id), map=Taxi.mountMap('passenger-map');
let user=null, csrf='', graph=null, snapshot=null, kind='disconnected', trips=[], selected=null, busy=false, refreshId=0;
const chosen=()=>$('destination-options').querySelector('input:checked')?.value;
function controls(){
  const ready=user?.role==='passenger' && kind==='live' && Taxi.healthy(snapshot) && snapshot.state==='READY' && snapshot.current_stop && chosen()!==snapshot.current_stop;
  $('book-trip').disabled=!ready || busy || !chosen();
  $('refresh-passenger').disabled=!user || user.role!=='passenger' || busy;
  $('cancel-trip').hidden=!(user?.role==='passenger' && selected?.status==='ACTIVE');$('cancel-trip').disabled=busy;
  if($('booking-availability'))Taxi.text('booking-availability',!snapshot || kind!=='live'?'Current vehicle state is unconfirmed. Booking is unavailable.':snapshot?.state==='READY'?'Vehicle ready at a named stop. Choose a different destination.':`${Taxi.state(snapshot.state)[0]} · A new trip needs a ready vehicle at a stop.`);
  for(const input of $('destination-options').querySelectorAll('input')){input.disabled=!!snapshot?.current_stop && input.value===snapshot.current_stop;const note=input.closest('label').querySelector('.stop-note');Taxi.text(note,input.disabled?'Current stop':'Campus destination');}
}
function identity(message){
  user=null;csrf='';trips=[];selected=null;++refreshId;
  Taxi.text($('passenger-access').querySelector('strong'),'Sign in to book a trip.');Taxi.text('passenger-identity',message || 'Your account keeps your trip records private.');
  const link=$('passenger-access').querySelector('a');link.href='/account?next=/passenger';link.textContent='Go to sign in →';
  Taxi.text('passenger-history','Sign in to see your records.');renderTrip();controls();
}
function renderHistory(){
  const box=$('passenger-history');box.replaceChildren();
  if(!trips.length){const p=document.createElement('p');p.className='empty-state';p.textContent='No trips yet. Your first request starts here.';box.append(p);return;}
  for(const trip of trips.slice(0,10)){
    const article=document.createElement('article');article.className='trip-record';const info=document.createElement('div'),title=document.createElement('strong'),date=document.createElement('p');title.textContent=`${trip.origin} → ${trip.destination}`;date.textContent=new Date(trip.created_at).toLocaleString();info.append(title,date);article.append(info,Taxi.badge(trip.status));box.append(article);
  }
}
async function refreshTrips(){
  if(user?.role!=='passenger')return;
  const generation=++refreshId;
  try{
    const rows=await TaxiApi.request('/api/trips');if(generation!==refreshId)return;
    trips=rows;selected=rows.find(t=>t.status==='ACTIVE') || rows[0] || null;renderHistory();renderTrip();controls();
  }catch(error){if(error.status===401)identity('Your session expired. Sign in again.');TaxiApi.showError(error,'passenger-feedback');}
}
function percent(s){
  if(!selected || s.trip?.id!==selected.id || !graph || !s.route?.length)return null;
  if(s.trip.status==='COMPLETED' && s.speed_mps===0)return 100;
  let total=0,best=Infinity,position=0;
  const p=[s.position.x,s.position.y];
  for(let i=1;i<s.route.length;i++){
    const a=graph.points[s.route[i-1]],b=graph.points[s.route[i]],dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);
    const t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(length*length || 1)));
    const distance=Math.hypot(p[0]-a[0]-dx*t,p[1]-a[1]-dy*t);
    if(distance<best){best=distance;position=total+t*length;}total+=length;
  }
  return total?Math.min(99,Math.max(0,Math.round(position/total*100))):0;
}
function renderTrip(){
  if(!selected){Taxi.text('trip-route','No trip selected');Taxi.text('trip-badge','No active trip');$('trip-badge').dataset.tone='muted';Taxi.text('trip-description','Your accepted request and progress will appear here.');$('trip-progress').value=0;Taxi.text('progress-copy','No current trip progress.');return;}
  const own=snapshot?.trip?.id===selected.id, status=own?snapshot.trip.status:selected.status;
  Taxi.text('trip-route',`${graph?.stops[selected.origin] || selected.origin} → ${graph?.stops[selected.destination] || selected.destination}`);
  const [label,tone]=Taxi.state(status);Taxi.text('trip-badge',label);$('trip-badge').dataset.tone=tone;
  if(kind!=='live'){
    Taxi.text('trip-description','Telemetry is unavailable. This is the last stored trip status, not live progress.');$('trip-progress').value=0;Taxi.text('progress-copy','Progress unavailable · Waiting for fresh telemetry.');
  }else{
    const progress=own?percent(snapshot):null;
    $('trip-progress').value=progress ?? 0;
    Taxi.text('progress-copy',progress===null?'Stored trip record · No matching current trip telemetry.':`${progress}% of simulated route · ${progress===100?'Arrival confirmed at zero simulated speed':'Position-based progress'}`);
    Taxi.text('trip-description',own && status==='COMPLETED' && snapshot.speed_mps===0?'Your simulated trip is complete. Arrival is confirmed for this trip.':status==='ACTIVE'?'Your request is active. Follow current simulated progress here.':status==='FAULTED'?'The trip faulted and stopped. An operator must investigate and explicitly rearm.':'This trip is terminal and remains in your stored history.');
  }
}
async function action(fn,success){busy=true;controls();Taxi.message('passenger-feedback','Sending your request…');try{await fn();Taxi.message('passenger-feedback',success);await refreshTrips();}catch(error){TaxiApi.showError(error,'passenger-feedback',$('passenger-booking'));if(error.status===401)identity('Your session expired. Sign in again.');}finally{busy=false;controls();}}
$('passenger-booking').onsubmit=event=>{event.preventDefault();if($('book-trip').disabled)return;action(async()=>{const result=await TaxiApi.request('/api/trips',{method:'POST',body:{destination:chosen()},csrf});selected=result;},'Your simulated trip was accepted.');};
$('cancel-trip').onclick=()=>action(()=>TaxiApi.request(`/api/trips/${selected.id}/cancel`,{method:'POST',csrf}),'Cancellation recorded for your trip. No physical stopping is implied.');
$('refresh-passenger').onclick=()=>action(async()=>{},'Your stored trips were refreshed.');
Taxi.watchTelemetry(s=>{
  const old=snapshot;snapshot=s;
  Taxi.connection('connection',Taxi.healthy(s)?'live':'stale',Taxi.healthy(s)?undefined:'⚠ Connected · Invalid samples');
  const [label,tone]=Taxi.state(s.state);Taxi.text('passenger-state',label);$('passenger-state').dataset.tone=tone;
  Taxi.text('passenger-stop',s.current_stop || 'Between stops');Taxi.text('passenger-speed',`${s.speed_mps.toFixed(2)} m/s`);Taxi.text('journey-source','Vehicle telemetry · Simulation');map.draw(s,graph);
  if(s.trip && selected?.id===s.trip.id)selected.status=s.trip.status;
  if(user && `${old?.trip?.id}:${old?.trip?.status}`!==`${s.trip?.id}:${s.trip?.status}`)refreshTrips();
  renderTrip();controls();
},(state,detail)=>{
  kind=state;Taxi.connection('connection',state,detail);
  if(state!=='live'){Taxi.text('passenger-state',state==='stale'?'◷ Stale telemetry':'○ Disconnected');$('passenger-state').dataset.tone='attention';for(const id of ['passenger-stop','passenger-speed'])Taxi.text(id,'Unavailable');Taxi.text('journey-source','Last known position · Not live');map.stale();renderTrip();}controls();
});
(async()=>{
  try{
    graph=await TaxiApi.request('/api/stops');map.labels(graph);const options=$('destination-options');options.replaceChildren();
    for(const [id,name] of Object.entries(graph.stops)){
      const label=document.createElement('label');label.className='destination-card';const input=document.createElement('input');input.type='radio';input.name='destination';input.value=id;input.required=true;input.checked=id==='B';
      const span=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');strong.textContent=`${id} · ${name}`;small.className='stop-note';small.textContent='Campus destination';span.append(strong,small);label.append(input,span);options.append(label);input.onchange=controls;
    }
    const data=await TaxiApi.request('/api/auth/me');user=data.user;csrf=data.csrf_token;
    if(user.must_change_password){identity('Change your temporary password on Account before booking.');return;}
    if(user.role!=='passenger'){identity('Use a passenger account to book and see your own trips.');return;}
    Taxi.text($('passenger-access').querySelector('strong'),`Passenger access · ${user.username}`);Taxi.text('passenger-identity','Your identity is applied automatically to every request.');const link=$('passenger-access').querySelector('a');link.href='/account';link.textContent='Manage account →';Taxi.message('passenger-feedback','Choose a destination when the simulated vehicle is ready.');await refreshTrips();controls();
  }catch(error){if(error.status===401)identity();else TaxiApi.showError(error,'passenger-feedback');}
})();
setInterval(()=>{if(user?.role==='passenger')refreshTrips();},5000);
