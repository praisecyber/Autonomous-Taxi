'use strict';
window.Taxi = (() => {
  const screen = document.body.dataset.screen || 'operator';
  const screens = [['passenger','/passenger','P','Passenger'],['operator','/operator','O','Operator'],['admin','/admin','A','Admin'],['diagnostics','/diagnostics','D','Diagnostics'],['account','/account','○','Account']];
  const shell = document.createElement('aside'); shell.className = 'sidebar';shell.setAttribute('aria-label','Workspace navigation');
  shell.innerHTML = '<a class="brand" href="/passenger"><span class="brand-icon" aria-hidden="true">CT</span><span>CAMPUS TAXI<small>CAMPUS MOBILITY</small></span></a><div><p class="nav-label">WORKSPACE</p><nav class="main-nav" aria-label="Main navigation"></nav></div><div class="sidebar-bottom"><span class="pill">SIMULATION ONLY</span><p>One vehicle. A shared campus.<br>Physical outputs disabled.</p><a href="/docs">Swagger API docs →</a></div>';
  const nav = shell.querySelector('nav');
  for (const [id,path,icon,name] of screens) {
    const a = document.createElement('a'); a.href = path; a.className = 'nav-link';
    if (id === screen) a.setAttribute('aria-current','page');
    const span = document.createElement('span'); span.className = 'nav-icon'; span.setAttribute('aria-hidden','true'); span.textContent = icon;
    a.append(span, document.createTextNode(name)); nav.append(a);
  }
  const skip = document.createElement('a'); skip.href = '#main'; skip.className = 'skip-link'; skip.textContent = 'Skip to main content';
  document.body.prepend(skip, shell);
  function text(id,value) { const element = typeof id === 'string' ? document.getElementById(id) : id; if (element && element.textContent !== String(value)) element.textContent = value; }
  function message(id,value,error=false) { const el = typeof id === 'string' ? document.getElementById(id) : id; if (!el) return; text(el,value); el.dataset.error=String(error); el.setAttribute('role',error?'alert':'status'); }
  function state(code) {
    return ({READY:['● Ready','ready'],ACTIVE:['→ Active','ready'],STOPPED:['■ Stopped','attention'],FAULT:['⚠ Fault','attention'],FAULTED:['⚠ Fault · FAULTED','attention'],CANCELLED:['■ Stopped · CANCELLED','attention'],INTERRUPTED:['■ Stopped · INTERRUPTED','attention'],COMPLETED:['✓ Arrived · COMPLETED','ready'],COMPLETE:['✓ Stopped · Arrived','ready']})[code] || ['○ Disconnected','attention'];
  }
  function badge(code) { const [label,tone]=state(code); const span=document.createElement('span');span.className='badge';span.dataset.tone=tone;span.textContent=label;return span; }
  function connection(id,kind,detail) { const el=typeof id==='string'?document.getElementById(id):id; if(!el)return; el.dataset.kind=kind; text(el,detail || ({live:'● Connected · Simulation',stale:'◷ Stale telemetry',disconnected:'○ Disconnected'})[kind]); }
  const healthy = s => TaxiTelemetry.healthy(s);
  const watchTelemetry = (onData,onConnection) => TaxiTelemetry.watch(onData,onConnection);
  function mountMap(id) {
    const el=document.getElementById(id);el.classList.add('route-map');el.dataset.stale='true';
    el.innerHTML='<svg viewBox="0 0 700 390" role="img" aria-label="Simulated campus route: Engineering, Library and Student Centre"><defs><pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path class="map-grid" d="M30 0H0V30" fill="none"/></pattern></defs><rect width="700" height="390" fill="url(#grid)"/><path class="map-road" d="M80 290H620 M350 290V70"/><path class="map-center" d="M80 290H620 M350 290V70"/><polyline class="route-line" points=""/><g><circle class="map-stop" cx="80" cy="290" r="11"/><circle class="map-stop" cx="620" cy="290" r="11"/><circle class="map-stop" cx="350" cy="70" r="11"/></g><g><text class="map-label" data-stop="A" x="80" y="335">A · Engineering</text><text class="map-label" data-stop="B" x="620" y="335">B · Library</text><text class="map-label" data-stop="C" x="350" y="40">C · Student Centre</text></g><g class="vehicle-marker" transform="translate(80 290)" visibility="hidden"><circle class="map-car" r="25" opacity=".12"/><rect class="map-car" x="-13" y="-9" width="26" height="18" rx="5"/><path class="map-direction" d="M4 -4L9 0 4 4"/></g></svg>';
    const legend=document.createElement('div');legend.className='map-legend';el.append(legend);
    return {labels(graph){for(const label of el.querySelectorAll('[data-stop]'))text(label,`${label.dataset.stop} · ${graph.stops[label.dataset.stop]}`);legend.replaceChildren();for(const [id,name] of Object.entries(graph.stops)){const item=document.createElement('span');item.textContent=`${id} · ${name}`;legend.append(item);}},draw(s,graph){const xy=([x,y])=>[80+x*54,290-y*44];el.dataset.stale='false';const car=el.querySelector('.vehicle-marker');car.setAttribute('visibility','visible');car.setAttribute('transform',`translate(${xy([s.position.x,s.position.y]).join(' ')})`);if(graph)el.querySelector('.route-line').setAttribute('points',s.route.map(n=>xy(graph.points[n]).join(',')).join(' '));},stale(){el.dataset.stale='true';}};
  }
  for(const region of document.querySelectorAll('.table-wrap')) {
    const name=region.querySelector('caption')?.textContent || region.closest('section')?.querySelector('h2')?.textContent || 'Stored records';
    region.setAttribute('aria-label',`${name} table`);
  }
  document.addEventListener('invalid',event=>{
    const input=event.target;if(!input.form)return;input.setAttribute('aria-invalid','true');
    const feedback=input.form.dataset.feedback;if(feedback)message(feedback,input.validationMessage,true);
  },true);
  document.addEventListener('input',event=>{event.target.removeAttribute('aria-invalid');});
  return {text,message,state,badge,connection,healthy,watchTelemetry,mountMap};
})();
