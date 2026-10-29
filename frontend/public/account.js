'use strict';
const $=id=>document.getElementById(id);
let csrf='',user=null,version=0;
function reset(message){
  ++version;user=null;csrf='';Taxi.text('account-identity','Sign in');$('login-form').hidden=false;
  for(const id of ['logout','password-panel','passenger-panel','account-next'])$(id).hidden=true;
  Taxi.message('feedback',message);$('password-form').reset();Taxi.connection('connection','disconnected','○ Signed out');
}
async function api(path,method='GET',body){
  const generation=version;
  try{const data=await TaxiApi.request(path,{method,body,csrf});if(generation!==version)throw new Error('Session changed.');return data;}
  catch(error){if(error.status===401 && user && path!=='/api/auth/password')reset('Session expired.');if(!error.status)Taxi.connection('connection','disconnected');throw error;}
}
async function action(fn,button){
  if(button){button.disabled=true;button.setAttribute('aria-busy','true');}
  Taxi.message('feedback','Working…');
  try{await fn();}catch(error){TaxiApi.showError(error,'feedback',button?.form);}
  finally{if(button){button.disabled=false;button.removeAttribute('aria-busy');}}
}
async function signedIn(data){
  user=data.user;csrf=data.csrf_token;$('login-form').hidden=true;$('logout').hidden=false;$('password-panel').hidden=false;
  Taxi.text('account-identity',`${user.username} · ${user.role}`);Taxi.connection('connection','live','● Session verified');
  if(user.must_change_password){$('account-next').hidden=true;$('passenger-panel').hidden=true;Taxi.message('feedback','Change your temporary password below before using the service.');return;}
  const destination={passenger:'/passenger',operator:'/operator',admin:'/admin',diagnostics:'/diagnostics'}[user.role];
  $('account-next').href=destination;$('account-next').textContent={passenger:'Choose your destination →',operator:'Open mission control →',admin:'Open administration →',diagnostics:'Open diagnostics →'}[user.role];$('account-next').hidden=false;
  Taxi.message('feedback','Your permissions are enforced by the backend. Use your workspace to continue.');
  $('passenger-panel').hidden=user.role!=='passenger';
  const next=new URLSearchParams(location.search).get('next');if(next===destination)location.assign(next);
}
$('login-form').onsubmit=event=>{event.preventDefault();action(async()=>{const password=$('login-password').value;$('login-password').value='';await signedIn(await api('/api/auth/login','POST',{username:$('login-username').value,password}));},event.submitter);};
$('logout').onclick=()=>action(async()=>{await api('/api/auth/logout','POST');reset('Signed out. Your session was revoked.');},$('logout'));
$('password-form').onsubmit=event=>{event.preventDefault();action(async()=>{
  const current_password=$('old-password').value,new_password=$('new-password').value;$('password-form').reset();await api('/api/auth/password','POST',{current_password,new_password});reset('Password changed. Every session was revoked; sign in again.');
},event.submitter);};
(async()=>{try{await signedIn(await api('/api/auth/me'));}catch(error){reset(error.status===401?'Sign in with the account supplied by your administrator.':error.message);if(error.status!==401)Taxi.message('feedback',error.message,true);}})();
