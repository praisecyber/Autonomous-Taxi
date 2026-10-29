'use strict';
const $ = id => document.getElementById(id);
let csrf = '', user = null, version = 0;
function reset(message) {
  ++version; user = null; csrf = '';
  $('account-identity').textContent = 'Sign in'; $('login-form').hidden = false;
  for (const id of ['logout','password-panel','passenger-panel']) $(id).hidden = true;
  $('my-trips').replaceChildren(); $('feedback').textContent = message;
  $('password-form').reset();
}
async function api(path, method='GET', body) {
  const generation = version;
  const r = await fetch(path,{method,credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json','X-Taxi-CSRF':csrf},
    ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  if (generation !== version) throw new Error('Session changed.');
  const data = r.status === 204 ? null : await r.json();
  if (generation !== version) throw new Error('Session changed.');
  if (!r.ok) {
    if (r.status === 401 && user) reset('Session expired.');
    throw new Error(typeof data?.detail === 'string' ? data.detail : `Request rejected (HTTP ${r.status}).`);
  }
  return data;
}
async function action(fn, button) {
  if (button) button.disabled = true;
  try { await fn(); } catch (e) { $('feedback').textContent = e.message; }
  finally { if (button) button.disabled = false; }
}
async function myTrips() {
  const trips = await api('/api/trips'); $('my-trips').replaceChildren();
  for (const trip of trips) {
    const row = document.createElement('tr');
    for (const value of [trip.id,`${trip.origin} → ${trip.destination}`,trip.status]) {
      const td = document.createElement('td'); td.textContent = value; row.append(td);
    }
    const td = document.createElement('td');
    if (trip.status === 'ACTIVE') {
      const cancel = document.createElement('button'); cancel.textContent = 'Cancel my trip'; cancel.className = 'compact';
      cancel.onclick = () => action(async () => {
        await api(`/api/trips/${trip.id}/cancel`,'POST'); $('feedback').textContent = 'Simulation cancellation recorded.'; await myTrips();
      },cancel); td.append(cancel);
    }
    row.append(td); $('my-trips').append(row);
  }
  if (!trips.length) { const row = document.createElement('tr'),td = document.createElement('td'); td.colSpan=4;td.textContent='No trips belong to this account.';row.append(td);$('my-trips').append(row); }
}
async function signedIn(data) {
  user = data.user; csrf = data.csrf_token;
  $('login-form').hidden = true; $('logout').hidden = false; $('password-panel').hidden = false;
  $('account-identity').textContent = `${user.username} · ${user.role}`;
  $('feedback').textContent = user.role === 'admin' ? 'Use Admin to manage accounts and records.' : user.role === 'operator' ? 'Use Operator for mission controls; leave the legacy token field blank to use this session.' : 'You can request and cancel your own simulated trips below.';
  if (user.role === 'passenger') {
    $('passenger-panel').hidden = false;
    const graph = await api('/api/stops'); $('destination').replaceChildren();
    for (const [id,label] of Object.entries(graph.stops)) $('destination').add(new Option(`${id} · ${label}`,id));
    await myTrips();
  }
}
$('login-form').onsubmit = event => { event.preventDefault(); action(async () => {
  const password = $('login-password').value; $('login-password').value = '';
  await signedIn(await api('/api/auth/login','POST',{username:$('login-username').value,password}));
},event.submitter); };
$('logout').onclick = () => action(async () => { await api('/api/auth/logout','POST'); reset('Signed out.'); },$('logout'));
$('password-form').onsubmit = event => { event.preventDefault(); action(async () => {
  const current_password = $('old-password').value, new_password = $('new-password').value;
  $('password-form').reset(); await api('/api/auth/password','POST',{current_password,new_password}); reset('Password changed. Sign in again.');
},event.submitter); };
$('booking-form').onsubmit = event => { event.preventDefault(); action(async () => {
  await api('/api/trips','POST',{destination:$('destination').value}); $('feedback').textContent='Simulated trip accepted.'; await myTrips();
},event.submitter); };
$('refresh-trips').onclick = () => action(myTrips,$('refresh-trips'));
action(async () => { try { await signedIn(await api('/api/auth/me')); } catch { reset('Sign in with an account provided by your administrator.'); } });
