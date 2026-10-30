'use strict';
// Simulation transport contract. No commands or mutation requests are sent here.
(function(root) {
  const MAX_MESSAGE_CHARS = 65536;
  const states = new Set(['READY','ACTIVE','STOPPED','FAULT','COMPLETE']);
  const nodes = new Set(['A','J','B','C']);
  const stops = new Set(['A','B','C']);
  const tripStates = new Set(['ACTIVE','COMPLETED','CANCELLED','FAULTED','INTERRUPTED']);
  const record = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  function valid(s) {
    if (!record(s) || s.mode !== 'simulation' || !states.has(s.state) ||
        s.motor_output_enabled !== false || !finite(s.speed_mps) || s.speed_mps < 0 ||
        !record(s.position) || !finite(s.position.x) || !finite(s.position.y) ||
        !(s.current_stop === null || stops.has(s.current_stop)) ||
        !(s.reason === null || (typeof s.reason === 'string' && s.reason.length <= 256)) ||
        !Number.isSafeInteger(s.sequence) || s.sequence < 0 ||
        !Array.isArray(s.route) || s.route.length > nodes.size || s.route.some(n => !nodes.has(n))) return false;
    const t = s.telemetry;
    if (!record(t) || t.source !== 'simulated' ||
        !['obstacle','sensor_failed','link_failed'].every(key => typeof t[key] === 'boolean') ||
        ![t.sensor_age_s,t.link_age_s].every(value => finite(value) && value >= 0)) return false;
    if (s.trip !== null && (!record(s.trip) || typeof s.trip.id !== 'string' ||
        !s.trip.id.length || s.trip.id.length > 128 || !tripStates.has(s.trip.status) ||
        !stops.has(s.trip.origin) || !stops.has(s.trip.destination))) return false;
    return true;
  }
  function parse(message) {
    if (typeof message !== 'string' || message.length > MAX_MESSAGE_CHARS) throw new Error('Invalid telemetry');
    const snapshot = JSON.parse(message);
    if (!valid(snapshot)) throw new Error('Invalid telemetry');
    return snapshot;
  }
  function healthy(s) {
    return valid(s) && !s.telemetry.sensor_failed && !s.telemetry.link_failed &&
      s.telemetry.sensor_age_s <= .5 && s.telemetry.link_age_s <= .5;
  }
  function watch(onData,onConnection) {
    let socket=null, stopped=false, last=0, current='disconnected', retry;
    const emit=(kind,detail)=>{if(current!==kind || detail){current=kind;onConnection(kind,detail);}};
    onConnection('disconnected');
    function connect() {
      if(stopped)return;
      const ws=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws/telemetry`);socket=ws;
      ws.onmessage=event=>{
        if(ws!==socket || stopped)return;
        let snapshot;
        try { snapshot=parse(event.data); }
        catch { emit('stale','⚠ Invalid telemetry');return; }
        last=performance.now();emit('live');onData(snapshot);
      };
      ws.onclose=()=>{if(ws!==socket || stopped)return;emit('disconnected');retry=setTimeout(connect,1800);};
      ws.onerror=()=>ws.close();
    }
    const timer=setInterval(()=>{if(current==='live' && performance.now()-last>1500)emit('stale');},300);
    const offline=()=>{emit('disconnected');socket?.close();};window.addEventListener('offline',offline);
    const close=()=>{stopped=true;clearTimeout(retry);clearInterval(timer);socket?.close();window.removeEventListener('offline',offline);};
    window.addEventListener('pagehide',close,{once:true});
    window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
    connect();return close;
  }
  root.TaxiTelemetry = {valid,parse,healthy,watch,MAX_MESSAGE_CHARS};
})(globalThis);
