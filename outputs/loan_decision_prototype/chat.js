let csrf='',pending=false,ready=false,connected=false;
const feed=document.getElementById('feed'),error=document.getElementById('error'),input=document.getElementById('message'),status=document.getElementById('activity');
let rows=[];
function bubble(m,animate=false){
 const el=document.createElement('div');const ai=m.role!=='user'&&m.kind?.startsWith('Groq');
 el.className='bubble '+(m.role==='user'?'user':ai?'assistant ai':'assistant app-message')+(animate?' enter':'');
 const meta=document.createElement('div');meta.className='meta';
 meta.textContent=m.role==='user'?'You':ai?'✦ Groq AI · '+(m.model||m.kind.replace('Groq · ','').replace('Groq explanation + local model','AI explanation + local assessment')):'App · '+(m.kind||'guide');
 const content=document.createElement('div');content.className='message-text';content.textContent=m.text;el.append(meta,content);
 if(m.sources?.length){const details=document.createElement('details');details.className='sources';const summary=document.createElement('summary');summary.textContent='Policy evidence · '+m.sources.length+' clauses';details.append(summary);for(const c of m.sources){const article=document.createElement('article'),title=document.createElement('b'),p=document.createElement('p');title.textContent=c.id+' · '+c.title;p.textContent=c.text;article.append(title,p);details.append(article)}el.append(details)}
 if(m.case_id){const link=document.createElement('a');link.className='case';link.href='/case?id='+encodeURIComponent(m.case_id);link.textContent='Open case · human review pending ↗';el.append(link)}return el;
}
function scrollDown(){feed.scrollTo({top:feed.scrollHeight,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}
function render(s,initial=false){
 csrf=s.csrf;connected=s.connected;ready=s.ready;
 const badge=document.getElementById('connection');badge.textContent=s.connected?'Groq configured · '+s.model:'Groq not configured';badge.classList.toggle('off',!s.connected);
 document.getElementById('confirm').classList.toggle('show',s.ready);
 const nearBottom=feed.scrollHeight-feed.scrollTop-feed.clientHeight<100;
 const keys=s.messages.map(m=>JSON.stringify(m));let common=0;while(common<rows.length&&common<keys.length&&rows[common].key===keys[common])common++;
 for(const row of rows.splice(common))row.el.remove();
 for(let i=common;i<s.messages.length;i++){const el=bubble(s.messages[i],!initial);feed.append(el);rows.push({key:keys[i],el})}
 if(initial||nearBottom)scrollDown();
}
function busy(value,label=''){
 pending=value;document.querySelectorAll('button').forEach(b=>b.disabled=value||!csrf);feed.setAttribute('aria-busy',String(value));status.textContent=label;status.classList.toggle('working',value);
}
async function send(raw){
 const text=raw.trim();if(pending||!csrf||!text)return;
 const submitted=input.value;input.value='';error.textContent='';
 const optimistic=bubble({role:'user',text},true);feed.append(optimistic);scrollDown();
 const local=['start over','check my eligibility','demo approval','demo rejection','demo edge','confirm assessment'].includes(text.toLowerCase());
 busy(true,local?'Processing application…':'Waiting for response…');
 const typing=document.createElement('div');typing.className='typing';typing.setAttribute('role','status');typing.innerHTML='<span></span><span></span><span></span><small>Processing your message</small>';feed.append(typing);scrollDown();
 try{const r=await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({csrf,text})});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');optimistic.remove();typing.remove();render(data);scrollDown();status.textContent=data.messages.at(-1)?.kind?.startsWith('Groq')?'Groq AI replied':'App updated'}
 catch(e){optimistic.remove();typing.remove();error.textContent=e.message; if(!input.value)input.value=submitted||text;status.textContent='Message failed — try again'}
 finally{busy(false,status.textContent);input.focus()}
}
async function reset(){
 if(pending||!csrf)return;error.textContent='';busy(true,'Starting a new conversation…');
 try{const r=await fetch('/api/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({csrf})});const s=await r.json();if(!r.ok)throw Error(s.error||'Could not reset');render(s,true);input.value='';status.textContent='New conversation started'}catch(e){error.textContent=e.message}finally{busy(false,status.textContent);input.focus()}
}
document.getElementById('composer').addEventListener('submit',e=>{e.preventDefault();send(input.value)});
document.querySelectorAll('[data-send]').forEach(b=>b.addEventListener('click',()=>send(b.dataset.send)));
document.getElementById('new-chat').addEventListener('click',reset);
busy(true,'Connecting to local app…');fetch('/api/state').then(r=>{if(!r.ok)throw Error('Could not connect');return r.json()}).then(s=>{render(s,true);busy(false,'Ready')}).catch(()=>{error.textContent='Could not connect to the local server. Refresh to retry.';busy(false,'Disconnected')});
