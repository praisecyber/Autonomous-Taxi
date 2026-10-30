import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/telemetry.js',import.meta.url),'utf8');
const snapshot=()=>({mode:'simulation',state:'READY',reason:null,position:{x:0,y:0},
  current_stop:'A',speed_mps:0,trip:null,route:[],sequence:0,motor_output_enabled:false,
  telemetry:{source:'simulated',obstacle:false,sensor_age_s:0,link_age_s:0,sensor_failed:false,link_failed:false}});
function harness(){
  let now=0;const sockets=[], intervals=new Map(),timeouts=new Map(),listeners=new Map();let id=0;
  class Socket {
    constructor(url){this.url=url;sockets.push(this);}
    close(){this.onclose?.();}
    message(value){this.onmessage({data:typeof value==='string'?value:JSON.stringify(value)});}
    send(){throw new Error('Read-only watcher must not send commands');}
  }
  const context={WebSocket:Socket,performance:{now:()=>now},location:{protocol:'https:',host:'pc.test:8443',reload(){}},
    setInterval:fn=>{intervals.set(++id,fn);return id;},clearInterval:i=>intervals.delete(i),
    setTimeout:fn=>{timeouts.set(++id,fn);return id;},clearTimeout:i=>timeouts.delete(i),
    window:{addEventListener:(name,fn)=>listeners.set(name,fn),removeEventListener:name=>listeners.delete(name)}};
  vm.createContext(context);vm.runInContext(source,context);
  return {api:context.TaxiTelemetry,sockets,listeners,intervals,timeouts,
    advance(ms){now+=ms;for(const fn of intervals.values())fn();},
    reconnect(){const pending=[...timeouts.values()];timeouts.clear();for(const fn of pending)fn();}};
}
test('strict simulation data keeps missing and malformed fields from appearing healthy',()=>{
  const {api}=harness();assert.equal(api.valid(snapshot()),true);assert.equal(api.healthy(snapshot()),true);
  for(const change of [s=>delete s.telemetry.sensor_failed,s=>s.telemetry.link_failed='false',
    s=>s.telemetry.obstacle=null,s=>s.speed_mps=-1,s=>s.position.x=Infinity,
    s=>s.motor_output_enabled=true,s=>s.telemetry.source='device',s=>s.route=['UNKNOWN'],
    s=>s.telemetry.sensor_age_s=-1,s=>s.sequence=1.2,s=>s.trip={id:'trip',status:'ACTIVE'},
    s=>s.current_stop='UNKNOWN']){
    const s=snapshot();change(s);assert.equal(api.valid(s),false);assert.equal(api.healthy(s),false);
  }
  assert.equal(api.healthy(null),false);
});
test('parser rejects oversized, nontext and invalid JSON messages',()=>{
  const {api}=harness();
  for(const data of [null,{},'[]','not json',' '.repeat(api.MAX_MESSAGE_CHARS+1)]) assert.throws(()=>api.parse(data));
  assert.equal(api.parse(JSON.stringify(snapshot())).state,'READY');
});
test('reported stale or failed samples remain invalid with fresh transport',()=>{
  const {api}=harness();
  for(const change of [s=>s.telemetry.sensor_age_s=.51,s=>s.telemetry.link_age_s=.51,
    s=>s.telemetry.sensor_failed=true,s=>s.telemetry.link_failed=true]){
    const s=snapshot();change(s);assert.equal(api.valid(s),true);assert.equal(api.healthy(s),false);
  }
});
test('silence and malformed messages invalidate live state until a valid snapshot',()=>{
  const h=harness(),received=[],states=[];h.api.watch(s=>received.push(s),kind=>states.push(kind));
  assert.equal(h.sockets[0].url,'wss://pc.test:8443/ws/telemetry');
  h.sockets[0].message(snapshot());assert.equal(states.at(-1),'live');
  h.advance(1600);assert.equal(states.at(-1),'stale');
  h.sockets[0].message('broken');assert.equal(received.length,1);assert.equal(states.at(-1),'stale');
  h.sockets[0].message(snapshot());assert.equal(states.at(-1),'live');
});
test('reconnect waits for valid data and ignores messages from the old socket',()=>{
  const h=harness(),received=[],states=[];const stop=h.api.watch(s=>received.push(s),kind=>states.push(kind));
  const fault=snapshot();fault.state='FAULT';fault.reason='sensor_stale';
  h.sockets[0].message(fault);h.sockets[0].close();assert.equal(states.at(-1),'disconnected');
  h.reconnect();assert.equal(states.at(-1),'disconnected');assert.equal(h.sockets.length,2);
  h.sockets[0].message(snapshot());assert.equal(received.length,1);
  h.sockets[1].message(fault);assert.equal(states.at(-1),'live');assert.equal(received.at(-1).state,'FAULT');
  stop();assert.equal(h.intervals.size,0);assert.equal(h.timeouts.size,0);
  h.sockets[1].message(snapshot());assert.equal(received.length,2);
});
