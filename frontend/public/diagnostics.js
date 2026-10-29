'use strict';
let last=null;
function missing(kind,detail){
  Taxi.connection('connection',kind,detail);Taxi.text('diagnostic-state',kind==='stale'?'◷ Stale telemetry':'○ Disconnected');
  for(const id of ['sensor-validity','link-validity','diagnostic-source','diag-vehicle','diag-reason','diag-obstacle','diag-sensor','diag-link'])Taxi.text(id,'Unavailable');
  Taxi.text('sensor-age','No current valid sample');Taxi.text('link-age','No current valid sample');
  Taxi.message('diagnostic-notice',kind==='stale'?'⚠ Telemetry is stale or invalid. Current sensor and vehicle state are unconfirmed.':'○ Disconnected. Waiting for a valid snapshot; no device is assumed healthy.',true);
  Taxi.text('snapshot-status',last?'Last received data below is retained for inspection only. It is not live.':'No snapshot. This view is read-only.');
}
Taxi.watchTelemetry(s=>{
  last=s;const t=s.telemetry,[label]=Taxi.state(s.state), sensor=!t.sensor_failed&&t.sensor_age_s<=.5, link=!t.link_failed&&t.link_age_s<=.5;
  Taxi.connection('connection',sensor&&link?'live':'stale',sensor&&link?undefined:'⚠ Connected · Invalid inputs');
  Taxi.text('diagnostic-state',label);Taxi.text('sensor-validity',sensor?'✓ Valid simulated sample':'⚠ Invalid / stale');Taxi.text('link-validity',link?'✓ Valid simulated link':'⚠ Invalid / stale');
  Taxi.text('sensor-age',`Sample age ${t.sensor_age_s.toFixed(2)} s · Simulation limit 0.50 s`);Taxi.text('link-age',`Sample age ${t.link_age_s.toFixed(2)} s · Simulation limit 0.50 s`);
  Taxi.text('diagnostic-source','Simulated');Taxi.text('last-received',`Last received ${new Date().toLocaleTimeString()}`);
  Taxi.text('diag-vehicle',label);Taxi.text('diag-reason',s.reason?.replaceAll('_',' ') || 'No stop reason reported');Taxi.text('diag-obstacle',t.obstacle?'⚠ Asserted (simulated)':'Clear (simulated)');Taxi.text('diag-sensor',t.sensor_failed?'⚠ Frozen (simulated)':'Updating (simulated)');Taxi.text('diag-link',t.link_failed?'⚠ Lost (simulated)':'Updating (simulated)');
  Taxi.message('diagnostic-notice',sensor&&link?'● Receiving current simulated telemetry. Physical devices are unavailable.':'⚠ Receiving telemetry with invalid or stale simulated inputs. Do not treat these inputs as healthy.',!sensor||!link);
  Taxi.text('snapshot-status','Current simulation snapshot · Read-only.');Taxi.text('diagnostic-json',JSON.stringify(s,null,2));
},(kind,detail)=>{if(kind!=='live')missing(kind,detail);});
