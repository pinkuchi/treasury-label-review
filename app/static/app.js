const pick = document.querySelector('#files');
const drop = document.querySelector('#drop');
const button = document.querySelector('#analyze');
const selected = document.querySelector('#selected');
const results = document.querySelector('#results');
const empty = document.querySelector('#empty');
let queue=[];
const escapeHTML=s=>String(s??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setFiles(list){queue=Array.from(list).slice(0,20);selected.innerHTML=queue.map(f=>`<div>▧ ${escapeHTML(f.name)} · ${(f.size/1024/1024).toFixed(2)} MB</div>`).join('');button.disabled=!queue.length;}
pick.addEventListener('change',e=>setFiles(e.target.files));
['dragenter','dragover'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.add('drag')}));
['dragleave','drop'].forEach(x=>drop.addEventListener(x,e=>{e.preventDefault();drop.classList.remove('drag')}));
drop.addEventListener('drop',e=>setFiles(e.dataTransfer.files));
function renderCheck(label,data){return `<div class="check"><div class="check-head"><span>${label}</span><span class="status ${escapeHTML(data.status)}">${escapeHTML(data.status)}</span></div><small>Application: ${escapeHTML(data.expected)}</small><small>Detected: ${escapeHTML(data.found)}</small><small>${escapeHTML(data.note)}</small></div>`;}
function render(res){const checks=res.checks;return `<article class="result-card"><h3>${escapeHTML(res.filename)} <span class="status ${escapeHTML(res.overall)}">${escapeHTML(res.overall)}</span></h3><div class="meta">Processed in ${(res.duration_ms/1000).toFixed(2)} seconds · human review required</div>${renderCheck('Brand name',checks.brand || {status:'review',note:'No applicant brand supplied'})}${renderCheck('Alcohol content (ABV)',checks.abv)}${renderCheck('Net contents',checks.volume)}${renderCheck('Government health warning',checks.warning)}<details><summary class="meta">View raw OCR evidence</summary><textarea class="ocr" readonly>${escapeHTML(res.ocr_text)}</textarea></details><div class="notice">${escapeHTML(res.notice)}</div></article>`}
button.addEventListener('click',async()=>{button.disabled=true;button.textContent='Reviewing labels…';results.innerHTML='';empty.hidden=true;
 for(const file of queue){const card=document.createElement('div');results.appendChild(card);card.className='result-card';card.textContent='Analyzing '+file.name+'…';
 try{const form=new FormData();form.append('file',file);['brand','abv','volume'].forEach(key=>form.append(key,document.getElementById(key).value));const response=await fetch('/api/analyze',{method:'POST',body:form});const kind=response.headers.get('content-type')||'';const raw=await response.text();let data;if(kind.includes('application/json')){try{data=JSON.parse(raw)}catch{throw Error('Invalid JSON returned by server')}}else{throw Error('Server returned HTTP '+response.status+' instead of JSON. The app may be restarting or overloaded; retry shortly.')}if(!response.ok)throw Error(data.detail||('Server error (HTTP '+response.status+')'));card.outerHTML=render(data)}catch(err){card.innerHTML=`<h3>${escapeHTML(file.name)}</h3><span class="status mismatch">Error</span><p>${escapeHTML(err.message)}</p>`}}
 button.disabled=false;button.innerHTML='Run label review <span>→</span>';});