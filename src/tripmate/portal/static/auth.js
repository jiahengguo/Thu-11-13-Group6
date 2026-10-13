'use strict';
let csrf = '', mode = 'login';
const $ = id => document.getElementById(id);
function message(text, error=false) { const node=$('auth-message'); node.textContent=text; node.className='status-message'+(error?' error':''); node.hidden=false; }
async function api(path,body) {const response=await fetch(path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json','X-CSRF-Token':csrf}:{},body:body?JSON.stringify(body):undefined,credentials:'same-origin'});const data=await response.json();if(!response.ok)throw new Error(data.message||'The request could not complete.');return data;}
async function initialise() {
  // Remove email callback tokens from the address before any further navigation.
  const hash=new URLSearchParams(location.hash.slice(1));
  const callbackState=new URLSearchParams(location.search).get('state');
  if(location.hash)history.replaceState(null,'',location.pathname);
  const session=await api('/api/session');csrf=session.csrf;
  if(hash.get('error')){message(hash.get('error_description')||'This email link is invalid or expired. Request a new link.',true);return;}
  if(hash.get('access_token')&&hash.get('refresh_token')){
    const result=await api('/api/auth/callback',{access_token:hash.get('access_token'),refresh_token:hash.get('refresh_token'),state:callbackState||''});
    if(hash.get('type')==='recovery'){
      csrf=(await api('/api/session')).csrf;$('auth-form').hidden=true;$('auth-toggle').hidden=true;$('recover').hidden=true;$('password-form').hidden=false;$('auth-title').textContent='Set a new password';$('auth-description').textContent='Use at least 12 characters.';
    }else location.replace(result.portal+(new URLSearchParams(location.search).get('intent')==='partner'&&result.portal==='/app'?'?intent=partner':''));
  }else if(session.user)location.replace(session.portal+(new URLSearchParams(location.search).get('intent')==='partner'&&session.portal==='/app'?'?intent=partner':''));
}
$('auth-form').addEventListener('submit',async event=>{event.preventDefault();$('auth-submit').disabled=true;try{const data=await api('/api/auth/'+mode,{email:$('email').value.trim(),password:$('password').value});$('password').value='';if(data.portal)location.replace(data.portal+(new URLSearchParams(location.search).get('intent')==='partner'&&data.portal==='/app'?'?intent=partner':''));else message(data.message);}catch(error){message(error.message,true);}finally{$('auth-submit').disabled=false;}});
$('auth-toggle').addEventListener('click',()=>{mode=mode==='login'?'signup':'login';const signup=mode==='signup';$('auth-title').textContent=signup?'Create your account':'Sign in';$('auth-submit').textContent=signup?'Create account':'Sign in';$('auth-toggle').textContent=signup?'Already have an account? Sign in':'Create an account';$('auth-description').textContent=signup?'Start as a traveller. Verify your email before using a portal.':'Use your verified email and password.';$('password').autocomplete=signup?'new-password':'current-password';$('password').minLength=signup?12:1;$('auth-message').hidden=true;});
$('recover').addEventListener('click',async()=>{const email=$('email').value.trim();if(!$('email').checkValidity()||!email){$('email').reportValidity();message('Enter your email above to request recovery instructions.',true);return;}$('recover').disabled=true;try{message((await api('/api/auth/recover',{email})).message);}catch(error){message(error.message,true);}finally{$('recover').disabled=false;}});
$('password-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{const data=await api('/api/auth/password',{password:$('new-password').value});$('new-password').value='';$('password-form').hidden=true;message(data.message);csrf=(await api('/api/session')).csrf;$('auth-form').hidden=false;$('auth-toggle').hidden=false;$('recover').hidden=false;$('auth-title').textContent='Sign in';}catch(error){message(error.message,true);}finally{button.disabled=false;}});
initialise().catch(error=>message(error.message,true));
