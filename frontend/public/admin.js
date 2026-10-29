'use strict';
const $ = id => document.getElementById(id);
let csrf = '', currentUser = null, epoch = 0;
const pageSize = 25;
const offsets = {trips: 0, events: 0, users: 0};
const totals = {trips: 0, events: 0, users: 0};
const filters = {trips: {q: '', status: ''}, events: {q: '', event_kind: ''}};

function textCell(row, value) {
  const td = document.createElement('td'); td.textContent = String(value ?? ''); row.append(td); return td;
}
function empty(body, columns, message) {
  const row = document.createElement('tr'); textCell(row, message).colSpan = columns; body.append(row);
}
function details(row, record) {
  const td = textCell(row, ''), box = document.createElement('details');
  const title = document.createElement('summary'), pre = document.createElement('pre');
  title.textContent = 'View record'; pre.textContent = JSON.stringify(record, null, 2);
  box.append(title, pre); td.append(box);
}
function hideSession(message) {
  Taxi.connection('connection','disconnected','○ Administrator sign-in required');
  ++epoch; csrf = ''; currentUser = null; $('admin-content').hidden = true;
  $('access-form').hidden = false; $('load-records').disabled = true; $('clear-records').disabled = true;
  $('identity').textContent = 'Administrator sign-in required.'; $('records-feedback').textContent = message;
  for (const id of ['admin-trips','admin-events','users','reports']) $(id).replaceChildren();
  $('configuration').value = ''; $('new-password').value = ''; $('new-username').value = '';
  for (const key of Object.keys(offsets)) { offsets[key] = 0; totals[key] = 0; }
}
async function api(path, method='GET', body) {
  const generation=epoch;
  try {
    const data=await TaxiApi.request(path,{method,body,csrf});
    if(generation!==epoch)throw new Error('Session changed; retry after signing in.');
    return data;
  } catch(error) {
    if([401,403].includes(error.status) && currentUser)hideSession('Session expired or access denied. Sign in again.');
    throw error;
  }
}
function options(id, values, label) {
  const select = $(id), previous = select.value;
  select.replaceChildren(new Option(label, ''));
  for (const value of values) select.add(new Option(value, value));
  if (values.includes(previous)) select.value = previous;
}
function pager(kind, prefix) {
  $(prefix+'-prev').disabled = offsets[kind] === 0;
  $(prefix+'-next').disabled = offsets[kind] + pageSize >= totals[kind];
}
async function loadRecords(kind) {
  const prefix = kind === 'trips' ? 'trip' : 'event';
  const body = $(kind === 'trips' ? 'admin-trips' : 'admin-events');
  body.replaceChildren(); empty(body, kind === 'trips' ? 5 : 4, 'Loading records…');
  $(prefix+'-prev').disabled = true; $(prefix+'-next').disabled = true;
  try {
    const data = await api(`/api/admin/records/${kind}?` + new URLSearchParams({limit:pageSize, offset:offsets[kind], ...filters[kind]}));
    body.replaceChildren(); totals[kind] = data.total;
    for (const record of data.items) {
      const row = document.createElement('tr'); textCell(row, record.id);
      if (kind === 'trips') { textCell(row, `${record.origin} → ${record.destination}`); textCell(row, '').append(Taxi.badge(record.status)); }
      else textCell(row, record.kind);
      textCell(row, new Date(record.created_at || record.at).toLocaleString());
      details(row, record); body.append(row);
    }
    if (!data.items.length) empty(body, kind === 'trips' ? 5 : 4, 'No stored records match these filters.');
    $(prefix+'-count').textContent = `${data.items.length} shown · ${data.total} matching records · offset ${data.offset}`;
    pager(kind, prefix);
  } catch (error) { body.replaceChildren(); empty(body, kind === 'trips' ? 5 : 4, error.message); throw error; }
}
async function loadReports() {
  $('reports').replaceChildren();
  const data = await api('/api/admin/reports'); $('reports').replaceChildren();
  for (const [heading, counts] of [['Trips by status',data.trips_by_status], ['Events by type',data.events_by_kind]]) {
    const section = document.createElement('section'); section.className = 'summary-group';
    const title = document.createElement('h3'); title.textContent = heading; section.append(title);
    for (const [name, count] of Object.entries(counts)) { const line = document.createElement('p'); line.textContent = `${name}: ${count}`; section.append(line); }
    if (!Object.keys(counts).length) { const line = document.createElement('p'); line.textContent = 'No stored records.'; section.append(line); }
    $('reports').append(section);
  }
  options('trip-status', Object.keys(data.trips_by_status), 'All statuses');
  options('event-kind', Object.keys(data.events_by_kind), 'All types');
}
async function loadUsers() {
  $('users').replaceChildren();
  const data = await api('/api/admin/users?' + new URLSearchParams({limit:pageSize,offset:offsets.users}));
  $('users').replaceChildren(); totals.users = data.total;
  for (const user of data.items) {
    const row = document.createElement('tr'); textCell(row, user.username);
    const role = document.createElement('select'); role.setAttribute('aria-label', `Role for ${user.username}`);
    for (const value of ['passenger','operator','admin','diagnostics']) role.add(new Option(value, value)); role.value = user.role;
    textCell(row, '').append(role);
    const enabled = document.createElement('input'); enabled.type = 'checkbox'; enabled.checked = !!user.enabled;
    enabled.setAttribute('aria-label', `Enabled account ${user.username}`); textCell(row, '').append(enabled);
    const save = document.createElement('button'); save.className = 'compact'; save.textContent = 'Save access';
    if (user.id === currentUser.id) { save.disabled = true; role.disabled = true; enabled.disabled = true; save.textContent = 'Your account'; }
    save.onclick = () => run(async () => {
      await api(`/api/admin/users/${user.id}`, 'PATCH', {role:role.value,enabled:enabled.checked});
      $('users-feedback').textContent = 'Access updated; existing sessions revoked.'; await loadUsers();
    }, 'users-feedback', save);
    textCell(row, '').append(save); $('users').append(row);
  }
  $('users-count').textContent = `${data.items.length} shown · ${data.total} accounts · offset ${data.offset}`;
  pager('users','users');
}
function showConfiguration(data) {
  $('configuration').value=JSON.stringify(data,null,2);Taxi.text('configuration-version',`Version ${data.version}`);
  $('stop-labels').replaceChildren();
  for(const [id,name] of Object.entries(data.stops)) {
    const box=document.createElement('div'),label=document.createElement('label'),input=document.createElement('input');
    input.id=`stop-name-${id}`;input.name=`stop-${id}`;input.value=name;input.required=true;input.maxLength=80;label.htmlFor=input.id;label.textContent=`${id} · Stop name`;
    input.oninput=()=>{try{const config=JSON.parse($('configuration').value);config.stops[id]=input.value;$('configuration').value=JSON.stringify(config,null,2);}catch{Taxi.message('configuration-feedback','Reload configuration before editing stop names.',true);}};
    box.append(label,input);$('stop-labels').append(box);
  }
  const seen=new Set(), roads=[];for(const [from,nodes] of Object.entries(data.edges))for(const to of nodes){const key=[from,to].sort().join(' ↔ ');if(!seen.has(key)){seen.add(key);roads.push(key);}}
  Taxi.text('route-summary',`Mapped road segments: ${roads.join(' · ')}. Geometry remains fixed.`);
}
async function loadConfiguration(){showConfiguration(await api('/api/admin/configuration'));}
async function refresh() {
  $('records-feedback').textContent = 'Refreshing snapshots…';
  for (const id of ['admin-trips','admin-events','users','reports']) $(id).replaceChildren();
  // Sequential loads make session failures unambiguous and avoid stale partial responses.
  await loadReports(); await loadRecords('trips'); await loadRecords('events'); await loadUsers(); await loadConfiguration();
  Taxi.message('records-feedback',`Snapshot refreshed at ${new Date().toLocaleTimeString()}.`);
  Taxi.text('admin-freshness',`Stored snapshot refreshed at ${new Date().toLocaleTimeString()}. Records are not live telemetry.`);
  Taxi.connection('connection','live','✓ Stored snapshot refreshed');
}
async function run(fn,feedback='records-feedback',button=null) {
  if(button){button.disabled=true;button.setAttribute('aria-busy','true');}
  Taxi.message(feedback,'Working…');
  try{await fn();}catch(error){
    TaxiApi.showError(error,feedback,button?.form);
    if(error instanceof TaxiApi.ApiError && !error.status){Taxi.connection('connection','disconnected');Taxi.text('admin-freshness','Disconnected · Stored records are not current. Refresh before relying on this snapshot.');}
  }finally{if(button){button.disabled=!currentUser && button.id==='load-records';button.removeAttribute('aria-busy');}}
}
async function enterSession(data) {
  if(data.user.must_change_password){hideSession('Change your temporary password through Account before administering the service.');return;}
  if (data.user.role !== 'admin') { hideSession('This account does not have administrator permissions.'); return; }
  csrf = data.csrf_token; currentUser = data.user;
  $('identity').textContent = `Signed in as ${data.user.username} · administrator`;
  $('access-form').hidden = true; $('admin-content').hidden = false;
  $('clear-records').disabled = false; $('load-records').disabled = false;
  await refresh();
}
$('access-form').onsubmit = event => {
  event.preventDefault(); run(async () => {
    const password = $('password').value; $('password').value = '';
    const data = await api('/api/auth/login','POST',{username:$('username').value,password});
    await enterSession(data);
  }, 'records-feedback', $('sign-in'));
};
$('clear-records').onclick = () => run(async () => { await api('/api/auth/logout','POST'); hideSession('Signed out.'); });
$('load-records').onclick = () => run(refresh,'records-feedback',$('load-records'));
for (const [kind,prefix] of [['trips','trip'],['events','event']]) {
  $(prefix+'-filter').onsubmit = event => {
    event.preventDefault(); offsets[kind] = 0;
    filters[kind] = kind === 'trips' ? {q:$('trip-search').value,status:$('trip-status').value} : {q:$('event-search').value,event_kind:$('event-kind').value};
    run(() => loadRecords(kind),'records-feedback',event.submitter);
  };
}
for (const [kind,prefix] of [['trips','trip'],['events','event'],['users','users']]) {
  for (const [direction,delta] of [['prev',-pageSize],['next',pageSize]]) $(prefix+'-'+direction).onclick = () => run(async () => {
    offsets[kind] = Math.max(0, offsets[kind]+delta);
    if (kind === 'users') await loadUsers(); else await loadRecords(kind);
  });
}
$('new-user-form').onsubmit = event => {
  event.preventDefault(); const button = event.submitter;
  run(async () => {
    const password = $('new-password').value; $('new-password').value = '';
    await api('/api/admin/users','POST',{username:$('new-username').value,password,role:$('new-role').value,require_password_change:$('new-force-password').checked});
    $('new-user-form').reset(); $('users-feedback').textContent = 'Account created.'; offsets.users = 0; await loadUsers();
  }, 'users-feedback', button);
};
$('configuration-form').onsubmit = event => {
  event.preventDefault(); run(async () => {
    let configuration;
    try { configuration = JSON.parse($('configuration').value); } catch { throw new Error('Enter valid JSON.'); }
    const saved = await api('/api/admin/configuration','PUT',configuration);
    showConfiguration(saved);
    $('configuration-feedback').textContent = `Saved version ${saved.version}. Operators should reload their stop lists.`;
  },'configuration-feedback',event.submitter);
};
$('reload-configuration').onclick = () => run(loadConfiguration,'configuration-feedback');
(async()=>{try{await enterSession(await api('/api/auth/me'));}catch(error){hideSession(error.status===401?'Sign in to load records.':error.message);if(error.status!==401)Taxi.message('records-feedback',error.message,true);}})();
